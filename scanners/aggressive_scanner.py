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
    """Version HTTP avec repli automatique sur plusieurs noms de modèles."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logging.error("GEMINI_API_KEY manquante.")
        return {"decision": "ERROR", "count": 0}

    # Liste des variantes de noms de modèles à tester
    model_variants = ["gemini-1.5-flash-latest", "gemini-1.5-flash", "gemini-pro"]
    
    # Lecture du prompt
    prompt_path = os.path.join("prompts", "mega_analysis.txt")
    if not os.path.exists(prompt_path):
        prompt_path = os.path.join("prompts", "system.txt")
    
    with open(prompt_path, "r", encoding="utf-8") as f:
        system_instructions = f.read()

    candidates = []
    current_model_index = 0
    
    logging.info(f"🚀 Scan en cours : Mode AUTO-RETRY (V1 Stable)")

    for market in markets:
        success = False
        while not success and current_model_index < len(model_variants):
            model_id = model_variants[current_model_index]
            url = f"https://generativelanguage.googleapis.com/v1/models/{model_id}:generateContent?key={api_key}"
            
            try:
                payload = {
                    "contents": [{"parts": [{"text": f"{system_instructions}\n\nANALYSE CE MARCHÉ :\n{market}"}]}],
                    "generationConfig": {"temperature": 0.1}
                }
                
                response = requests.post(url, headers={'Content-Type': 'application/json'}, json=payload)
                res_data = response.json()

                if response.status_code == 200:
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
                        logging.info(f"🟢 OPPORTUNITÉ ({model_id}) : {market.get('question')}")
                    
                    success = True
                elif response.status_code == 404:
                    logging.warning(f"⚠️ Modèle {model_id} non trouvé, essai du suivant...")
                    current_model_index += 1
                else:
                    logging.error(f"Erreur {response.status_code} sur {model_id}")
                    break

            except Exception as e:
                logging.error(f"Erreur : {e}")
                break

        time.sleep(4) # Respect du quota

    return {"decision": "SCAN_COMPLETED", "count": len(candidates), "markets": candidates}
