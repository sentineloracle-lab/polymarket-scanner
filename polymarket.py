import requests
import logging

def fetch_markets():
    logging.info("📡 Scraping Gamma API...")
    url = "https://gamma-api.polymarket.com/events"
    params = {
        "limit": 500,
        "active": "true",
        "closed": "false",
        "order": "volume",
        "dir": "desc"
    }
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=15)
        if response.status_code == 200:
            events = response.json()
            markets_list = []
            for event in events:
                question = event.get('title') or event.get('description', '')
                
                # FILTRE : On ignore les marchés de prix (Bitcoin/Ethereum Up or Down)
                # Ces marchés sont souvent du bruit pour de l'arbitrage long terme.
                noise_keywords = ["Up or Down", "Price of", "Predict the price"]
                if any(kw in question for kw in noise_keywords):
                    continue
                    
                markets_list.append({
                    'id': event.get('id'),
                    'question': question,
                    'liquidity': float(event.get('liquidity', 0)),
                    'volume': float(event.get('volume', 0))
                })
            return markets_list
        return []
    except Exception as e:
        logging.error(f"Fetch error: {e}")
        return []
