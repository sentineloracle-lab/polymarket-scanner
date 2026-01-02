import json
import re
import logging
import os
import time
from groq import Groq
from telegram_client import send_message

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
    
    # Prompt affiné pour forcer des raisons contextuelles
    instructions = """Tu es un analyste expert en paris.
    Objectif : Trouver des erreurs de prix (Value Bet).
    
    RÈGLES :
    1. Compare le Prix (Cote) à la probabilité réelle de l'événement.
    2. Si Probabilité Réelle >> Prix du marché -> OPPORTUNITY.
    3. Action : 'BUY YES' (si sous-coté) ou 'BUY NO' (si sur-coté).
    4. Mise : 50$ (Confiance >90%), 20$ (Confiance >80%).
    
    IMPORTANT : Dans le champ 'reason', ne dis pas juste "bonne probabilité". Donne un argument contextuel (ex: "L'équipe joue à domicile", "Le candidat est en tête des sondages", etc.)."""

    logging.info(f"⚡ Analyse Advisor de {len(markets)} marchés...")
    candidates = []
    batch_size = 5

    for i in range(0, len(markets), batch_size):
        batch = markets[i:i + batch_size]
        try:
            batch_data = [{
                "id": m.get('id'), 
                "q": m.get('question'), 
                "vol": m.get('volume'), # On passe le volume à l'IA aussi
                "price_YES": m.get('price_yes'),
                "price_NO": m.get('price_no')
            } for m in batch]
            
            completion = client.chat.completions.create(
                model=model_fast,
                messages=[
                    {"role": "system", "content": f"{instructions}\nRéponds UNIQUEMENT en JSON: {{'results': [{{'id': '...', 'decision': 'OPPORTUNITY'|'REJECTED', 'action': 'BUY YES'|'BUY NO', 'amount': '20$', 'reason': '...'}}]}}"},
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
                        # Logique d'affichage du prix correct
                        if "YES" in res.get('action'):
                            current_price = m.get('price_yes')
                        else:
                            current_price = m.get('price_no')
                        
                        # --- FORMAT DU MESSAGE (Volume + Raison) ---
                        msg = (f"💰 *CONSEIL TRADING*\n\n"
                               f"❓ *Marché:* {m.get('question')}\n"
                               f"📊 *Volume:* {m.get('volume')}$\n"
                               f"💲 *Prix payé:* {current_price} cts\n"
                               f"👉 *ACTION:* {res.get('action')}\n"
                               f"💵 *Mise:* {res.get('amount')}\n\n"
                               f"📝 *Raison:* {res.get('reason')}")
                        # -------------------------------------------
                        
                        send_message(msg)
                        logging.info(f"✅ Conseil envoyé : {m.get('question')}")
                        candidates.append(m)

            time.sleep(2) 
            
        except Exception as e:
            if "429" in str(e): time.sleep(10)
            else: logging.error(f"Erreur : {e}")

    return {"decision": "SCAN_COMPLETED", "count": len(candidates), "markets": candidates}
