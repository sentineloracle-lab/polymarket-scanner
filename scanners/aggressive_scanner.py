import json
import time
import csv
import os
from llm_client import ask_llm
from news.tavily_client import fetch_recent_news

# --- PARAMÈTRES STRATÉGIQUES (Calibrés post-audit Grok) ---
# On baisse le volume min pour attraper les marchés "Zombies" (post-event)
# qui ont peu d'activité récente mais une liquidité bloquée.
MIN_VOLUME = 200        
MIN_LIQUIDITY = 300     
CSV_FILE = "scan_history.csv"

def log_to_csv(market, analysis, decision):
    """Enregistre les données pour Backtest futur (Data Driven)."""
    file_exists = os.path.isfile(CSV_FILE)
    try:
        # utf-8-sig pour compatibilité Excel immédiate
        with open(CSV_FILE, mode='a', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow([
                    "Timestamp", "Question", "ID", "Volume", "Liquidity", 
                    "Decision", "Strategy", "Confidence", "Edge", "Risk_Flags"
                ])
            
            writer.writerow([
                time.strftime("%Y-%m-%d %H:%M:%S"),
                market.get("question"),
                market.get("id", "N/A"),
                market.get("volume"),
                market.get("liquidity"),
                decision,
                analysis.get("strategy_type", "N/A") if analysis else "N/A",
                analysis.get("confidence_score", 0) if analysis else 0,
                analysis.get("estimated_edge", 0) if analysis else 0,
                analysis.get("risk_flags", "") if analysis else ""
            ])
    except Exception as e:
        print(f"⚠️ Erreur écriture CSV: {e}")

def run_aggressive_scanner(markets, prompts):
    candidates = []
    analyzed_count = 0
    math_filtered_count = 0
    
    print(f"🔄 Début du filtrage sur {len(markets)} marchés...")

    # --- PHASE 1 : FILTRE MATHÉMATIQUE (Le grand entonnoir) ---
    pre_filtered = []
    for m in markets:
        vol = float(m.get("volume") or 0)
        liq = float(m.get("liquidity") or 0)
        
        # 1. Filtre de viabilité de base
        if vol < MIN_VOLUME and liq < MIN_LIQUIDITY:
            continue

        # 2. Exclusion Sémantique (Sport pur = trop efficient)
        # On garde Politique, Crypto, Business, Science
        title = m.get("question", "").lower()
        if any(x in title for x in ["nba ", "nfl ", "premier league", "tennis match", "goals"]):
            continue

        pre_filtered.append(m)

    math_filtered_count = len(pre_filtered)
    print(f"📉 Candidats après filtre math : {math_filtered_count}")

    # --- PHASE 2 : ANALYSE IA (Le Sniper) ---
    # On limite l'analyse IA aux 30 meilleurs candidats pour gérer le budget
    # On pourrait trier par liquidité décroissante ici si on voulait
    
    for market in pre_filtered[:30]:
        try:
            analyzed_count += 1
            question_short = market.get('question', '')[:50]
            print(f"🧠 Analyse IA ({analyzed_count}/{min(30, math_filtered_count)}): {question_short}...")

            # 1. ANALYSE STRATÉGIQUE (Mega-Prompt)
            analysis_raw = ask_llm(
                prompts["system"],
                prompts["mega_analysis"].replace("{{DATA}}", json.dumps(market))
            )
            
            # Nettoyage JSON robuste
            clean_json = analysis_raw.replace("```json", "").replace("```", "").strip()
            try:
                analysis = json.loads(clean_json)
            except:
                print("   ⚠️ JSON malformé, skip.")
                continue

            # Décision intermédiaire
            if not analysis.get("is_interesting") or analysis.get("confidence_score", 0) < 80:
                log_to_csv(market, analysis, "REJECTED_AI")
                continue

            print(f"   🔥 Potentiel détecté ({analysis.get('strategy_type')}) ! Vérification News...")

            # 2. VALIDATION EXTERNE (News & Règles)
            # On cherche spécifiquement des règles de résolution
            news_query = f"{market['question']} polymarket resolution rules UMA"
            news = fetch_recent_news(news_query)
            
            # 3. CHECKLIST FINALE (Risk Manager)
            checklist_raw = ask_llm(
                prompts["system"], 
                prompts["checklist"]
                .replace("{{DATA}}", json.dumps(market))
                .replace("{{NEWS}}", json.dumps(news))
            )
            checklist = json.loads(checklist_raw.replace("```json", "").replace("```", "").strip())
            
            if not checklist.get("checklist_passed", False):
                print("   ❌ Bloqué par la Checklist (Risque identifié).")
                log_to_csv(market, analysis, "REJECTED_CHECKLIST")
                continue

            # --- SUCCÈS ---
            market.update({
                "analysis": analysis,
                "news_summary": news[:2],
                "found_at": time.strftime("%Y-%m-%d %H:%M:%S")
            })
            candidates.append(market)
            log_to_csv(market, analysis, "ACCEPTED_CANDIDATE")

        except Exception as e:
            print(f"⚠️ Erreur process loop: {e}")
            continue

    # --- RAPPORT FINAL ---
    if not candidates:
        return {
            "decision": "NO OPPORTUNITY", 
            "scanned_total": len(markets),
            "scanned_math": math_filtered_count, 
            "scanned_ai": analyzed_count
        }

    # Génération message Telegram
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
