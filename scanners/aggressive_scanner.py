import json
import re
import logging
import os
import time
import csv
import requests
from datetime import datetime
from groq import Groq
from tavily import TavilyClient

SUGGESTED_BET_USD = 10.0
PAUSE_BETWEEN_GROQ = 3.0
JOURNAL_FILE = "trading_journal.csv"

def quick_send(msg):
    """Envoi direct sans passer par un autre fichier pour éliminer les bugs d'import."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        r = requests.post(url, json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"})
        if r.status_code != 200:
            requests.post(url, json={"chat_id": chat_id, "text": msg}) # Second essai sans Markdown
    except Exception as e:
        logging.error(f"Erreur Telegram: {e}")

def log_to_journal(m_id, question, action, price, confidence, reason):
    file_exists = os.path.isfile(JOURNAL_FILE)
    try:
        with open(JOURNAL_FILE, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(['Date', 'ID', 'Marche', 'Action', 'Prix', 'Confiance', 'Raison'])
            writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M"), m_id, question, action, price, f"{confidence}%", reason])
    except: pass

def run_aggressive_scanner(markets, prompts_dir):
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
    candidates = []

    for i in range(0, len(markets), 4):
        batch = markets[i:i + 4]
        try:
            batch_data = [{"id": m.get('id'), "q": m.get('question'), "p_YES": m.get('price_yes'), "p_NO": m.get('price_no')} for m in batch]
            
            # Étape 1: Détection
            comp = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "system", "content": "Return ONLY JSON: {'results': [{'id': '...', 'decision': 'OPPORTUNITY', 'action': 'BUY_YES'}]}"},
                          {"role": "user", "content": json.dumps(batch_data)}],
                response_format={"type": "json_object"}
            )
            data = json.loads(comp.choices[0].message.content)
            
            for res in data.get('results', []):
                if res.get('decision') == "OPPORTUNITY":
                    m = next((item for item in batch if str(item["id"]) == str(res.get('id'))), None)
                    if m:
                        # Étape 2: News
                        search = tavily.search(query=f"{m.get('question')} latest status news", max_results=2)
                        news_txt = str(search.get('results', []))
                        
                        # Étape 3: Validation
                        time.sleep(PAUSE_BETWEEN_GROQ)
                        val = client.chat.completions.create(
                            model="llama-3.1-8b-instant",
                            messages=[{"role": "system", "content": "Return ONLY JSON: {'valid': bool, 'reason': 'string', 'conf': int}"},
                                      {"role": "user", "content": f"Market: {m.get('question')}\nNews: {news_txt}"}],
                            response_format={"type": "json_object"}
                        )
                        v = json.loads(val.choices[0].message.content)
                        
                        if v.get('valid') and v.get('conf', 0) > 80:
                            is_yes = "YES" in res.get('action').upper()
                            price = m.get('price_yes') if is_yes else m.get('price_no')
                            
                            # Log et Envoi
                            log_to_journal(m.get('id'), m.get('question'), res.get('action'), price, v.get('conf'), v.get('reason'))
                            
                            msg = (f"🔔 *NOUVELLE OPPORTUNITÉ*\n\n"
                                   f"📍 {m.get('question')}\n"
                                   f"💎 Action: {res.get('action')}\n"
                                   f"💰 Prix: {price} cts\n"
                                   f"🧠 {v.get('reason')}")
                            
                            quick_send(msg)
                            candidates.append(m)
            time.sleep(PAUSE_BETWEEN_GROQ)
        except Exception as e:
            logging.error(f"Erreur: {e}")
            
    return {"count": len(candidates)}
