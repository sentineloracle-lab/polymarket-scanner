import os
import logging
import traceback
from datetime import datetime
from polymarket import fetch_markets
from scanners.aggressive_scanner import run_aggressive_scanner
from telegram_client import send_message

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)

def load_prompts():
    def r(p): 
        path = os.path.join(os.path.dirname(__file__), p)
        if not os.path.exists(path):
            logging.warning(f"Prompt {p} introuvable.")
            return ""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except:
            return ""

    return {
        "system": r("prompts/system.txt") or "Tu es un assistant expert.",
        "mega_analysis": r("prompts/mega_analysis.txt"),
        "checklist": r("prompts/checklist.txt"),
        "final_summary": r("prompts/final_summary.txt")
    }

def filter_active_markets(markets):
    """Filtre les marchés pour ne garder que ceux qui sont actifs et liquides."""
    filtered = []
    current_year = str(datetime.now().year) # 2026
    
    for m in markets:
        try:
            # 1. Ignorer les marchés avec une liquidité ridicule ou nulle
            liquidity = float(m.get('liquidity', 0))
            if liquidity < 100: # Seuil minimum de 500$ pour éviter le "bruit"
                continue
                
            # 2. Ignorer les marchés qui semblent terminés ou vieux
            # On vérifie si la question contient des années passées
            question = m.get('question', '').lower()
            if any(year in question for year in ["2020", "2021", "2022", "2023", "2024"]):
                continue

            # 3. Vérifier le statut (si disponible dans votre API Gamma)
            if m.get('closed') is True or m.get('active') is False:
                continue

            filtered.append(m)
        except:
            continue
            
    return filtered

def main():
    logging.info("🚀 Démarrage du Polymarket Scanner V4 (Turbo Trawl)...")
    
    try:
        # 1. Fetch
        raw_markets = fetch_markets()
        if not raw_markets:
            logging.error("Echec critique: Aucun marché récupéré.")
            return

        # 2. Filtrage (La clé de l'efficacité)
        markets = filter_active_markets(raw_markets)
        logging.info(f"📥 {len(raw_markets)} marchés reçus -> {len(markets)} marchés actifs filtrés.")

        if not markets:
            logging.info("✅ Aucun marché actif pertinent à analyser. Fin du cycle.")
            return

        # 3. Prompts
        prompts = load_prompts()
        
        # 4. Run (Avec Groq et Batching)
        result = run_aggressive_scanner(markets, prompts)
        
        # 5. Resultats
        logging.info("-" * 30)
        logging.info(f"📊 Résultat final : {result.get('decision')}")
        
        if result.get("decision") == "SCAN_COMPLETED" and result.get("count", 0) > 0:
            logging.info(f"🔥 {result['count']} opportunités trouvées. Envoi Telegram.")
            # On construit un petit message récapitulatif
            msg = f"🎯 *Scanner Polymarket*\n\n{result['count']} opportunités détectées sur {len(markets)} marchés analysés.\nConsultez le fichier CSV pour les détails."
            send_message(msg)
        else:
            logging.info("💤 Aucune opportunité détectée.")
            
    except Exception as e:
        error_msg = f"⚠️ CRASH DU BOT :\n{str(e)}\n\n{traceback.format_exc()}"
        logging.critical(error_msg)
        try:
            send_message(error_msg[:1000])
        except:
            pass

if __name__ == "__main__":
    main()
