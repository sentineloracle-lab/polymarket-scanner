import json
import re
import logging
import os
import csv
import time
from groq import Groq

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def clean_json_response(raw_text):
    """Nettoyage rigoureux du JSON pour Groq."""
    try:
        text = re.sub(r'```json', '', raw_text)
        text = re.sub(r'```', '', text)
        match = re.search(r'\{.*\}', text, re.DOTALL)
        return match.group(0) if match else text.strip()
    except: return raw_text

def append_to_csv(row):
    file_path = "scan_history.csv"
    file_exists = os.path.isfile(file_path)
    with open(file_path, mode='a', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Timestamp", "Question", "ID", "Volume", "Liquidity", "Decision", "Strategy", "Confidence", "Edge", "Risk_Flags"])
        writer.writerow(row)

def run_aggressive_scanner(markets, prompts_dir):
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        logging.error("GROQ_API_KEY manquante.")
        return {"decision": "ERROR", "count": 0}

    client = Groq(api_key=api_key)
    # llama-3.3-70b-versatile est excellent pour l'analyse financière
    model_id = "llama-3.3-70b-versatile" 

    # Chargement du prompt système
    prompt_path = os.path.join("prompts", "mega_analysis.txt")
    if not os.path.exists(prompt_path):
        prompt_path = os.path.join("prompts", "system.txt")
    
    with open(prompt_path, "r", encoding="utf-8") as f:
        system_prompt = f.read()

    candidates = []
    logging.info(f"🚀 Scan RAPIDE lancé avec Groq ({model_id})")

    for i, market in enumerate(markets):
        try:
            # Appel API Groq
            completion = client.chat.completions.create(
                model=model_id,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Analyze this market: {market}"}
                ],
                temperature=0.1,
                response_format={"type": "json_object"} # Groq supporte le mode JSON natif
            )
            
            raw_res = completion.choices[0].message.content
            analysis = json.loads(raw_res)
            
            decision = analysis.get('decision', 'REJECTED')
            conf = analysis.get('confidence_score', 0)

            # Log de progression
            status = "🟢 OPPORTUNITÉ" if decision == "OPPORTUNITY" and conf >= 80 else "⚪ REJET"
            logging.info(f"[{i+1}/{len(markets)}] {status} : {market.get('question')[:50]}...")

            append_to_csv([
                time.strftime("%Y-%m-%d %H:%M:%S"), 
                market.get('question'), market.get('id'), market.get('volume'), 
                market.get('liquidity'), decision, analysis.get('strategy'), 
                conf, analysis.get('edge_estimate'), str(analysis.get('risk_flags'))
            ])

            if decision == "OPPORTUNITY" and conf >= 80:
                candidates.append(market)

            # Pause très courte pour éviter le Rate Limit de Groq (beaucoup plus généreux)
            time.sleep(0.5) 

        except Exception as e:
            if "rate_limit_exceeded" in str(e).lower():
                logging.warning("⚠️ Rate limit Groq, pause de 10s...")
                time.sleep(10)
            else:
                logging.error(f"Erreur sur {market.get('id')} : {e}")

    return {"decision": "SCAN_COMPLETED", "count": len(candidates), "markets": candidates}
