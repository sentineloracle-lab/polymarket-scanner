import requests
import logging
import json

def fetch_markets():
    logging.info("📡 Scraping Gamma API (Avec récupération des prix)...")
    url = "https://gamma-api.polymarket.com/events"
    
    # On filtre un peu plus pour avoir des données propres
    params = {
        "limit": 50, # On réduit un peu pour la qualité des données prix
        "active": "true",
        "closed": "false",
        "order": "volume",
        "dir": "desc"
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=15)
        if response.status_code == 200:
            events = response.json()
            markets_list = []
            
            for event in events:
                # Extraction des marchés à l'intérieur de l'événement
                markets = event.get('markets', [])
                if not markets: continue
                
                # On prend le marché principal (le premier souvent)
                main_market = markets[0]
                
                # Récupération des Prix (souvent stockés en string JSON : '["0.65", "0.35"]')
                try:
                    raw_prices = main_market.get('outcomePrices')
                    prices = json.loads(raw_prices) if raw_prices else ["?", "?"]
                    # Prix du YES (index 0) et NO (index 1) pour les marchés binaires
                    price_yes = float(prices[0]) if len(prices) > 0 and prices[0] != "?" else 0.5
                    price_no = float(prices[1]) if len(prices) > 1 and prices[1] != "?" else 0.5
                except:
                    price_yes, price_no = 0.5, 0.5

                question = event.get('title') or event.get('description', '')
                
                # Filtre anti-bruit (Crypto Up/Down)
                if "Up or Down" in question or "Price of" in question:
                    continue

                markets_list.append({
                    'id': event.get('id'),
                    'question': question,
                    'liquidity': float(event.get('liquidity', 0)),
                    'volume': float(event.get('volume', 0)),
                    'price_yes': price_yes,
                    'price_no': price_no
                })
            
            return markets_list
        return []
    except Exception as e:
        logging.error(f"Erreur Fetch: {e}")
        return []
