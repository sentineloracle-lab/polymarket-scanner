import json
import re
import logging
import os
import csv
import time
from groq import Groq

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def clean_json_response(raw_text):
    try:
        text = re.sub(r'```json|```', '', raw_text)
        match = re.search(r'\[.*\]|\{.*\}', text, re.DOTALL)
        return match.group(0) if match else text.strip()
    except: return raw_text

def append_to_csv(rows):
    file_path = "scan_history.csv"
    file_exists = os.path.isfile(file_path)
    with open(file_path, mode='a', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Timestamp", "Question", "ID", "Volume", "Liquidity", "Decision", "Strategy", "Confidence", "Edge", "Risk_Flags"])
        writer.writerows(rows)

def run_aggressive_scanner(markets, prompts_dir):
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key: return {"decision": "ERROR", "count": 0}

    client = Groq(api_key=api_key)
    # Llama 3 8b est 10x plus rapide que le 70b pour le tri de masse
    model_id = "llama3-8b-8192" 

    # Filtrage préalable : On ignore les marchés sans liquidité (souvent vieux ou morts)
    active_markets = [m for m in markets if float(m.get('liquidity', 0)) > 100]
    logging.info(f"🔍 Filtrage : {len(active_markets)} marchés valides sur {len(markets)} (Liquidité > 100$)")

    prompt_path = os.path.join("prompts", "mega_analysis.txt")
    if not os.path.exists(prompt_path): prompt_path = os.path.join("prompts", "system.txt")
    with open(prompt_path, "r", encoding="utf-8") as f: system_prompt = f.read()

    batch_size = 10
    candidates = []
    
    logging.info(f"🚀 Scan BATCHÉ (10 par 10) avec Groq {model_id}")

    for i in range(0, len(active_markets), batch_size):
        batch = active_markets[i:i + batch_size]
        try:
            # On demande une liste de résultats JSON
            batch_data = [{"id": m.get('id'), "q": m.get('question')} for m in batch]
            
            completion = client.chat.completions.create(
                model=model_id,
                messages=[
                    {"role": "system", "content": system_prompt + "\nIMPORTANT: Réponds UNIQUEMENT par une LISTE JSON de résultats pour chaque marché fourni."},
                    {"role": "user", "content": f"Analyse ces {len(batch)} marchés : {json.dumps(batch_data)}"}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            raw_res = completion.choices[0].message.content
            results = json.loads(clean_json_response(raw_res))
            
            # Si l'IA renvoie un dictionnaire avec une clé 'results' ou 'markets'
            if isinstance(results, dict):
                results = results.get('results', results.get('markets', [results]))
            
            # S'assurer que c'est une liste
            if not isinstance(results, list): results = [results]

            csv_buffer = []
            for res, m in zip(results, batch):
                decision = res.get('decision', 'REJECTED')
                conf = res.get('confidence_score', 0)
                
                csv_buffer.append([
                    time.strftime("%Y-%m-%d %H:%M:%S"), m.get('question'), m.get('id'),
                    m.get('volume'), m.get('liquidity'), decision, res.get('strategy'),
                    conf, res.get('edge_estimate'), str(res.get('risk_flags'))
                ])
                
                if decision == "OPPORTUNITY" and conf >= 80:
                    candidates.append(m)
                    logging.info(f"🟢 OPPORTUNITÉ : {m.get('question')}")

            append_to_csv(csv_buffer)
            logging.info(f"📦 Batch {i//batch_size + 1} traité ({min(i+batch_size, len(active_markets))}/{len(active_markets)})")
            
            time.sleep(2) # Petite pause pour le quota

        except Exception as e:
            logging.error(f"Erreur sur le batch {i}: {e}")
            time.sleep(5)

    return {"decision": "SCAN_COMPLETED", "count": len(candidates), "markets": candidates}
