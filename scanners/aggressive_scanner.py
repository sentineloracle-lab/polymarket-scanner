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
    
    # On utilise le 8B pour TOUT afin d'éviter le blocage TPD (Daily Limit)
    # Ce modèle est ultra-rapide et gratuit pour de gros volumes
    model_fast = "llama-3.1-8b-instant"
    
    # Chargement du prompt stratégique
    with open(os.path.join("prompts", "mega_analysis.txt"), "r", encoding="utf-8") as f:
        instructions = f.read()

    logging.info(f"⚡ Analyse de {len(markets)} marchés avec {model_fast}...")
    
    candidates = []
    batch_size = 5 # Batch réduit pour plus de précision par marché

    for i in range(0, len(markets), batch_size):
        batch = markets[i:i + batch_size]
        try:
            batch_data = [{"id": m.get('id'), "q": m.get('question'), "vol": m.get('volume')} for m in batch]
            
            completion = client.chat.completions.create(
                model=model_fast,
                messages=[
                    {"role": "system", "content": f"{instructions}\n\nRéponds UNIQUEMENT en JSON sous la forme: {{'results': [{{'id': '...', 'decision': 'OPPORTUNITY' ou 'REJECTED', 'confidence_score': 0-100}}]}}"},
                    {"role": "user", "content": json.dumps(batch_data)}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            data = json.loads(clean_json_response(completion.choices[0].message.content))
            results = data.get('results', [])
            
            for j, res in enumerate(results):
                m = batch[j] if j < len(batch) else {}
                # Seuil de confiance abaissé à 75 pour le modèle 8B
                if res.get('decision') == "OPPORTUNITY" and res.get('confidence_score', 0) >= 75:
                    candidates.append(m)
                    logging.info(f"🟢 OPPORTUNITÉ : {m.get('question')}")

            logging.info(f"📦 Batch {i//batch_size + 1} terminé.")
            time.sleep(1.5) # Protection contre le Rate Limit par minute
            
        except Exception as e:
            logging.error(f"Erreur Batch {i}: {e}")
            time.sleep(2)

    return {"decision": "SCAN_COMPLETED", "count": len(candidates), "markets": candidates}
