import os
import logging
import traceback
from datetime import datetime
from polymarket import fetch_markets
from scanners.aggressive_scanner import run_aggressive_scanner
from telegram_client import send_message

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)

def get_liquidity_safe(m):
    """Extrait la liquidité de manière robuste."""
    try:
        if 'liquidity' in m and m['liquidity'] is not None:
            return float(m['liquidity'])
        if 'metrics' in m and isinstance(m['metrics'], dict):
            return float(m['metrics'].get('liquidity', 0))
    except:
        return 0
    return 0

def filter_quality_markets(raw_markets):
    """
    Filtre les marchés pour ne garder que le contenu 'frais' et liquide.
    Cela évite d'envoyer des déchets à l'IA.
    """
    filtered = []
    current_year = str(datetime.now().year) # 2026
    
    for m in raw_markets:
        try:
            # 1. Vérification de la question
            question = m.get('question', '')
            if not question:
                continue
                
            # 2. Vérification de la liquidité (minimum 100$ pour être sérieux)
            liq = get_liquidity_safe(m)
            if liq < 100:
                continue
            
            # 3. Éviter les marchés archivés (2020-2024)
            if any(old_year in question for old_year in ["2020", "2021", "2022", "2023", "2024"]):
                continue
                
            filtered.append(m)
        except:
            continue
            
    return filtered

def main():
    logging.info("🚀 Démarrage du Polymarket Scanner V4 (Turbo Funnel)...")
    
    try:
        # 1. Récupération (Doit être configuré à 500 dans polymarket.py)
        raw_markets = fetch_markets()
        if not raw_markets:
            logging.error("Échec critique : Aucun marché récupéré.")
            return

        # 2. Filtrage de premier niveau (Qualité/Liquidité)
        markets = filter_quality_markets(raw_markets)
        logging.info(f"📥 {len(raw_markets)} bruts -> {len(markets)} qualifiés pour l'IA.")

        if not markets:
            logging.info("💤 Aucun marché qualifié après filtrage. Fin du cycle.")
            return

        # 3. Chargement des instructions
        # Note: Le scanner chargera lui-même mega_analysis.txt s'il existe
        prompts = {
            "system": "Expert en arbitrage et marchés de prédiction.",
            "mega_analysis": "Recherche d'opportunités à haut rendement."
        }
        
        # 4. Lancement de l'analyse IA (Modèle Entonnoir 8B -> 70B)
        result = run_aggressive_scanner(markets, prompts)
        
        # 5. Synthèse et Notification Telegram
        logging.info("-" * 30)
        found_count = result.get("count", 0)
        logging.info(f"📊 Scan terminé : {found_count} opportunités réelles détectées.")
        
        if found_count > 0:
            # Envoi d'une notification globale si des opportunités ont été trouvées
            # (Les détails sont généralement gérés à l'intérieur du scanner ou ici)
            msg = f"🔔 *Scanner Polymarket*\n\n✅ Analyse terminée sur {len(markets)} marchés.\n🔥 *{found_count}* opportunités détectées !\n\nVérifiez le fichier CSV pour les détails."
            send_message(msg)
            
    except Exception as e:
        error_msg = f"⚠️ CRASH DU BOT :\n{str(e)}\n\n{traceback.format_exc()}"
        logging.critical(error_msg)
        try:
            send_message(error_msg[:500])
        except:
            pass

if __name__ == "__main__":
    main()
