import json
import re
import logging
import os
import csv
import time
from groq import Groq

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def clean_json_response(raw_text):
    try:
        text = re.sub(r'```json|```', '', raw_text)
        match = re.search(r'\[.*\]|\{.*\}', text, re.DOTALL)
        return match.group(0) if match else text.strip()
    except: return raw_text

def run_aggressive_scanner(markets, prompts_dir):
    api_key = os.getenv("GROQ_API_KEY")
    client = Groq(api_key=api_key)
    
    # ÉTAPE 1 : TRI MASSIF (Modèle 8B - Très peu coûteux en quota)
    # On peut passer à 500 marchés ici dans polymarket.py
    model_fast = "llama-3.1-8b-instant"
    
    logging.info(f"⚡ Étape 1 : Tri rapide de {len(markets)} marchés...")
    pre_selected = []
    batch_size = 20 # On peut faire des plus gros batches pour le tri

    for i in range(0, len(markets), batch_size):
        batch = markets[i:i + batch_size]
        try:
            batch_data = [{"id": m.get('id'), "q": m.get('question')} for m in batch]
            completion = client.chat.completions.create(
                model=model_fast,
                messages=[{"role": "system", "content": "Tu es un trieur. Réponds en JSON avec une liste 'keep' contenant les IDs des marchés qui ont un potentiel de profit ou une anomalie. Sois permissif."},
                          {"role": "user", "content": json.dumps(batch_data)}],
                response_format={"type": "json_object"}
            )
            data = json.loads(clean_json_response(completion.choices[0].message.content))
            keep_ids = data.get('keep', [])
            pre_selected.extend([m for m in batch if m.get('id') in keep_ids])
            time.sleep(1)
        except Exception as e:
            logging.error(f"Erreur Tri : {e}")

    logging.info(f"🎯 {len(pre_selected)} marchés retenus pour analyse approfondie.")

    # ÉTAPE 2 : ANALYSE STRATÉGIQUE (Modèle 70B - Uniquement sur la sélection)
    if not pre_selected:
        return {"decision": "SCAN_COMPLETED", "count": 0, "markets": []}

    model_smart = "llama-3.3-70b-versatile"
    candidates = []
    
    # Chargement du vrai prompt stratégique
    with open(os.path.join("prompts", "mega_analysis.txt"), "r", encoding="utf-8") as f:
        instructions = f.read()

    for m in pre_selected:
        try:
            completion = client.chat.completions.create(
                model=model_smart,
                messages=[{"role": "system", "content": instructions},
                          {"role": "user", "content": f"Analyze: {m.get('question')}"}],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            res = json.loads(clean_json_response(completion.choices[0].message.content))
            
            if res.get('decision') == "OPPORTUNITY" and res.get('confidence_score', 0) >= 80:
                candidates.append(m)
                logging.info(f"🟢 OPPORTUNITÉ : {m.get('question')}")
            
            time.sleep(2) # On ménage le 70B
        except Exception as e:
            logging.error(f"Erreur Analyse 70B : {e}")

    return {"decision": "SCAN_COMPLETED", "count": len(candidates), "markets": candidates}
