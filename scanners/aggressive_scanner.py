import json
import re
import logging
import os
import csv
import time
from google import genai
from google.genai import types

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def clean_json_response(raw_text):
    """Extrait le bloc JSON d'une réponse texte."""
    try:
        match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if match:
            return match.group(0)
        return raw_text
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
    """Fonction utilisant le SDK Google GenAI configuré sur la version V1."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logging.error("GEMINI_API_KEY manquante.")
        return {"decision": "ERROR", "count": 0}

    # FORCER LA VERSION V1 DE L'API (évite le 404 de la v1beta)
    client = genai.Client(api_key=api_key, http_options={'api_version': 'v1'})
    model_id = "gemini-1.5-flash"

    # Lecture du prompt
    prompt_path = os.path.join("prompts", "mega_analysis.txt")
    if not os.path.exists(prompt_path):
        prompt_path = os.path.join("prompts", "system.txt")
    
    with open(prompt_path, "r", encoding="utf-8") as f:
        system_prompt = f.read()

    candidates = []
    logging.info(f"🚀 Scan en cours avec Gemini 1.5 Flash (API v1)")

    for market in markets:
        try:
            # Appel API
            response = client.models.generate_content(
                model=model_id,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.1,
                    response_mime_type="application/json"
                ),
                contents=f"Analyse ce marché : {market.get('question')} | Données : {market}"
            )
            
            if response.text:
                analysis = json.loads(clean_json_response(response.text))
                
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
            
            # Rate limit pour le plan gratuit (15 RPM)
            time.sleep(4) 

        except Exception as e:
            logging.error(f"Erreur sur {market.get('question')} : {e}")
            # Enregistrement de l'erreur dans le CSV
            append_to_csv([time.strftime("%Y-%m-%d %H:%M:%S"), market.get('question'), market.get('id'), market.get('volume'), market.get('liquidity'), "ERROR_API", "N/A", 0, 0, str(e)])

    return {"decision": "SCAN_COMPLETED", "count": len(candidates), "markets": candidates}
    
