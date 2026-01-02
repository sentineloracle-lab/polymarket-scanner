import json
import re
import logging
import os
import time
from groq import Groq
from telegram_client import send_message
from tavily import TavilyClient

# Configuration
SUGGESTED_BET_USD = 10.0
PAUSE_BETWEEN_GROQ = 3.0  # Pause de sécurité pour éviter l'erreur 429

def clean_json_response(raw_text):
    try:
        text = re.sub(r'```json|```', '', raw_text)
        match = re.search(r'\[.*\]|\{.*\}', text, re.DOTALL)
        return match.group(0) if match else text.strip()
    except: return raw_text

def get_smart_search_query(question):
    """Génère une requête de recherche ultra-ciblée."""
    q = question.lower()
    if any(word in q for word in ["vs", "fc", "united", "city", "real", "cup", "league"]):
        return f"{question} injury news, starting lineup rumors, latest team news"
    elif any(word in q for word in ["election", "president", "trump", "biden", "senate", "poll"]):
        return f"{question} latest poll results, breaking political news"
    return f"{question} latest breaking news, status update"

def get_real_time_news(question):
    """Recherche news via Tavily (limité à 3 résultats pour économiser le quota)."""
    try:
        tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
        query = get_smart_search_query(question)
        search = tavily.search(query=query, search_depth="advanced", max_results=3, include_answer=True)
        
        context = f"RÉSUMÉ: {search.get('answer', 'N/A')}\n"
        for r in search.get('results', []):
            context += f"• {r['title']}\n"
        return context
    except Exception as e:
        return f"Info: Recherche indisponible ({str(e)})"

def run_aggressive_scanner(markets, prompts_dir):
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    model = "llama-3.1-8b-instant"
    
    logging.info(f"⚡ Scan 45min (Anti-429) sur {len(markets)} marchés...")
    candidates = []
    batch_size = 4 

    for i in range(0, len(markets), batch_size):
        batch = markets[i:i + batch_size]
        try:
            batch_data = [{"id": m.get('id'), "q": m.get('question'), "p_YES": m.get('price_yes'), "p_NO": m.get('price_no')} for m in batch]
            
            # Étape 1 : Détection d'anomalie de prix
            completion = client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": "Identifie les anomalies de prix. Réponds en JSON: {'results': [{'id': '...', 'decision': 'OPPORTUNITY'|'REJECTED', 'action': 'BUY_YES'|'BUY_NO'}]}"},
                          {"role": "user", "content": json.dumps(batch_data)}],
                response_format={"type": "json_object"}
            )
            
            data = json.loads(clean_json_response(completion.choices[0].message.content))
            
            for res in data.get('results', []):
                if res.get('decision') == "OPPORTUNITY":
                    m = next((item for item in batch if str(item["id"]) == str(res.get('id'))), None)
                    if m:
                        # Étape 2 : Vérification News
                        news_context = get_real_time_news(m.get('question'))
                        
                        # Étape 3 : Validation Finale IA
                        time.sleep(PAUSE_BETWEEN_GROQ) 
                        val = client.chat.completions.create(
                            model=model,
                            messages=[{"role": "system", "content": "Analyse critique : Valide ce trade avec les news. Réponds en JSON: {'valid': true/false, 'reason': '...', 'conf': 0-100}"},
                                      {"role": "user", "content": f"Marché: {m.get('question')}\nAction: {res.get('action')}\nNews: {news_context}"}],
                            response_format={"type": "json_object"}
                        )
                        
                        v = json.loads(clean_json_response(val.choices[0].message.content))
                        
                        if v.get('valid') and v.get('conf', 0) > 80:
                            is_yes = "YES" in res.get('action').upper()
                            price = m.get('price_yes') if is_yes else m.get('price_no')
                            shares = SUGGESTED_BET_USD / price if price > 0 else 0
                            
                            msg = (f"🔥 *OPPORTUNITÉ CONFIRMÉE*\n\n"
                                   f"📋 *Marché:* {m.get('question')}\n"
                                   f"🎯 *CIBLE:* {'OUI (YES)' if is_yes else 'NON (NO)'}\n"
                                   f"💲 *Prix:* {price} cts/part\n"
                                   f"💵 *MISE:* {SUGGESTED_BET_USD}$\n"
                                   f"📈 *Quantité:* ~{int(shares)} parts\n\n"
                                   f"🧠 *Analyse:* {v.get('reason')}\n"
                                   f"📡 *News:* {news_context[:150]}...")
                            
                            send_message(msg)
                            candidates.append(m)

            # Pause anti-429 entre les lots
            time.sleep(PAUSE_BETWEEN_GROQ)
            
        except Exception as e:
            logging.error(f"Erreur : {e}")
            time.sleep(5)

    return {"decision": "SCAN_FINISHED", "count": len(candidates)}
