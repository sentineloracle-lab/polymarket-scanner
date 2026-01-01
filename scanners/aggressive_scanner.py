import json
import re
import logging
import os
import csv
import time
from openai import OpenAI

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def clean_json_response(raw_text):
    """Nettoie la réponse pour n'extraire que le bloc JSON."""
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

def get_ai_client():
    """Initialise le client Google Gemini avec le bon nom de modèle."""
    gemini_key = os.getenv("GEMINI_API_KEY")
    logging.info("Système : Initialisation du client GOOGLE GEMINI")
    # Pour Gemini via OpenAI, le nom du modèle doit souvent être préfixé ou exact
    return OpenAI(
        api_key=gemini_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    ), "gemini-1.5-flash" # Le nom du modèle sans astérisques

def analyze_market_with_ai(client, model_name, market_data):
    # Chemin exact vers ton fichier
    prompt_path = os.path.join("prompts", "mega_analysis.txt")
    
    if not os.path.exists(prompt_path):
        prompt_path = os.path.join("prompts", "system.txt")
        
    if not os.path.exists(prompt_path):
        logging.error("ERREUR : Aucun fichier de prompt trouvé.")
        return None

    with open(prompt_path, "r", encoding="utf-8") as f:
        system_prompt = f.read()

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"MARKET: {market_data['question']} | DATA: {market_data}"}
            ],
            temperature=0.1,
        )
        return response
    except Exception as e:
        # Si le modèle simple échoue, on tente avec le préfixe complet exigé par certaines versions de l'API
        if "not found" in str(e).lower() and model_name == "gemini-1.5-flash":
            logging.info("Tentative avec le préfixe models/...")
            try:
                return client.chat.completions.create(
                    model="models/gemini-1.5-flash",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"MARKET: {market_data['question']} | DATA: {market_data}"}
                    ],
                    temperature=0.1,
                )
            except Exception as e2:
                logging.error(f"Échec définitif Gemini : {e2}")
                return None
        logging.error(f"Erreur API LLM ({model_name}) : {e}")
        return None

def run_aggressive_scanner(markets, prompts_dir):
    client, model_name = get_ai_client()
    candidates = []
    
    logging.info(f"Démarrage du scan avec {model_name}")

    for market in markets:
        ai_res = analyze_market_with_ai(client, model_name, market)
        
        if ai_res:
            try:
                raw_content = ai_res.choices[0].message.content
                analysis = json.loads(clean_json_response(raw_content))
                
                decision = analysis.get('decision', 'REJECTED_AI')
                conf = analysis.get('confidence_score', 0)
                
                append_to_csv([
                    time.strftime("%Y-%m-%d %H:%M:%S"), 
                    market['question'], market['id'], market['volume'], 
                    market['liquidity'], decision, analysis.get('strategy'), 
                    conf, analysis.get('edge_estimate'), str(analysis.get('risk_flags'))
                ])
                
                if decision == "OPPORTUNITY" and conf >= 80:
                    candidates.append(market)
                    logging.info(f"🟢 OPPORTUNITÉ : {market['question']}")
            except Exception as e:
                logging.error(f"Erreur parsing JSON : {e}")
                append_to_csv([time.strftime("%Y-%m-%d %H:%M:%S"), market['question'], market['id'], market['volume'], market['liquidity'], "ERROR_JSON", "N/A", 0, 0, str(e)])
        else:
            append_to_csv([time.strftime("%Y-%m-%d %H:%M:%S"), market['question'], market['id'], market['volume'], market['liquidity'], "ERROR_API_GEMINI", "N/A", 0, 0, "Erreur 404 ou 429"])

    return {"decision": "SCAN_COMPLETED", "count": len(candidates), "markets": candidates}
