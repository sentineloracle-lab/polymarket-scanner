import json
import time
import csv
import os
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from llm_client import ask_llm
from news.tavily_client import fetch_recent_news
from config import MIN_VOLUME, MIN_LIQUIDITY, CSV_LOG_FILE, MAX_AI_ANALYSIS

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def clean_json_response(raw_text):
    """Extrait proprement le JSON d'une réponse texte de l'IA."""
    content = raw_text.strip()
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()
    return content

def append_to_csv(rows):
    """Écrit une liste de résultats dans le CSV en une seule fois (Batch Write)."""
    file_exists = os.path.isfile(CSV_LOG_FILE)
    try:
        with open(CSV_LOG_FILE, mode='a', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow([
                    "Timestamp", "Question", "ID", "Volume", "Liquidity", 
                    "Decision", "Strategy", "Confidence", "Edge", "Risk_Flags"
                ])
            writer.writerows(rows)
    except Exception as e:
        logging.error(f"Erreur critique écriture CSV: {e}")

def analyze_single_market(market, prompts):
    """Fonction isolée pour traiter UN marché."""
    try:
        # 1. Analyse Stratégique (Mega Prompt)
        analysis_raw = ask_llm(
            prompts["system"],
            prompts["mega_analysis"].replace("{{DATA}}", json.dumps(market))
        )
        
        content = clean_json_response(analysis_raw)
        try:
            analysis = json.loads(content)
        except json.JSONDecodeError:
            logging.error(f"Format JSON invalide (Phase 1) pour {market.get('question')}")
            return {"status": "ERROR_JSON", "market": market, "analysis": None}

        # Filtre primaire IA
        if not analysis.get("is_interesting") or analysis.get("confidence_score", 0) < 80:
            return {"status": "REJECTED_AI", "market": market, "analysis": analysis}

        # 2. Validation Externe (News & UMA Rules)
        news_query = f"{market['question']} polymarket resolution rules UMA"
        news = fetch_recent_news(news_query)
        
        # 3. Checklist Finale
        checklist_raw = ask_llm(
            prompts["system"], 
            prompts["checklist"]
            .replace("{{DATA}}", json.dumps(market))
            .replace("{{NEWS}}", json.dumps(news))
        )
        
        checklist_content = clean_json_response(checklist_raw)
        try:
            checklist = json.loads(checklist_content)
        except:
             checklist = {"checklist_passed": False, "risk_flags": ["JSON Checklist Error"]}
        
        if not checklist.get("checklist_passed", False):
            analysis["risk_flags"] = str(checklist.get("risk_flags", []))
            return {"status": "REJECTED_CHECKLIST", "market": market, "analysis": analysis}

        # Succès
        market.update({
            "analysis": analysis,
            "news_summary": news[:2] if isinstance(news, list) else [],
            "found_at": time.strftime("%Y-%m-%d %H:%M:%S")
        })
        return {"status": "ACCEPTED", "market": market, "analysis": analysis}

    except Exception as e:
        return {"status": f"ERROR_PROCESS: {str(e)}", "market": market, "analysis": None}

def run_aggressive_scanner(markets, prompts):
    logging.info(f"🔄 Début du filtrage mathématique sur {len(markets)} marchés...")

    # --- PHASE 1 : FILTRE MATHÉMATIQUE ---
    pre_filtered = []
    for m in markets:
        vol = float(m.get("volume") or 0)
        liq = float(m.get("liquidity") or 0)
        
        if vol < MIN_VOLUME and liq < MIN_LIQUIDITY:
            continue

        title = m.get("question", "").lower()
        if any(x in title for x in ["nba ", "nfl ", "premier league", "tennis match"]):
            continue

        pre_filtered.append(m)

    pre_filtered.sort(key=lambda x: float(x.get("liquidity") or 0), reverse=True)
    logging.info(f"📉 Candidats retenus pour IA : {len(pre_filtered)} (Limité à {MAX_AI_ANALYSIS})")

    # --- PHASE 2 : ANALYSE PARALLÈLE ---
    candidates = []
    csv_buffer = []
    
    targets = pre_filtered[:MAX_AI_ANALYSIS]
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_market = {executor.submit(analyze_single_market, m, prompts): m for m in targets}
        
        for future in as_completed(future_to_market):
            m = future_to_market[future]
            try:
                res = future.result(timeout=35) # Timeout légèrement augmenté
                
                status = res["status"]
                an = res["analysis"]
                
                csv_buffer.append([
                    time.strftime("%Y-%m-%d %H:%M:%S"),
                    m.get("question"),
                    m.get("id"),
                    m.get("volume"),
                    m.get("liquidity"),
                    status,
                    an.get("strategy_type", "N/A") if an else "N/A",
                    an.get("confidence_score", 0) if an else 0,
                    an.get("estimated_edge", 0) if an else 0,
                    an.get("risk_flags", "") if an else ""
                ])

                if status == "ACCEPTED":
                    logging.info(f"✅ Opportunité validée : {m.get('question')}")
                    candidates.append(res["market"])
                elif status == "REJECTED_CHECKLIST":
                    logging.info(f"❌ Rejet Checklist : {m.get('question')}")
                
            except TimeoutError:
                logging.warning(f"⏳ Timeout sur le marché : {m.get('question')}")
            except Exception as exc:
                logging.error(f"💥 Exception thread : {exc}")

    append_to_csv(csv_buffer)

    # --- RAPPORT FINAL ---
    if not candidates:
        return {
            "decision": "NO_OPPORTUNITY", 
            "scanned_total": len(markets),
            "scanned_math": len(pre_filtered)
        }

    final_msg_raw = ask_llm(
        prompts["system"],
        prompts["final_summary"].replace("{{DATA}}", json.dumps(candidates))
    )

    return {
        "decision": "OPPORTUNITY_FOUND", 
        "count": len(candidates), 
        "telegram_message": final_msg_raw
    }
