import json
import re
import logging
import os
import csv
import time
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def clean_json_response(raw_text):
    """Extrait le JSON proprement du texte de l'IA."""
    try:
        text = re.sub(r'```json|```', '', raw_text)
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
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logging.error("GEMINI_API_KEY manquante.")
        return {"decision": "ERROR", "count": 0}

    # Utilisation du modèle flash 1.5 en version stable v1
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    prompt_path = os.path.join("prompts", "mega_analysis.txt")
    if not os.path.exists(prompt_path): prompt_path = os.path.join("prompts", "system.txt")
    with open(prompt_path, "r", encoding="utf-8") as f: system_instructions = f.read()

    candidates = []
    logging.info("🚀 Lancement de l'analyse avec Gemini 1.5 Flash (v1)")

    for market in markets:
        try:
            payload = {
                "contents": [{
                    "parts": [{
                        "text": f"{system_instructions}\n\nANALYSE LE MARCHÉ SUIVANT :\n{market}"
                    }]
                }],
                "generationConfig": {
                    "temperature": 0.1
                }
            }
            
            response = requests.post(url, headers={'Content-Type': 'application/json'}, json=payload)
            
            if response.status_code == 200:
                res_data = response.json()
                raw_text = res_data['candidates'][0]['content']['parts'][0]['text']
                analysis = json.loads(clean_json_response(raw_text))
                
                decision = analysis.get('decision', 'REJECTED_AI')
                conf = analysis.get('confidence_score', 0)
                
                append_to_csv([
                    time.strftime("%Y-%m-%d %H:%M:%S"), 
                    market.get('question'), market.get('id'), market.get('volume'), 
                    market.get('liquidity'), decision, analysis.get('strategy'), 
                    conf, analysis.get('edge_estimate'), str(analysis.get('risk_flags'))
                ])
                
                if decision == "OPPORTUNITY" and conf >= 80:
                    candidates.append(market)
                    logging.info(f"🟢 OPPORTUNITÉ : {market.get('question')}")
                
            elif response.status_code == 403:
                logging.error("‼️ ERREUR 403 : Votre clé API est rejetée par Google. Vérifiez AI Studio.")
                return {"decision": "AUTH_ERROR", "count": 0}
            else:
                logging.warning(f"⚠️ Erreur {response.status_code} sur {market.get('id')}")

            time.sleep(4) # Respect du quota gratuit

        except Exception as e:
            logging.error(f"Erreur technique : {e}")

    return {"decision": "SCAN_COMPLETED", "count": len(candidates), "markets": candidates}
