import json
import re
import logging
import os
import csv
import time
import google.generativeai as genai

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def clean_json_response(raw_text):
    """Extrait le bloc JSON d'une réponse texte."""
    try:
        # Cherche le premier '{' et le dernier '}'
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
    """Fonction principale utilisant le SDK officiel Google Gemini."""
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        logging.error("GEMINI_API_KEY manquante dans les variables d'environnement.")
        return {"decision": "ERROR", "count": 0}

    # Configuration du SDK Google
    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # Lecture du prompt
    prompt_path = os.path.join("prompts", "mega_analysis.txt")
    if not os.path.exists(prompt_path):
        prompt_path = os.path.join("prompts", "system.txt")
    
    with open(prompt_path, "r", encoding="utf-8") as f:
        system_prompt = f.read()

    candidates = []
    logging.info("🚀 Démarrage du scan avec GOOGLE GEMINI (SDK Officiel)")

    for market in markets:
        try:
            user_message = f"MARKET DATA: {market}"
            
            # Appel API Gemini
            response = model.generate_content(
                f"{system_prompt}\n\n{user_message}",
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,
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
            
            # Petite pause pour éviter de saturer le quota gratuit (limit 15 RPM)
            time.sleep(1)

        except Exception as e:
            logging.error(f"Erreur Gemini sur {market.get('question')} : {e}")
            append_to_csv([time.strftime("%Y-%m-%d %H:%M:%S"), market.get('question'), market.get('id'), market.get('volume'), market.get('liquidity'), "ERROR_API", "N/A", 0, 0, str(e)])

    return {"decision": "SCAN_COMPLETED", "count": len(candidates), "markets": candidates}
