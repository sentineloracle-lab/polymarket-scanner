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

def run_aggressive_scanner(markets, prompts_dir):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key: return {"decision": "ERROR", "count": 0}

    # On force le modèle que nous avons découvert
    model_path = "models/gemini-2.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/{model_path}:generateContent?key={api_key}"
    
    prompt_path = os.path.join("prompts", "mega_analysis.txt")
    if not os.path.exists(prompt_path): prompt_path = os.path.join("prompts", "system.txt")
    with open(prompt_path, "r", encoding="utf-8") as f: system_instructions = f.read()

    candidates = []
    logging.info(f"🚀 Analyse bridée à 5 RPM pour respecter le quota (Modèle: {model_path})")

    for i, market in enumerate(markets):
        try:
            payload = {"contents": [{"parts": [{"text": f"{system_instructions}\n\nDATA:\n{market}"}]}]}
            response = requests.post(url, headers={'Content-Type': 'application/json'}, json=payload)
            
            if response.status_code == 200:
                res_data = response.json()
                raw_text = res_data['candidates'][0]['content']['parts'][0]['text']
                analysis = json.loads(clean_json_response(raw_text))
                
                decision = analysis.get('decision', 'REJECTED')
                if decision == "OPPORTUNITY":
                    candidates.append(market)
                    logging.info(f"🟢 [{i+1}/{len(markets)}] OPPORTUNITÉ : {market.get('question')}")
                else:
                    logging.info(f"⚪ [{i+1}/{len(markets)}] Analysé : REJET")

                # Sauvegarde CSV
                with open("scan_history.csv", "a", newline='', encoding='utf-8') as f:
                    csv.writer(f).writerow([time.ctime(), market.get('question'), decision])
            
            elif response.status_code == 429:
                logging.warning("⚠️ Quota atteint (5 RPM). Pause forcée de 60 secondes...")
                time.sleep(60) # On attend une minute entière pour reset le quota
                continue # On retente le même marché après la pause

            else:
                logging.error(f"Erreur {response.status_code}: {response.text}")

            # PAUSE STRATÉGIQUE : 13 secondes entre chaque requête 
            # (60s / 13s = ~4.6 requêtes par minute, ce qui nous garde sous la limite de 5)
            time.sleep(13)

        except Exception as e:
            logging.error(f"Erreur technique : {e}")

    return {"decision": "SCAN_COMPLETED", "count": len(candidates), "markets": candidates}
