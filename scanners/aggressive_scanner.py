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
    
    # NOUVEAU PROMPT : On lui apprend à être un trader
    instructions = """Tu es un conseiller en paris sportifs et politiques expert.
    Ta mission : Identifier si le prix actuel (Cote) est sous-évalué ou sur-évalué.
    
    RÈGLES D'ACTION :
    - Si un événement est TRÈS probable mais que le prix YES est bas (<0.60) -> RECOMMANDATION : BUY YES.
    - Si un événement est PEU probable mais que le prix YES est haut (>0.40) -> RECOMMANDATION : BUY NO.
    - Calcul du montant (Mise) :
       * Confiance 90%+ -> Mise Fort (50$)
       * Confiance 80-90% -> Mise Moyenne (20$)
       * Confiance <80% -> REJECTED
    """

    logging.info(f"⚡ Analyse Advisor de {len(markets)} marchés...")
    candidates = []
    batch_size = 5 # Petit batch pour laisser l'IA réfléchir aux prix

    for i in range(0, len(markets), batch_size):
        batch = markets[i:i + batch_size]
        try:
            # On envoie les prix à l'IA maintenant
            batch_data = [{
                "id": m.get('id'), 
                "q": m.get('question'), 
                "price_YES": m.get('price_yes'),
                "price_NO": m.get('price_no')
            } for m in batch]
            
            completion = client.chat.completions.create(
                model=model_fast,
                messages=[
                    {"role": "system", "content": f"{instructions}\nRéponds UNIQUEMENT en JSON: {{'results': [{{'id': '...', 'decision': 'OPPORTUNITY'|'REJECTED', 'action': 'BUY YES'|'BUY NO', 'amount': '20$', 'reason': 'Court et précis'}}]}}"},
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
                        # --- MESSAGE TELEGRAM AMÉLIORÉ ---
                        price_display = m.get('price_yes') if 'YES' in res.get('action') else m.get('price_no')
                        
                        msg = (f"💰 *CONSEIL TRADING*\n\n"
                               f"❓ *Marché:* {m.get('question')}\n"
                               f"💲 *Prix actuel:* {price_display} cts\n"
                               f"👉 *ACTION:* {res.get('action')}\n"
                               f"💵 *Mise conseillée:* {res.get('amount')}\n\n"
                               f"📝 *Analyse:* {res.get('reason')}")
                        
                        send_message(msg)
                        logging.info(f"✅ Conseil envoyé : {res.get('action')} sur {m.get('question')}")
                        candidates.append(m)

            time.sleep(2) 
            
        except Exception as e:
            if "429" in str(e): time.sleep(10)
            else: logging.error(f"Erreur : {e}")

    return {"decision": "SCAN_COMPLETED", "count": len(candidates), "markets": candidates}
