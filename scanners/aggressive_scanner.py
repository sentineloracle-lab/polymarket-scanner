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

def get_available_model(api_key):
    """Interroge Google pour savoir quel modèle cette clé peut utiliser."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            models = response.json().get('models', [])
            # On cherche un modèle qui supporte generateContent et qui est un Gemini
            for m in models:
                if "generateContent" in m.get("supportedGenerationMethods", []) and "gemini" in m.get("name").lower():
                    logging.info(f"✅ Modèle trouvé et sélectionné : {m.get('name')}")
                    return m.get("name")
        logging.error(f"Impossible de lister les modèles : {response.text}")
    except Exception as e:
        logging.error(f"Erreur lors du listage : {e}")
    return None

def run_aggressive_scanner(markets, prompts_dir):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key: return {"decision": "ERROR", "count": 0}

    # AUTO-DÉTECTION DU MODÈLE
    model_path = get_available_model(api_key)
    if not model_path:
        logging.error("❌ Aucun modèle Gemini compatible trouvé pour cette clé API.")
        return {"decision": "MODEL_NOT_FOUND", "count": 0}

    url = f"https://generativelanguage.googleapis.com/v1beta/{model_path}:generateContent?key={api_key}"
    
    prompt_path = os.path.join("prompts", "mega_analysis.txt")
    if not os.path.exists(prompt_path): prompt_path = os.path.join("prompts", "system.txt")
    with open(prompt_path, "r", encoding="utf-8") as f: system_instructions = f.read()

    candidates = []
    for market in markets:
        try:
            payload = {"contents": [{"parts": [{"text": f"{system_instructions}\n\nDATA:\n{market}"}]}]}
            response = requests.post(url, headers={'Content-Type': 'application/json'}, json=payload)
            
            if response.status_code == 200:
                res_data = response.json()
                raw_text = res_data['candidates'][0]['content']['parts'][0]['text']
                analysis = json.loads(clean_json_response(raw_text))
                
                if analysis.get('decision') == "OPPORTUNITY":
                    candidates.append(market)
                    logging.info(f"🟢 OPPORTUNITÉ : {market.get('question')}")
                
                # Sauvegarde CSV simplifiée pour le test
                with open("scan_history.csv", "a") as f:
                    csv.writer(f).writerow([time.ctime(), market.get('question'), analysis.get('decision')])
            else:
                logging.error(f"Échec sur {model_path}: {response.text}")
                return {"decision": "API_FAILURE", "count": 0}

            time.sleep(2)
        except Exception as e:
            logging.error(f"Erreur : {e}")

    return {"decision": "SCAN_COMPLETED", "count": len(candidates), "markets": candidates}
