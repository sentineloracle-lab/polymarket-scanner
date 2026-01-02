import os
import logging
import traceback
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
        if not os.path.exists(path): return ""
        try:
            with open(path, "r", encoding="utf-8") as f: return f.read()
        except: return ""

    return {
        "system": r("prompts/system.txt") or "Tu es un expert en marchés de prédiction.",
        "mega_analysis": r("prompts/mega_analysis.txt")
    }

def main():
    logging.info("🚀 Démarrage du Polymarket Scanner V4...")
    
    try:
        # 1. Fetch (On prend ce que l'API nous donne sans discuter)
        raw_markets = fetch_markets()
        if not raw_markets:
            logging.error("Echec critique: Aucun marché récupéré.")
            return

        # 2. Filtrage minimaliste pour DEBUG
        # On ne garde que les marchés avec une liquidité > 10$ pour être sûr d'avoir du contenu
        markets = [m for m in raw_markets if float(m.get('liquidity', 0)) > 10]
        
        logging.info(f"📥 {len(raw_markets)} reçus -> {len(markets)} à analyser (Liquidité > 10$)")

        if not markets:
            logging.info("✅ Aucun marché trouvé après filtrage (Liquidité trop basse).")
            return

        # 3. Prompts
        prompts = load_prompts()
        
        # 4. Run (Groq va maintenant recevoir les données)
        result = run_aggressive_scanner(markets, prompts)
        
        # 5. Resultats
        logging.info("-" * 30)
        if result.get("count", 0) > 0:
            logging.info(f"🔥 {result['count']} opportunités trouvées !")
            send_message(f"🚀 Scanner a analysé {len(markets)} marchés et trouvé {result['count']} opportunités.")
        else:
            logging.info("💤 Fin du scan. Aucune opportunité validée par l'IA.")
            
    except Exception as e:
        logging.critical(f"⚠️ CRASH : {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
