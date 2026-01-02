import json
import re
import logging
import os
import csv
import time
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def clean_json_response(raw_text):
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

    # Stratégie de la dernière chance : Tester le modèle avec le préfixe "models/" explicite
    # et l'endpoint de base sans spécifier de version si le 404 persiste.
    model_name = "models/gemini-1.5-flash" 
    url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={api_key}"
    
    prompt_path = os.path.join("prompts", "mega_analysis.txt")
    if not os.path.exists(prompt_path): prompt_path = os.path.join("prompts", "system.txt")
    with open(prompt_path, "r", encoding="utf-8") as f: system_instructions = f.read()

    candidates = []
    logging.info(f"🚀 Tentative finale (Model: {model_name})")

    for market in markets:
        try:
            payload = {
                "contents": [{
                    "parts": [{
                        "text": f"{system_instructions}\n\nDATA:\n{market}"
                    }]
                }]
            }
            
            response = requests.post(url, headers={'Content-Type': 'application/json'}, json=payload)
            
            if response.status_code == 200:
                res_data = response.json()
                raw_text = res_data['candidates'][0]['content']['parts'][0]['text']
                analysis = json.loads(clean_json_response(raw_text))
                
                decision = analysis.get('decision', 'REJECTED_AI')
                append_to_csv([
                    time.strftime("%Y-%m-%d %H:%M:%S"), 
                    market.get('question'), market.get('id'), market.get('volume'), 
                    market.get('liquidity'), decision, analysis.get('strategy'), 
                    analysis.get('confidence_score', 0), analysis.get('edge_estimate'), str(analysis.get('risk_flags'))
                ])
                
                if decision == "OPPORTUNITY" and analysis.get('confidence_score', 0) >= 80:
                    candidates.append(market)
                    logging.info(f"🟢 OPPORTUNITÉ : {market.get('question')}")
            else:
                # Si ça échoue encore, on log la réponse COMPLETE de Google pour comprendre
                logging.error(f"❌ Échec Critique {response.status_code}: {response.text}")
                # On s'arrête après le premier échec pour ne pas spammer et pour analyser le log
                return {"decision": "API_FAILURE", "count": 0}

            time.sleep(4)
        except Exception as e:
            logging.error(f"Erreur : {e}")

    return {"decision": "SCAN_COMPLETED", "count": len(candidates), "markets": candidates}
