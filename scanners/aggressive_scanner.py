import json
import re
import logging
import os
import csv
import time
from groq import Groq

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def clean_json_response(raw_text):
    """Nettoie la réponse pour extraire uniquement le bloc JSON."""
    try:
        text = re.sub(r'```json|```', '', raw_text)
        match = re.search(r'\[.*\]|\{.*\}', text, re.DOTALL)
        return match.group(0) if match else text.strip()
    except: return raw_text

def append_to_csv(rows):
    """Enregistre les résultats d'un batch dans le fichier historique."""
    file_path = "scan_history.csv"
    file_exists = os.path.isfile(file_path)
    with open(file_path, mode='a', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Timestamp", "Question", "ID", "Volume", "Liquidity", "Decision", "Strategy", "Confidence", "Edge", "Risk_Flags"])
        writer.writerows(rows)

def run_aggressive_scanner(markets, prompts_dir):
    """Analyse les marchés par batches avec Groq en utilisant les prompts système."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key: 
        logging.error("GROQ_API_KEY non trouvée.")
        return {"decision": "ERROR", "count": 0}

    client = Groq(api_key=api_key)
    
    # Choix du modèle : 
    # 'llama-3.1-8b-instant' pour la vitesse pure
    # 'llama-3.3-70b-versatile' pour une analyse financière plus fine
    model_id = "llama-3.3-70b-versatile" 

    # Chargement du prompt stratégique
    prompt_path = os.path.join("prompts", "mega_analysis.txt")
    if not os.path.exists(prompt_path):
        prompt_path = os.path.join("prompts", "system.txt")
    
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            instructions = f.read()
    except Exception as e:
        instructions = "Tu es un expert en marchés de prédiction. Analyse les marchés fournis."
        logging.warning(f"Impossible de charger le prompt : {e}")

    # On force le format de réponse JSON dans le prompt système
    system_prompt = f"{instructions}\n\nIMPORTANT: Tu dois analyser chaque marché du batch et répondre UNIQUEMENT au format JSON suivant : {{'results': [{{'id': '...', 'decision': 'OPPORTUNITY' ou 'REJECTED', 'confidence_score': 0-100, 'strategy': '...', 'edge_estimate': 0, 'risk_flags': []}}, ...]}}"

    batch_size = 10
    candidates = []
    active_markets = markets 
    
    logging.info(f"🚀 Analyse stratégique de {len(active_markets)} marchés avec {model_id}...")

    for i in range(0, len(active_markets), batch_size):
        batch = active_markets[i:i + batch_size]
        try:
            # Préparation des données légères pour l'IA
            batch_data = [{"id": m.get('id'), "q": m.get('question'), "vol": m.get('volume'), "liq": m.get('liquidity')} for m in batch]
            
            completion = client.chat.completions.create(
                model=model_id,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Voici le batch de marchés à analyser :\n{json.dumps(batch_data)}"}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            raw_res = completion.choices[0].message.content
            data = json.loads(clean_json_response(raw_res))
            results = data.get('results', [])
            
            csv_buffer = []
            for j, res in enumerate(results):
                # Récupération du marché correspondant dans le batch local
                m = batch[j] if j < len(batch) else {}
                decision = res.get('decision', 'REJECTED')
                conf = res.get('confidence_score', 0)
                
                csv_buffer.append([
                    time.strftime("%Y-%m-%d %H:%M:%S"), 
                    m.get('question'), 
                    m.get('id'),
                    m.get('volume'), 
                    m.get('liquidity'), 
                    decision, 
                    res.get('strategy', 'Batch Analysis'),
                    conf, 
                    res.get('edge_estimate', 0), 
                    str(res.get('risk_flags', []))
                ])
                
                # Critère de sélection pour Telegram
                if decision == "OPPORTUNITY" and conf >= 80:
                    candidates.append(m)
                    logging.info(f"🟢 OPPORTUNITÉ DÉTECTÉE : {m.get('question')}")

            append_to_csv(csv_buffer)
            logging.info(f"📦 Batch {i//batch_size + 1} terminé ({min(i+batch_size, len(active_markets))}/{len(active_markets)})")
            
            # Pause de 2 secondes pour respecter les quotas TPM (Tokens Per Minute)
            time.sleep(2.5) 

        except Exception as e:
            logging.error(f"Erreur lors du traitement du batch {i}: {e}")
            time.sleep(5) # Pause plus longue en cas d'erreur

    return {"decision": "SCAN_COMPLETED", "count": len(candidates), "markets": candidates}
