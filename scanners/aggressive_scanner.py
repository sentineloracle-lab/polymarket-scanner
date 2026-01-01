import json
import time
from llm_client import ask_llm
from news.tavily_client import fetch_recent_news

# Configuration des seuils (Le Mur Mathématique)
MIN_VOLUME = 1500       # On veut un minimum d'activité
MIN_LIQUIDITY = 500     # Pour pouvoir sortir si besoin
MAX_SPREAD = 0.15       # 15% max (si calculable via bid/ask, sinon ignoré)

def run_aggressive_scanner(markets, prompts):
    candidates = []
    analyzed_count = 0
    
    print(f"🔄 Scan démarré sur {len(markets)} marchés bruts...")

    # --- PHASE 1 : FILTRE MATHÉMATIQUE (Gratuit & Rapide) ---
    pre_filtered = []
    for m in markets:
        # 1. Extraction sécurisée des données
        vol = float(m.get("volume") or 0)
        liq = float(m.get("liquidity") or 0)
        
        # 2. Rejet immédiat des marchés morts
        if vol < MIN_VOLUME:
            continue
        if liq < MIN_LIQUIDITY:
            continue
            
        # 3. Filtre de mots-clés (Exemple : on évite le sport pur souvent trop efficient)
        title = m.get("question", "").lower()
        if any(x in title for x in ["nba", "nfl", "soccer", "tennis"]):
            continue

        pre_filtered.append(m)

    print(f"📉 Après filtre mathématique : {len(pre_filtered)} marchés retenus pour analyse IA.")

    # --- PHASE 2 : ANALYSE PROFONDE (IA) ---
    # On limite à 20 analyses IA max par run pour contrôler le budget/temps
    for market in pre_filtered[:20]:
        try:
            analyzed_count += 1
            print(f"🧠 Analyse IA ({analyzed_count}): {market.get('question')[:30]}...")

            # Appel unique au Mega-Prompt (remplace 3 appels)
            analysis_raw = ask_llm(
                prompts["system"],
                prompts["mega_analysis"].replace("{{DATA}}", json.dumps(market))
            )
            
            # Nettoyage JSON (gestion des backticks markdown fréquents chez les LLM)
            analysis_raw = analysis_raw.replace("```json", "").replace("```", "").strip()
            analysis = json.loads(analysis_raw)

            # Si l'IA rejette, on passe
            if not analysis.get("is_interesting") or analysis.get("confidence_score", 0) < 80:
                continue

            # --- PHASE 3 : VALIDATION NEWS & CHECKLIST (Seulement pour les élus) ---
            print("🔎 Candidat potentiel détecté ! Vérification News...")
            
            # Vérification News (Tavily)
            news = fetch_recent_news(market["question"])
            # Ici on pourrait ajouter un prompt "News Risk", mais pour économiser
            # on l'ajoute juste aux données pour l'humain
            
            # Dernier check procédural
            checklist_raw = ask_llm(
                prompts["system"], 
                prompts["checklist"].replace("{{DATA}}", json.dumps(market))
            )
            checklist_raw = checklist_raw.replace("```json", "").replace("```", "").strip()
            checklist = json.loads(checklist_raw)
            
            if not checklist.get("checklist_passed", False):
                print("❌ Rejeté par la Checklist finale.")
                continue

            # Construction du candidat final
            market.update({
                "analysis": analysis,
                "news_summary": news[:2], # Juste les 2 premières
                "found_at": time.strftime("%Y-%m-%d %H:%M:%S")
            })
            candidates.append(market)

        except json.JSONDecodeError:
            print("⚠️ Erreur JSON LLM, on ignore.")
            continue
        except Exception as e:
            print(f"⚠️ Erreur process: {e}")
            continue

    # --- PHASE 4 : RAPPORT FINAL ---
    if not candidates:
        return {"decision": "NO OPPORTUNITY", "scanned_math": len(pre_filtered), "scanned_ai": analyzed_count}

    # Génération du résumé Telegram via LLM
    final_msg = ask_llm(
        prompts["system"],
        prompts["final_summary"].replace("{{DATA}}", json.dumps(candidates))
    )

    # On retourne un objet structuré pour le main.py, mais le 'content' sera le message telegram
    return {
        "decision": "OPPORTUNITY_FOUND", 
        "count": len(candidates), 
        "telegram_message": final_msg,
        "raw_candidates": candidates
    }
