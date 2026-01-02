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

def append_to_csv(rows):
    file_path = "scan_history.csv"
    file_exists = os.path.isfile(file_path)
    with open(file_path, mode='a', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Timestamp", "Question", "ID", "Volume", "Liquidity", "Decision", "Strategy", "Confidence", "Edge", "Risk_Flags"])
        writer.writerows(rows)

def run_aggressive_scanner(markets, prompts_dir):
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key: return {"decision": "ERROR", "count": 0}

    client = Groq(api_key=api_key)
    model_id = "llama3-8b-8192" 

    # ON ANALYSE TOUT (Le filtrage a déjà été fait en amont dans main.py ou l'API)
    active_markets = markets 
    
    system_prompt = "Tu es un expert en marchés de prédiction. Analyse les marchés fournis et réponds UNIQUEMENT par un objet JSON contenant une liste 'results'."

    batch_size = 10
    candidates = []
    
    logging.info(f"🚀 Analyse de {len(active_markets)} marchés en cours...")

    for i in range(0, len(active_markets), batch_size):
        batch = active_markets[i:i + batch_size]
        try:
            batch_data = [{"id": m.get('id'), "q": m.get('question')} for m in batch]
            
            completion = client.chat.completions.create(
                model=model_id,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Analyse ces marchés et indique les opportunités (OPPORTUNITY/REJECTED): {json.dumps(batch_data)}"}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            raw_res = completion.choices[0].message.content
            data = json.loads(clean_json_response(raw_res))
            results = data.get('results', [])
            
            csv_buffer = []
            for j, res in enumerate(results):
                # On recréé un lien avec le marché original
                m = batch[j] if j < len(batch) else {}
                decision = res.get('decision', 'REJECTED')
                
                csv_buffer.append([
                    time.strftime("%Y-%m-%d %H:%M:%S"), m.get('question'), m.get('id'),
                    m.get('volume'), m.get('liquidity'), decision, "Batch Analysis",
                    res.get('confidence_score', 0), 0, "[]"
                ])
                
                if decision == "OPPORTUNITY":
                    candidates.append(m)
                    logging.info(f"🟢 OPPORTUNITÉ : {m.get('question')}")

            append_to_csv(csv_buffer)
            logging.info(f"📦 Batch {i//batch_size + 1} terminé.")
            time.sleep(1) 

        except Exception as e:
            logging.error(f"Erreur batch {i}: {e}")

    return {"decision": "SCAN_COMPLETED", "count": len(candidates), "markets": candidates}
    
