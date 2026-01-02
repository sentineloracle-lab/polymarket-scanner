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
    with open(file_path, mode='a', newline='', encoding='utf-8-sig') as f:
        csv.writer(f).writerow(row)

def run_aggressive_scanner(markets, prompts_dir):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logging.error("GEMINI_API_KEY manquante.")
        return {"decision": "ERROR", "count": 0}

    # Liste exhaustive des combinaisons à tester pour débloquer le 404
    attempts = [
        ("v1", "gemini-1.5-flash"),
        ("v1beta", "gemini-1.5-flash"),
        ("v1", "gemini-pro"),
        ("v1beta", "gemini-pro")
    ]
    
    prompt_path = os.path.join("prompts", "mega_analysis.txt")
    if not os.path.exists(prompt_path): prompt_path = os.path.join("prompts", "system.txt")
    with open(prompt_path, "r", encoding="utf-8") as f: system_instructions = f.read()

    candidates = []
    working_config = None # On garde en mémoire celle qui marche

    logging.info("🚀 Scan de diagnostic lancé...")

    for market in markets:
        success = False
        
        # Si on n'a pas encore trouvé la config qui marche, on les teste toutes
        configs_to_test = [working_config] if working_config else attempts

        for version, model_id in configs_to_test:
            if not model_id: continue
            url = f"https://generativelanguage.googleapis.com/{version}/models/{model_id}:generateContent?key={api_key}"
            
            try:
                payload = {
                    "contents": [{"parts": [{"text": f"{system_instructions}\n\nANALYSE :\n{market}"}]}],
                    "generationConfig": {"temperature": 0.1}
                }
                
                response = requests.post(url, headers={'Content-Type': 'application/json'}, json=payload)
                
                if response.status_code == 200:
                    working_config = (version, model_id)
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
                        logging.info(f"🟢 SUCCESS ({model_id} {version}) : {market.get('question')}")
                    success = True
                    break
                else:
                    if not working_config:
                        logging.warning(f"❌ Test échoué : {model_id} en {version} (Code {response.status_code})")

            except Exception as e:
                logging.error(f"Erreur technique : {e}")
                break

        if not success and not working_config:
            logging.error("‼️ AUCUNE CONFIGURATION NE FONCTIONNE. Vérifiez votre clé API sur AI Studio.")
            return {"decision": "FATAL_ERROR", "count": 0}

        time.sleep(2) # On accélère un peu si ça marche

    return {"decision": "SCAN_COMPLETED", "count": len(candidates), "markets": candidates}
