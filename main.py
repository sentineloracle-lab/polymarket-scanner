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
        if not os.path.exists(path):
            logging.warning(f"Prompt {p} introuvable.")
            return ""
        return open(path, "r", encoding="utf-8").read()

    return {
        "system": r("prompts/system.txt") if os.path.exists("prompts/system.txt") else "Tu es un assistant expert.",
        "mega_analysis": r("prompts/mega_analysis.txt"),
        "checklist": r("prompts/checklist.txt"),
        "final_summary": r("prompts/final_summary.txt")
    }

def main():
    logging.info("🚀 Démarrage du Polymarket Scanner V4 (Turbo Trawl)...")
    
    try:
        # 1. Fetch
        markets = fetch_markets()
        if not markets:
            logging.error("Echec critique: Aucun marché récupéré.")
            return

        # 2. Prompts
        prompts = load_prompts()
        
        # 3. Run
        result = run_aggressive_scanner(markets, prompts)
        
        # 4. Resultats
        logging.info("-" * 30)
        logging.info(f"📊 Résultat final : {result['decision']}")
        
        if result["decision"] == "OPPORTUNITY_FOUND":
            logging.info(f"🔥 {result['count']} opportunités trouvées. Envoi Telegram.")
            send_message(result["telegram_message"])
        else:
            logging.info("💤 Dodo.")
            
    except Exception as e:
        # Panic Button : Si tout explose, on veut être prévenu
        error_msg = f"⚠️ CRASH DU BOT :\n{str(e)}\n\n{traceback.format_exc()}"
        logging.critical(error_msg)
        try:
            send_message(error_msg[:1000]) # On coupe si c'est trop long
        except:
            pass

if __name__ == "__main__":
    main()
