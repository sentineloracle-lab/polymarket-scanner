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
        "system": r("prompts/system.txt") if os.path.exists("prompts/system.txt") else "Tu es un assistant expert.",
        "mega_analysis": r("prompts/mega_analysis.txt"),
        "checklist": r("prompts/checklist.txt"),
        "final_summary": r("prompts/final_summary.txt")
    }

def main():
    print("🚀 Démarrage du Polymarket Scanner V3 (Deep Trawl)...")
    
    # 1. Fetch Massif (Pagination active)
    # On vise 1500 marchés pour avoir une bonne profondeur historique (Zombies)
    markets = fetch_markets(max_markets=1500)
    
    if not markets:
        print("❌ Echec critique: Aucun marché récupéré.")
        return

    # 2. Load Prompts
    prompts = load_prompts()
    
    # 3. Run Scanner
    result = run_aggressive_scanner(markets, prompts)
    
    # 4. Resultats
    print("-" * 30)
    print(f"📊 Rapport de session :")
    print(f"   • Marchés bruts : {result.get('scanned_total', 0)}")
    print(f"   • Après filtre Math : {result.get('scanned_math', 0)}")
    print(f"   • Analysés par IA : {result.get('scanned_ai', 0)}")
    print(f"   • Opportunités : {result.get('count', 0)}")
    print("-" * 30)

    if result["decision"] == "OPPORTUNITY_FOUND":
        send_message(result["telegram_message"])
        print("📨 Notification envoyée.")
    else:
        print("💤 Aucune opportunité validée ce tour-ci.")

if __name__ == "__main__":
    main()
