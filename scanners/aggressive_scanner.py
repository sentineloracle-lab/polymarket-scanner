import json
import re
import logging
import os
import time
from groq import Groq
from telegram_client import send_message
from tavily import TavilyClient

def clean_json_response(raw_text):
    try:
        text = re.sub(r'```json|```', '', raw_text)
        match = re.search(r'\[.*\]|\{.*\}', text, re.DOTALL)
        return match.group(0) if match else text.strip()
    except: return raw_text

def get_real_time_news(question):
    """Recherche les dernières infos sur le sujet via Tavily."""
    try:
        tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
        # On cherche des infos très récentes (dernières 24h/48h)
        search = tavily.search(query=f"latest news and status: {question}", search_depth="advanced")
        context = ""
        for result in search.get('results', [])[:3]: # On prend les 3 meilleurs résultats
            context += f"- {result['content'][:200]}...\n"
        return context
    except Exception as e:
        logging.error(f"Erreur Tavily: {e}")
        return "Pas de news récentes trouvées."

def run_aggressive_scanner(markets, prompts_dir):
    api_key = os.getenv("GROQ_API_KEY")
    client = Groq(api_key=api_key)
    model_fast = "llama-3.1-8b-instant"
    
    instructions = """Tu es un analyste pro. Compare Prix vs Probabilité.
    Si tu détectes une opportunité (OPPORTUNITY), propose BUY YES ou BUY NO.
    Sois attentif aux erreurs de côte."""

    logging.info(f"⚡ Analyse Advisor + News sur {len(markets)} marchés...")
    candidates = []
    batch_size = 6

    for i in range(0, len(markets), batch_size):
        batch = markets[i:i + batch_size]
        try:
            batch_data = [{"id": m.get('id'), "q": m.get('question'), "vol": m.get('volume'), "p_YES": m.get('price_yes'), "p_NO": m.get('price_no')} for m in batch]
            
            completion = client.chat.completions.create(
                model=model_fast,
                messages=[
                    {"role": "system", "content": f"{instructions}\nRéponds en JSON: {{'results': [{{'id': '...', 'decision': 'OPPORTUNITY'|'REJECTED', 'action': '...', 'amount': '...', 'reason': '...'}}]}}"},
                    {"role": "user", "content": json.dumps(batch_data)}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            data = json.loads(clean_json_response(completion.choices[0].message.content))
            results = data.get('results', [])
            
            for res in results:
                if res.get('decision') == "OPPORTUNITY":
                    m = next((item for item in batch if str(item["id"]) == str(res.get('id'))), None)
                    if m:
                        # --- LE DOUBLE CHECK TAVILY ---
                        logging.info(f"🔍 Vérification des news pour: {m.get('question')}")
                        news_context = get_real_time_news(m.get('question'))
                        
                        # Deuxième passage IA pour valider avec les news
                        validation = client.chat.completions.create(
                            model=model_fast,
                            messages=[
                                {"role": "system", "content": "Tu es un expert en validation. Voici une opportunité et les news récentes. Confirme si c'est un bon trade. Réponds courtement."},
                                {"role": "user", "content": f"Marché: {m.get('question')}\nAction: {res.get('action')}\nNews:\n{news_context}"}
                            ]
                        )
                        final_reason = validation.choices[0].message.content

                        # --- ENVOI TELEGRAM ---
                        current_price = m.get('price_yes') if "YES" in res.get('action') else m.get('price_no')
                        msg = (f"🔥 *OPPORTUNITÉ CONFIRMÉE*\n\n"
                               f"❓ *Marché:* {m.get('question')}\n"
                               f"📊 *Volume:* {m.get('volume')}$\n"
                               f"💲 *Prix:* {current_price} cts\n"
                               f"👉 *ACTION:* {res.get('action')}\n"
                               f"💵 *Mise:* {res.get('amount')}\n\n"
                               f"🔍 *Infos Temps Réel:* {final_reason}\n\n"
                               f"📌 *Source News:* {news_context[:150]}...")
                        
                        send_message(msg)
                        time.sleep(1) # Petit délai pour Telegram
                        candidates.append(m)

            time.sleep(2) 
            
        except Exception as e:
            if "429" in str(e): time.sleep(10)
            else: logging.error(f"Erreur : {e}")

    return {"decision": "SCAN_COMPLETED", "count": len(candidates), "markets": candidates}
