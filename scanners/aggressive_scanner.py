import json
import re
import logging
import os
import time
import csv
from datetime import datetime
from groq import Groq
from telegram_client import send_message
from tavily import TavilyClient

SUGGESTED_BET_USD = 10.0
PAUSE_BETWEEN_GROQ = 3.0
JOURNAL_FILE = "trading_journal.csv"

def clean_json_response(raw_text):
    try:
        text = re.sub(r'```json|```', '', raw_text)
        match = re.search(r'\[.*\]|\{.*\}', text, re.DOTALL)
        return match.group(0) if match else text.strip()
    except: return raw_text

def log_to_journal(m_id, question, action, price, confidence, reason):
    file_exists = os.path.isfile(JOURNAL_FILE)
    try:
        with open(JOURNAL_FILE, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(['Date', 'ID', 'Marche', 'Action', 'Prix', 'Confiance', 'Raison'])
            writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M"), m_id, question, action, price, f"{confidence}%", reason])
    except Exception as e:
        logging.error(f"Erreur journal: {e}")

def get_real_time_news(question):
    try:
        tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
        search = tavily.search(query=f"{question} latest news status", search_depth="advanced", max_results=3, include_answer=True)
        return f"RÉSUMÉ: {search.get('answer', 'N/A')}"
    except: return "News indisponibles."

def run_aggressive_scanner(markets, prompts_dir):
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    model = "llama-3.1-8b-instant"
    candidates = []

    # Batch de 4 pour éviter la surcharge
    for i in range(0, len(markets), 4):
        batch = markets[i:i + 4]
        try:
            batch_data = [{"id": m.get('id'), "q": m.get('question'), "p_YES": m.get('price_yes'), "p_NO": m.get('price_no')} for m in batch]
            
            # Prompt strict pour éviter l'erreur 400 (math analytics)
            completion = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a professional trader. Identify price anomalies. Return ONLY JSON: {'results': [{'id': '...', 'decision': 'OPPORTUNITY', 'action': 'BUY_YES'}]}. No commentary."},
                    {"role": "user", "content": json.dumps(batch_data)}
                ],
                response_format={"type": "json_object"}
            )
            
            data = json.loads(clean_json_response(completion.choices[0].message.content))
            
            for res in data.get('results', []):
                if res.get('decision') == "OPPORTUNITY":
                    m = next((item for item in batch if str(item["id"]) == str(res.get('id'))), None)
                    if m:
                        news = get_real_time_news(m.get('question'))
                        time.sleep(PAUSE_BETWEEN_GROQ)
                        
                        val = client.chat.completions.create(
                            model=model,
                            messages=[
                                {"role": "system", "content": "Verify opportunity with news. Return ONLY JSON: {'valid': bool, 'reason': 'string', 'conf': int}"},
                                {"role": "user", "content": f"Market: {m.get('question')}\nNews: {news}"}
                            ],
                            response_format={"type": "json_object"}
                        )
                        v = json.loads(clean_json_response(val.choices[0].message.content))
                        
                        if v.get('valid') and v.get('conf', 0) > 80:
                            is_yes = "YES" in res.get('action').upper()
                            price = m.get('price_yes') if is_yes else m.get('price_no')
                            
                            log_to_journal(m.get('id'), m.get('question'), res.get('action'), price, v.get('conf'), v.get('reason'))
                            send_message(f"🔥 *OPPORTUNITÉ*\n\n{m.get('question')}\n\n🎯 Action: {res.get('action')}\n💰 Prix: {price} cts\n🧠 Raison: {v.get('reason')}")
                            candidates.append(m)
            
            time.sleep(PAUSE_BETWEEN_GROQ)
        except Exception as e: 
            logging.error(f"Erreur batch: {e}")
            time.sleep(5)
            
    return {"count": len(candidates)}
