import json
import re
import logging
import os
import csv
import time
import requests

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def clean_json_response(raw_text):
    """Extrait le bloc JSON d'une réponse texte."""
    try:
        text = re.sub(r'```json', '', raw_text)
        text = re.sub(r'```', '', text)
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return match.group(0)
        return text.strip()
    except Exception:
        return raw_text

def append_to_csv(row):
    file_path = "scan_history.csv"
    file_exists = os.path.isfile(file_path)
    with open(file_path, mode='a', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Timestamp", "Question", "ID", "Volume", "Liquidity", "Decision", "Strategy", "Confidence", "Edge", "Risk_Flags"])
        writer.writerow(row)

def run_aggressive_scanner(markets, prompts_dir):
    """Version Direct HTTP pour contourner les erreurs de SDK."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logging.error("GEMINI_API_KEY manquante.")
        return {"decision": "ERROR", "count": 0}

    # URL STABLE DE GOOGLE
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    # Lecture du prompt
    prompt_path = os.path.join("prompts", "mega_analysis.txt")
    if not os.path.exists(prompt_path):
        prompt_path = os.path.join("prompts", "system.txt")
    
    with open(prompt_path, "r", encoding="utf-8") as f:
        system_instructions = f.read()

    candidates = []
    logging.info(f"🚀 Scan en cours : Mode DIRECT HTTP (V1 Stable)")

    for market in markets:
        try:
            # Construction de la requête selon le format exact de Google
            payload = {
                "contents": [{
                    "parts": [{
                        "text": f"{system_instructions}\n\nANALYSE CE MARCHÉ :\n{market}"
                    }]
                }],
                "generationConfig": {
                    "temperature": 0.1
                }
            }

            headers = {'Content-Type': 'application/json'}
            
            response = requests.post(url, headers=headers, json=payload)
            res_data = response.json()

            if response.status_code == 200:
                # Extraction du texte de la réponse Google
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
            else:
                logging.error(f"Erreur API {response.status_code}: {res_data}")
                append_to_csv([time.strftime("%Y-%m-%d %H:%M:%S"), market.get('question'), market.get('id'), market.get('volume'), market.get('liquidity'), "ERROR_HTTP", "N/A", 0, 0, f"Code {response.status_code}"])

            # Délai pour le quota gratuit (15 requêtes par minute max)
            time.sleep(4) 

        except Exception as e:
            logging.error(f"Erreur sur {market.get('question')} : {e}")
            append_to_csv([time.strftime("%Y-%m-%d %H:%M:%S"), market.get('question'), market.get('id'), market.get('volume'), market.get('liquidity'), "ERROR_API", "N/A", 0, 0, str(e)])

    return {"decision": "SCAN_COMPLETED", "count": len(candidates), "markets": candidates}
