import json
import re
import logging
from datetime import datetime
from openai import OpenAI
import os

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def clean_json_response(raw_text):
    """
    Extrait le bloc JSON d'une réponse texte, même si l'IA ajoute du texte parasite.
    Ceci corrige l'erreur 'Expecting property name enclosed in double quotes'.
    """
    try:
        # Cherche le contenu entre les premières et dernières accolades { ... }
        match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if match:
            return match.group(0)
        return raw_text
    except Exception as e:
        logging.error(f"Erreur lors du nettoyage JSON : {e}")
        return raw_text

def analyze_market_with_ai(client, market_data, news_context):
    """
    Envoie les données au LLM et récupère une analyse structurée.
    """
    prompt_path = os.path.join("instructions", "ai_prompt.txt")
    with open(prompt_path, "r", encoding="utf-8") as f:
        system_prompt = f.read()

    user_message = f"""
    MARKET TO ANALYZE:
    - Question: {market_data['question']}
    - Volume Total: {market_data['volume']}
    - Liquidity: {market_data['liquidity']}
    - Current Prices: {market_data['prices']}
    
    NEWS CONTEXT:
    {news_context}
    """

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile", # Ou ton modèle Groq habituel
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.1, # Bas pour plus de stabilité JSON
            response_format={"type": "json_object"}
        )
        
        return response
    except Exception as e:
        logging.error(f"Erreur API LLM : {e}")
        return None

def process_ai_decision(market_data, ai_response):
    """
    Traite la réponse de l'IA avec une validation stricte et correction de logique.
    """
    if not ai_response:
        return "ERROR_API", "N/A", 0, 0, ["API Call failed"]

    raw_content = ai_response.choices[0].message.content
    cleaned_content = clean_json_response(raw_content)
    
    try:
        analysis = json.loads(cleaned_content)
        
        # 1. Validation des champs requis
        required = ["decision", "confidence_score", "strategy"]
        if not all(k in analysis for k in required):
            return "ERROR_JSON_INCOMPLETE", "N/A", 0, 0, []

        decision = analysis['decision']
        strategy = analysis['strategy']
        confidence = analysis['confidence_score']
        edge = analysis.get('edge_estimate', 0)
        risk_flags = analysis.get('risk_flags', [])

        # 2. Correction automatique de la logique de Volume/Slippage
        # Si la liquidité est suffisante (> 200$), on ignore les erreurs de l'IA sur le volume
        if market_data.get('liquidity', 0) > 200:
            risk_flags = [f for f in risk_flags if "volume" not in f.lower() and "slippage" not in f.lower()]
            # Si le seul blocage était le volume, on pourrait repasser en OPPORTUNITY 
            # mais on respecte ici le choix de l'IA par sécurité.
            
        return decision, strategy, confidence, edge, risk_flags

    except json.JSONDecodeError as e:
        logging.error(f"JSON Crash sur le marché {market_data['id']}: {cleaned_content}")
        return "ERROR_JSON_FORMAT", "N/A", 0, 0, [str(e)]
