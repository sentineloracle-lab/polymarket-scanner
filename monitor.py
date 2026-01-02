import os
import csv
import logging
import requests
from telegram_client import send_message

JOURNAL_FILE = "trading_journal.csv"

def get_current_price(market_id, action):
    try:
        response = requests.get(f"https://gamma-api.polymarket.com/markets/{market_id}")
        data = response.json()
        prices = data.get('outcomePrices', [])
        if not prices: return None
        return float(prices[0] if "YES" in action.upper() else prices[1])
    except:
        return None

def check_for_profits():
    if not os.path.exists(JOURNAL_FILE):
        return

    with open(JOURNAL_FILE, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        positions = list(reader)

    logging.info(f"Analyse de {len(positions)} positions en cours...")
    
    for pos in positions:
        m_id = pos.get('ID')
        buy_price = float(pos.get('Prix', 0))
        market_name = pos.get('Marche')
        action = pos.get('Action')

        if not m_id or buy_price == 0: continue

        current_price = get_current_price(m_id, action)
        
        if current_price:
            gain = (current_price - buy_price) / buy_price
            
            # Alerte si gain >= 20% ET que le prix n'est pas encore au plafond (0.90)
            if gain >= 0.20 and current_price < 0.90:
                msg = (f"🚀 *ALERTE PROFIT (+{int(gain*100)}%)*\n\n"
                       f"📋 *Marché:* {market_name}\n"
                       f"💰 *Achat:* {buy_price} cts\n"
                       f"📈 *Actuel:* {current_price} cts\n\n"
                       f"👉 Action : Pensez à revendre !")
                send_message(msg)
            elif current_price >= 0.90:
                logging.info(f"Profit max atteint pour {market_name} ({current_price}). Alerte muette.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    check_for_profits()
