import os
import csv
import logging
import requests
from telegram_client import send_message

JOURNAL_FILE = "trading_journal.csv"

def check_prices():
    if not os.path.exists(JOURNAL_FILE):
        return

    # 1. Lire les positions ouvertes dans le journal
    with open(JOURNAL_FILE, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        positions = list(reader)

    if not positions:
        return

    # 2. Récupérer les prix actuels sur Polymarket (Gamma API)
    # Note: On simplifie ici, l'idéal est de refaire un appel API pour les IDs précis
    try:
        response = requests.get("https://gamma-api.polymarket.com/markets?active=true&limit=100")
        current_markets = {str(m['id']): m for m in response.json()}
    except Exception as e:
        print(f"Erreur API: {e}")
        return

    # 3. Comparer
    for pos in positions:
        m_id = pos.get('id') # Il faudra s'assurer que l'ID est dans le journal
        buy_price = float(pos['Prix'])
        action = pos['Action']
        
        # Simulation de recherche par nom si l'ID n'est pas parfait
        market_name = pos['Marche']
        
        # Logique de détection de hausse (Exemple simplifié par nom)
        for mid, mdata in current_markets.items():
            if mdata['question'] == market_name:
                current_price = float(mdata['outcomePrices'][0] if "YES" in action else mdata['outcomePrices'][1])
                
                # Calcul de la performance
                change = (current_price - buy_price) / buy_price
                
                if change >= 0.20:
                    msg = (f"🚀 *ALERTE PROFIT (+{int(change*100)}%)*\n\n"
                           f"📋 *Marché:* {market_name}\n"
                           f"💰 *Prix achat:* {buy_price}\n"
                           f"📈 *Prix actuel:* {current_price}\n\n"
                           f"💡 Conseil : Pensez à revendre une partie ou la totalité pour sécuriser vos gains !")
                    send_message(msg)

if __name__ == "__main__":
    check_prices()
