import json
import time
import csv
import os
from llm_client import ask_llm
from news.tavily_client import fetch_recent_news

# Configuration des seuils (Ajustés suite analyse Grok)
# On baisse le volume car les opportunités "Redeem" (post-event) ont souvent peu de volume récent
MIN_VOLUME = 300       
MIN_LIQUIDITY = 300     # On garde un minimum pour pouvoir entrer/sortir
CSV_FILE = "scan_history.csv"

def log_to_csv(market, analysis, decision):
    """Enregistre les résultats pour analyse future (Backtesting)"""
    file_exists = os.path.isfile(CSV_FILE)
    with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Timestamp", "Question", "ID", "Volume", "Liquidity", "Decision", "Strategy", "Confidence", "Edge"])
        
        writer.writerow([
            time.strftime("%Y-%m-%d %H:%M:%S"),
            market.get("question"),
            market.get("id", "N/A"),
            market.get("volume"),
            market.get("liquidity"),
            decision,
            analysis.get("strategy_type", "N/A") if analysis else "N/A",
            analysis.get("confidence_score", 0) if analysis else 0,
            analysis.get("estimated_edge", 0) if analysis else 0
        ])

def run_aggressive_scanner(markets, prompts):
    candidates = []
    analyzed_count = 0
    
    print(f"🔄 Scan démarré sur {len(markets)} marchés bruts...")

    # --- PHASE 1 : FILTRE MATHÉMATIQUE (Optimisé Grok/Redeem) ---
    pre_filtered = []
    for m in markets:
        vol = float(m.get("volume") or 0)
        liq = float(m.get("liquidity") or 0)
        
        # On accepte un volume faible SI la liquidité est correcte (cas des marchés en attente de résolution)
        if vol < MIN_VOLUME and liq < MIN_LIQUIDITY:
            continue
            
        # Exclusion des mots clés "Sport pur" (souvent trop efficaces/bots)
        # Mais on garde "Politics", "Crypto", "Business" où l'UMA est complexe
        title = m.get("question", "").lower()
        if any(x in title for x in ["nba ", "nfl ", "premier league", "tennis"]):
            continue

        pre_filtered.append(m)

    print(f"📉 Après filtre mathématique : {len(pre_filtered)} marchés retenus.")

    # --- PHASE 2 : ANALYSE PROFONDE (IA) ---
    # On limite à 25 analyses pour contrôler les coûts API
    for market in pre_filtered[:25]:
        try:
            analyzed_count += 1
            print(f"🧠 Analyse IA ({analyzed_count}): {market.get('question')[:40]}...")

            analysis_raw = ask_llm(
                prompts["system"],
                prompts["mega_analysis"].replace("{{DATA}}", json.dumps(market))
            )
            
            # Nettoyage
            analysis_raw = analysis_raw.replace("```json", "").replace("```", "").strip()
            analysis = json.loads(analysis_raw)

            # Logging SYSTEMATIQUE (même si rejeté) pour analyse future
            decision = "REJECTED_AI"
            if analysis.get("is_interesting") and analysis.get("confidence_score", 0) >= 80:
                decision = "CANDIDATE"

            log_to_csv(market, analysis, decision)

            if decision == "REJECTED_AI":
                continue

            # --- PHASE 3 : VALIDATION ---
            print("🔎 Candidat détecté ! Vérification News & Checklist...")
            
            # Recherche spécifique sur les règles/résolutions
            news_query = f"{market['question']} resolution rules UMA polymarket"
            news = fetch_recent_news(news_query)
            
            checklist_raw = ask_llm(
                prompts["system"], 
                prompts["checklist"]
                .replace("{{DATA}}", json.dumps(market))
                .replace("{{NEWS}}", json.dumps(news))
            )
            checklist = json.loads(checklist_raw.replace("```json", "").replace("```", "").strip())
            
            if not checklist.get("checklist_passed", False):
                print("❌ Rejeté par la Checklist finale.")
                log_to_csv(market, analysis, "REJECTED_CHECKLIST")
                continue

            market.update({
                "analysis": analysis,
                "news_summary": news[:2],
                "found_at": time.strftime("%Y-%m-%d %H:%M:%S")
            })
            candidates.append(market)
            log_to_csv(market, analysis, "ACCEPTED")

        except Exception as e:
            print(f"⚠️ Erreur process: {e}")
            continue

    # --- PHASE 4 : SORTIE ---
    if not candidates:
        return {"decision": "NO OPPORTUNITY", "scanned_math": len(pre_filtered), "scanned_ai": analyzed_count}

    final_msg = ask_llm(
        prompts["system"],
        prompts["final_summary"].replace("{{DATA}}", json.dumps(candidates))
    )

    return {
        "decision": "OPPORTUNITY_FOUND", 
        "count": len(candidates), 
        "telegram_message": final_msg,
        "raw_candidates": candidates
    }
