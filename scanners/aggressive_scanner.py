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
    try:
        match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if match:
            return match.group(0)
        return raw_text
    except Exception:
        return raw_text

def append_to_csv(row):
    """Enregistre chaque analyse, même en cas d'erreur."""
    file_path = "scan_history.csv"
    file_exists = os.path.isfile(file_path)
    with open(file_path, mode='a', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Timestamp", "Question", "ID", "Volume", "Liquidity", "Decision", "Strategy", "Confidence", "Edge", "Risk_Flags"])
        writer.writerow(row)

def analyze_market_with_ai(client, market_data, news_context):
    prompt_path = os.path.join("prompts", "mega_analyst.txt")
    if not os.path.exists(prompt_path):
        prompt_path = os.path.join("prompts", "system.txt")
        
    with open(prompt_path, "r", encoding="utf-8") as f:
        system_prompt = f.read()

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"MARKET: {market_data['question']} | DATA: {market_data}"}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        return response
    except Exception as e:
        logging.error(f"Erreur API LLM : {e}")
        return None

def run_aggressive_scanner(markets, prompts_dir):
    client = OpenAI(api_key=os.environ.get("GROQ_API_KEY"), base_url="https://api.groq.com/openai/v1")
    candidates = []
    
    for market in markets:
        ai_res = analyze_market_with_ai(client, market, "No news context.")
        
        if ai_res:
            try:
                raw_content = ai_res.choices[0].message.content
                analysis = json.loads(clean_json_response(raw_content))
                
                decision = analysis.get('decision', 'REJECTED_AI')
                conf = analysis.get('confidence_score', 0)
                
                # Sauvegarde CSV
                append_to_csv([time.strftime("%Y-%m-%d %H:%M:%S"), market['question'], market['id'], market['volume'], market['liquidity'], decision, analysis.get('strategy'), conf, analysis.get('edge_estimate'), str(analysis.get('risk_flags'))])
                
                if decision == "OPPORTUNITY" and conf >= 80:
                    candidates.append(market)
            except:
                append_to_csv([time.strftime("%Y-%m-%d %H:%M:%S"), market['question'], market['id'], market['volume'], market['liquidity'], "ERROR_JSON", "N/A", 0, 0, "Parse error"])
        else:
            # Si l'API Rate Limit (Erreur 429), on note l'erreur dans le CSV
            append_to_csv([time.strftime("%Y-%m-%d %H:%M:%S"), market['question'], market['id'], market['volume'], market['liquidity'], "ERROR_RATE_LIMIT", "N/A", 0, 0, "Quota journalier atteint"])

    return {"decision": "SCAN_COMPLETED", "count": len(candidates), "markets": candidates}
