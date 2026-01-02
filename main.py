import os
import logging
import traceback
from datetime import datetime
from polymarket import fetch_markets
from scanners.aggressive_scanner import run_aggressive_scanner
from telegram_client import send_message

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)

def get_liquidity_safe(m):
    """Extrait la liquidité avec plusieurs fallback."""
    try:
        # Liste des clés possibles pour la liquidité selon les versions de l'API
        keys = ['liquidity', 'active_order_count', 'volume_24h']
        for key in keys:
            val = m.get(key)
            if val is not None: return float(val)
        
        if 'metrics' in m and isinstance(m['metrics'], dict):
            return float(m['metrics'].get('liquidity', 0))
    except:
        return 0
    return 0

def filter_quality_markets(raw_markets, min_liq=100):
    """Filtre avec un seuil de liquidité ajustable."""
    filtered = []
    for m in raw_markets:
        try:
            question = m.get('question', '')
            if not question: continue
            
            # On vérifie la liquidité
            liq = get_liquidity_safe(m)
            if liq < min_liq: continue
            
            # On retire uniquement les marchés explicitement clos
            if m.get('closed') is True: continue
                
            filtered.append(m)
        except:
            continue
    return filtered

def main():
    logging.info("🚀 Démarrage du Polymarket Scanner V4 (Turbo Funnel)...")
    
    try:
        raw_markets = fetch_markets()
        if not raw_markets:
            logging.error("Échec : Liste vide.")
            return

        # Tentative 1 : Filtrage qualitatif (Liquidité > 100$)
        markets = filter_quality_markets(raw_markets, min_liq=100)
        
        # Tentative 2 : Si 0 marchés, on baisse le seuil à 0 pour forcer l'analyse
        if not markets:
            logging.warning("⚠️ Aucun marché > 100$. Passage en mode permissif (Liquidité > 0)...")
            markets = filter_quality_markets(raw_markets, min_liq=0)

        logging.info(f"📥 {len(raw_markets)} bruts -> {len(markets)} qualifiés pour l'IA.")

        if not markets:
            logging.info("💤 Toujours rien. Vérifiez si l'API Gamma renvoie bien des données valides.")
            return

        prompts = {"system": "Expert", "mega_analysis": "Analyse"}
        
        # Lancement de l'analyse IA (Entonnoir 8B -> 70B)
        result = run_aggressive_scanner(markets, prompts)
        
        logging.info("-" * 30)
        found_count = result.get("count", 0)
        logging.info(f"📊 Scan terminé : {found_count} opportunités détectées.")
        
        if found_count > 0:
            msg = f"🔔 *Scanner Polymarket*\n🔥 *{found_count}* opportunités détectées sur {len(markets)} marchés !"
            send_message(msg)
            
    except Exception as e:
        logging.critical(f"⚠️ CRASH : {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
