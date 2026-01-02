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

def get_smart_search_query(question):
    """Génère une requête de recherche ultra-ciblée selon le contexte."""
    q = question.lower()
    # Mots-clés de rupture selon le domaine
    if any(word in q for word in ["vs", "fc", "united", "city", "real", "cup", "league"]):
        return f"{question} injury news, starting lineup rumors, latest team news"
    elif any(word in q for word in ["election", "president", "trump", "biden", "senate", "poll"]):
        return f"{question} latest poll results, breaking political news, prediction market analysis"
    elif any(word in q for word in ["temperature", "weather", "rain", "snow"]):
        return f"{question} official weather forecast, historical records, climate data"
    else:
        return f"{question} latest breaking news, status update, expert analysis"

def get_real_time_news(question):
    """Recherche approfondie avec requêtes optimisées."""
    try:
        tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
        query = get_smart_search_query(question)
        logging.info(f"🔎 Recherche Tavily optimisée : {query}")
        
        # On utilise search_depth="advanced" et on demande spécifiquement des news
        search = tavily.search(
            query=query, 
            search_depth="advanced", 
            max_results=5,
            include_answer=True # Tavily essaiera de résumer lui-même
        )
        
        context = ""
        # On récupère l'IA answer de Tavily si elle existe, sinon les snippets
        if search.get('answer'):
            context = f"RÉSUMÉ TAVILY : {search.get('answer')}\n\n"
        
        for result in search.get('results', []):
            context += f"• {result['title']}: {result['content'][:300]}...\n"
            
        return context if context else "Aucune info pertinente trouvée."
    except Exception as e:
        logging.error(f"Erreur Tavily: {e}")
        return "Erreur lors de la recherche de news."

def run_aggressive_scanner(markets, prompts_dir):
    api_key = os.getenv("GROQ_API_KEY")
    client = Groq(api_key=api_key)
    model_fast = "llama-3.1-8b-instant"
    
    # Nouveau prompt système pour forcer l'IA à être critique vis-à-vis des news
    instructions = """Tu es un analyste financier de haut niveau. 
    Ta mission est de confronter les cotes de Polymarket aux dernières informations du terrain.
    - Si les news confirment un avantage non reflété dans le prix -> OPPORTUNITY.
    - Si les news sont vagues ou contredisent l'opportunité -> REJECTED."""

    logging.info(f"⚡ Scan High-Precision sur {len(markets)} marchés...")
    candidates = []
    batch_size = 5

    for i in range(0, len(markets), batch_size):
        batch = markets[i:i + batch_size]
        try:
            batch_data = [{"id": m.get('id'), "q": m.get('question'), "vol": m.get('volume'), "p_YES": m.get('price_yes'), "p_NO": m.get('price_no')} for m in batch]
            
            completion = client.chat.completions.create(
                model=model_fast,
                messages=[
                    {"role": "system", "content": f"Analyse ces marchés et identifie les anomalies de prix. Réponds en JSON: {{'results': [{{'id': '...', 'decision': 'OPPORTUNITY'|'REJECTED', 'action': '...', 'amount': '...', 'reason': '...'}}]}}"},
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
                        news_context = get_real_time_news(m.get('question'))
                        
                        # VALIDATION FINALE avec un prompt beaucoup plus sévère
                        validation = client.chat.completions.create(
                            model=model_fast,
                            messages=[
                                {"role": "system", "content": "Tu dois valider un trade. Sois extrêmement critique. Si les news n'apportent pas de preuve concrète (blessure, sondage précis, annonce), rejette le trade. Réponds en JSON: {'valid': true/false, 'final_reason': '...', 'confidence': 0-100}"},
                                {"role": "user", "content": f"Marché: {m.get('question')}\nAction: {res.get('action')}\nNews:\n{news_context}"}
                            ],
                            response_format={"type": "json_object"}
                        )
                        
                        v_data = json.loads(clean_json_response(validation.choices[0].message.content))
                        
                        if v_data.get('valid') is True and v_data.get('confidence', 0) > 75:
                            current_price = m.get('price_yes') if "YES" in res.get('action') else m.get('price_no')
                            msg = (f"🔥 *OPPORTUNITÉ CONFIRMÉE*\n\n"
                                   f"❓ *Marché:* {m.get('question')}\n"
                                   f"📊 *Volume:* {m.get('volume')}$\n"
                                   f"💲 *Prix:* {current_price} cts\n"
                                   f"👉 *ACTION:* {res.get('action')}\n"
                                   f"💵 *Mise:* {res.get('amount')}\n\n"
                                   f"🧠 *Analyse Expert:* {v_data.get('final_reason')}\n\n"
                                   f"📡 *Infos trouvées:* {news_context[:200]}...")
                            
                            send_message(msg)
                            candidates.append(m)

            time.sleep(2) 
            
        except Exception as e:
            logging.error(f"Erreur : {e}")

    return {"decision": "SCAN_COMPLETED", "count": len(candidates), "markets": candidates}
