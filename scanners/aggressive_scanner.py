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
        # Nettoyage des balises Markdown si présentes (ex: ```json ... ```)
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
    """Version ultra-compatible du scanner pour Google Gemini."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logging.error("GEMINI_API_KEY manquante.")
        return {"decision": "ERROR", "count": 0}

    # On retire l'option api_version pour laisser le SDK gérer par défaut, 
    # mais on simplifie la configuration de génération.
    client = genai.Client(api_key=api_key)
    model_id = "gemini-1.5-flash"

    # Lecture du prompt
    prompt_path = os.path.join("prompts", "mega_analysis.txt")
    if not os.path.exists(prompt_path):
        prompt_path = os.path.join("prompts", "system.txt")
    
    with open(prompt_path, "r", encoding="utf-8") as f:
        system_instructions = f.read()

    candidates = []
    logging.info(f"🚀 Scan en cours : Mode compatibilité Gemini activé")

    for market in markets:
        try:
            # On fusionne les instructions système et les données car l'endpoint v1 
            # rejette parfois le champ séparé 'system_instruction' selon la région.
            full_prompt = f"{system_instructions}\n\nANALYSE LE MARCHÉ SUIVANT :\n{market}"

            response = client.models.generate_content(
                model=model_id,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1
                )
            )
            
            if response.text:
                cleaned_json = clean_json_response(response.text)
                analysis = json.loads(cleaned_json)
                
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
            
            # Délai pour le quota gratuit
            time.sleep(4) 

        except Exception as e:
            logging.error(f"Erreur sur {market.get('question')} : {e}")
            append_to_csv([time.strftime("%Y-%m-%d %H:%M:%S"), market.get('question'), market.get('id'), market.get('volume'), market.get('liquidity'), "ERROR_API", "N/A", 0, 0, str(e)])

    return {"decision": "SCAN_COMPLETED", "count": len(candidates), "markets": candidates}
