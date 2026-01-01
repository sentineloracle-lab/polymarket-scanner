import json
import os
from polymarket import fetch_markets
from scanners.aggressive_scanner import run_aggressive_scanner
from telegram_client import send_message

def load_prompts():
    def r(p): 
        path = os.path.join(os.path.dirname(__file__), p)
        if not os.path.exists(path):
            print(f"⚠️ Warning: Prompt {p} introuvable.")
            return ""
        return open(path, "r", encoding="utf-8").read()

    return {
        # On garde un system prompt générique s'il existe, sinon vide
        "system": r("prompts/system.txt") if os.path.exists("prompts/system.txt") else "Tu es un assistant expert.",
        "mega_analysis": r("prompts/mega_analysis.txt"),
        "checklist": r("prompts/checklist.txt"),
        "final_summary": r("prompts/final_summary.txt")
    }

def main():
    print("🚀 Démarrage du Polymarket Scanner V2...")
    
    # 1. Fetch massif
    markets = fetch_markets(limit=1000)
    if not markets:
        print("❌ Aucun marché récupéré. Arrêt.")
        return

    # 2. Chargement Prompts
    prompts = load_prompts()
    
    # 3. Run Scanner
    result = run_aggressive_scanner(markets, prompts)
    
    # 4. Envoi Telegram
    if result["decision"] == "OPPORTUNITY_FOUND":
        print(f"✅ {result['count']} opportunités trouvées. Envoi Telegram.")
        send_message(result["telegram_message"])
    else:
        print(f"💤 Rien à signaler. (Math Scanned: {result.get('scanned_math')}, AI Scanned: {result.get('scanned_ai')})")

if __name__ == "__main__":
    main()
