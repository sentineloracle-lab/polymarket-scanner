import os
import logging
import traceback
from polymarket import fetch_markets
from scanners.aggressive_scanner import run_aggressive_scanner
from telegram_client import send_message

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)

def get_liquidity_safe(m):
    """Extrait la liquidité peu importe où Polymarket la cache."""
    try:
        # Test 1: Champ direct (le plus probable)
        if 'liquidity' in m and m['liquidity'] is not None:
            return float(m['liquidity'])
        # Test 2: Dans l'objet metrics
        if 'metrics' in m and isinstance(m['metrics'], dict):
            return float(m['metrics'].get('liquidity', 0))
        # Test 3: Dans active_order_count (indicateur d'activité si liquidité absente)
        if 'active_order_count' in m:
            return float(m['active_order_count'])
    except:
        return 0
    return 0

def main():
    logging.info("🚀 Démarrage du Polymarket Scanner V4...")
    
    try:
        raw_markets = fetch_markets()
        if not raw_markets:
            logging.error("Echec critique: Aucun marché récupéré.")
            return

        # FILTRAGE ULTRA-PERMISSIF POUR DÉBLOQUER
        markets = []
        for m in raw_markets:
            liq = get_liquidity_safe(m)
            # Si le marché a une question et semble exister, on l'analyse 
            # On ignore le filtre de liquidité si le résultat est toujours 0
            if m.get('question'):
                markets.append(m)
        
        logging.info(f"📥 {len(raw_markets)} reçus -> {len(markets)} envoyés à l'IA")

        if not markets:
            logging.info("❌ Aucun marché avec une question n'a été trouvé.")
            return

        prompts = {
            "system": "Tu es un expert en marchés de prédiction.",
            "mega_analysis": "Analyse les opportunités de profit."
        }
        
        # On lance enfin l'IA
        result = run_aggressive_scanner(markets, prompts)
        
        logging.info("-" * 30)
        logging.info(f"📊 Scan terminé : {len(result.get('markets', []))} opportunités détectées.")
            
    except Exception as e:
        logging.critical(f"⚠️ CRASH : {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
