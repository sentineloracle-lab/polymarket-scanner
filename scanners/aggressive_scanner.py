import json
import re
import logging
import os
import time
from groq import Groq
from telegram_client import send_message # On utilise ton client existant

def clean_json_response(raw_text):
    try:
        text = re.sub(r'```json|```', '', raw_text)
        match = re.search(r'\[.*\]|\{.*\}', text, re.DOTALL)
        return match.group(0) if match else text.strip()
    except: return raw_text

def run_aggressive_scanner(markets, prompts_dir):
    api_key = os.getenv("GROQ_API_KEY")
    client = Groq(api_key=api_key)
    model_fast = "llama-3.1-8b-instant"
    
    instructions = "Expert en arbitrage. Détecte les opportunités réelles (Sport, Politique, News). Ignore les variations de prix Crypto. Réponds en JSON."

    logging.info(f"⚡ Analyse de {len(markets)} marchés...")
    candidates = []
    batch_size = 8 

    for i in range(0, len(markets), batch_size):
        batch = markets[i:i + batch_size]
        try:
            batch_data = [{"id": m.get('id'), "q": m.get('question'), "vol": m.get('volume')} for m in batch]
            
            completion = client.chat.completions.create(
                model=model_fast,
                messages=[
                    {"role": "system", "content": f"{instructions}\nRéponds UNIQUEMENT en JSON: {{'results': [{{'id': '...', 'decision': 'OPPORTUNITY'|'REJECTED', 'confidence_score': 0-100, 'reason': '...'}}]}}"},
                    {"role": "user", "content": json.dumps(batch_data)}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            data = json.loads(clean_json_response(completion.choices[0].message.content))
            results = data.get('results', [])
            
            for res in results:
                if res.get('decision') == "OPPORTUNITY" and res.get('confidence_score', 0) >= 80:
                    m = next((item for item in batch if str(item["id"]) == str(res.get('id'))), None)
                    if m:
                        # --- ENVOI DIRECT TELEGRAM ---
                        msg = (f"🎯 *NOUVELLE OPPORTUNITÉ*\n\n"
                               f"❓ *Question:* {m.get('question')}\n"
                               f"📊 *Volume:* {m.get('volume')}$\n"
                               f"🚀 *Confiance:* {res.get('confidence_score')}%\n"
                               f"📝 *Raison:* {res.get('reason')}")
                        send_message(msg)
                        # ----------------------------
                        candidates.append(m)
                        logging.info(f"✅ Alerte envoyée pour : {m.get('question')}")

            time.sleep(2.2) # Pour éviter l'erreur 429
            
        except Exception as e:
            if "429" in str(e):
                time.sleep(10)
            else:
                logging.error(f"Erreur : {e}")

    return {"decision": "SCAN_COMPLETED", "count": len(candidates), "markets": candidates}
