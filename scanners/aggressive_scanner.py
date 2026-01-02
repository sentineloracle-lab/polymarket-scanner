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
        search = tavily.search(query=f"{question} news", search_depth="advanced", max_results=3, include_answer=True)
        return f"RÉSUMÉ: {search.get('answer', 'N/A')}"
    except: return "News indisponibles."

def run_aggressive_scanner(markets, prompts_dir):
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    model = "llama-3.1-8b-instant"
    candidates = []

    for i in range(0, len(markets), 4):
        batch = markets[i:i + 4]
        try:
            batch_data = [{"id": m.get('id'), "q": m.get('question'), "p_YES": m.get('price_yes'), "p_NO": m.get('price_no')} for m in batch]
            
            completion = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "Trader bot. Return ONLY JSON: {'results': [{'id': '...', 'decision': 'OPPORTUNITY', 'action': 'BUY_YES'}]}"},
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
                                {"role": "system", "content": "Return ONLY JSON: {'valid': bool, 'reason': 'string', 'conf': int}"},
                                {"role": "user", "content": f"Market: {m.get('question')}\nNews: {news}"}
                            ],
                            response_format={"type": "json_object"}
                        )
                        v = json.loads(clean_json_response(val.choices[0].message.content))
                        
                        if v.get('valid') and v.get('conf', 0) > 80:
                            is_yes = "YES" in res.get('action').upper()
                            price = m.get('price_yes') if is_yes else m.get('price_no')
                            
                            # Logique de calcul des parts pour le message
                            shares = SUGGESTED_BET_USD / price if price > 0 else 0

                            # --- SAUVEGARDE JOURNAL ---
                            log_to_journal(m.get('id'), m.get('question'), res.get('action'), price, v.get('conf'), v.get('reason'))
                            
                            # --- ENVOI TELEGRAM (FORMAT COMPLET REPRIS) ---
                            msg = (f"🔥 *OPPORTUNITÉ CONFIRMÉE*\n\n"
                                   f"📋 *Marché:* {m.get('question')}\n"
                                   f"🎯 *CIBLE:* {'OUI (YES)' if is_yes else 'NON (NO)'}\n"
                                   f"💲 *Prix:* {price} cts/part\n"
                                   f"💵 *MISE:* {SUGGESTED_BET_USD}$\n"
                                   f"📈 *Parts:* ~{int(shares)}\n\n"
                                   f"🧠 *Analyse:* {v.get('reason')}\n"
                                   f"📡 *News:* {news[:150]}...")
                            
                            send_message(msg)
                            candidates.append(m)
            
            time.sleep(PAUSE_BETWEEN_GROQ)
        except Exception as e: 
            logging.error(f"Erreur batch: {e}")
            
    return {"count": len(candidates)}
