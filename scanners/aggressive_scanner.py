import json
import re
import logging
import os
from openai import OpenAI

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def clean_json_response(raw_text):
    """Extrait le bloc JSON d'une réponse texte parasite."""
    try:
        match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if match:
            return match.group(0)
        return raw_text
    except Exception:
        return raw_text

def analyze_market_with_ai(client, market_data, news_context):
    """Envoie les données au LLM."""
    # Utilisation du fichier mega_analyst.txt comme demandé
    prompt_path = os.path.join("instructions", "mega_analyst.txt")
    if not os.path.exists(prompt_path):
        # Fallback au cas où le nom diffèrerait
        prompt_path = os.path.join("instructions", "system.txt")
        
    with open(prompt_path, "r", encoding="utf-8") as f:
        system_prompt = f.read()

    user_message = f"""
    MARKET TO ANALYZE:
    - Question: {market_data.get('question', 'N/A')}
    - Volume Total: {market_data.get('volume', 0)}
    - Liquidity: {market_data.get('liquidity', 0)}
    - Current Prices: {market_data.get('prices', 'N/A')}
    
    NEWS CONTEXT:
    {news_context}
    """

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        return response
    except Exception as e:
        logging.error(f"Erreur API LLM : {e}")
        return None

def process_ai_decision(market_data, ai_response):
    """Traite et valide la réponse JSON de l'IA."""
    if not ai_response:
        return "ERROR_API", "N/A", 0, 0, ["API Call failed"]

    raw_content = ai_response.choices[0].message.content
    cleaned_content = clean_json_response(raw_content)
    
    try:
        analysis = json.loads(cleaned_content)
        decision = analysis.get('decision', 'REJECTED_AI')
        risk_flags = analysis.get('risk_flags', [])

        # Correction de la logique de volume (sécurité liquidité > 200$)
        if market_data.get('liquidity', 0) > 200:
            risk_flags = [f for f in risk_flags if "volume" not in f.lower() and "slippage" not in f.lower()]
            
        return (
            decision,
            analysis.get('strategy', 'N/A'),
            analysis.get('confidence_score', 0),
            analysis.get('edge_estimate', 0),
            risk_flags
        )
    except Exception as e:
        logging.error(f"Erreur décodage JSON : {e}")
        return "ERROR_JSON_FORMAT", "N/A", 0, 0, [str(e)]

def run_aggressive_scanner(markets, prompts_dir):
    """
    FONCTION PRINCIPALE (Ajustée pour main.py)
    """
    # Initialisation du client ici pour éviter le manque d'argument dans main.py
    client = OpenAI(api_key=os.environ.get("GROQ_API_KEY"), base_url="https://api.groq.com/openai/v1")
    
    results = []
    for market in markets:
        # On simule ou appelle une fonction de news si elle existe, sinon texte vide
        news = "Recherche de news en cours..." 
        
        ai_res = analyze_market_with_ai(client, market, news)
        decision, strategy, conf, edge, flags = process_ai_decision(market, ai_res)
        
        results.append({
            "market": market,
            "decision": decision,
            "strategy": strategy,
            "confidence": conf,
            "edge": edge,
            "flags": flags
        })
    return results
