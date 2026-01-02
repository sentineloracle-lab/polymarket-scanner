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
        # Enlever les blocs de code Markdown
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

    # URL CORRIGÉE : Suppression du "/" superflu avant le ":"
    # Format exact : https://generativelanguage.googleapis.com/v1/models/{model}:generateContent
    base_url = "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent"
    
    prompt_path = os.path.join("prompts", "mega_analysis.txt")
    if not os.path.exists(prompt_path): prompt_path = os.path.join("prompts", "system.txt")
    with open(prompt_path, "r", encoding="utf-8") as f: system_instructions = f.read()

    candidates = []
    logging.info("🚀 Analyse en cours (Endpoint v1 Stable)...")

    for market in markets:
        try:
            # Paramètre API Key passé dans l'URL pour une compatibilité maximale
            url = f"{base_url}?key={api_key}"
            
            payload = {
                "contents": [{
                    "parts": [{
                        "text": f"{system_instructions}\n\nMARCHÉ À ANALYSER :\n{market}"
                    }]
                }],
                "generationConfig": {
                    "temperature": 0.1,
                    "topP": 0.95,
                    "maxOutputTokens": 1024
                }
            }
            
            response = requests.post(url, headers={'Content-Type': 'application/json'}, json=payload)
            
            if response.status_code == 200:
                res_data = response.json()
                if 'candidates' in res_data and len(res_data['candidates']) > 0:
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
                    logging.warning(f"⚠️ Réponse vide de l'IA pour {market.get('id')}")
            
            elif response.status_code == 404:
                logging.error(f"❌ Erreur 404 persistante. Tentative avec l'URL alternative...")
                # Fallback immédiat sur l'ancienne structure si la v1 échoue encore
                alt_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
                response = requests.post(alt_url, headers={'Content-Type': 'application/json'}, json=payload)
                # (Le reste de la logique de traitement peut être ajouté ici si nécessaire)

            else:
                logging.warning(f"⚠️ Erreur {response.status_code} sur {market.get('id')}: {response.text}")

            # Pause pour respecter le quota (15 RPM)
            time.sleep(4)

        except Exception as e:
            logging.error(f"Erreur technique sur {market.get('id')} : {e}")

    return {"decision": "SCAN_COMPLETED", "count": len(candidates), "markets": candidates}
