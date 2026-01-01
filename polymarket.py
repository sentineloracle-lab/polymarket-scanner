import requests
import time
from config import MAX_MARKETS_TO_FETCH

BASE_URL = "https://gamma-api.polymarket.com/markets"

def fetch_markets():
    all_markets = []
    limit = 100
    offset = 0
    
    print(f"📡 Scraping Gamma (Cible: {MAX_MARKETS_TO_FETCH})...")

    while len(all_markets) < MAX_MARKETS_TO_FETCH:
        try:
            # Paramètres minimalistes pour garantir l'acceptation par l'API
            params = {
                "limit": limit,
                "offset": offset,
                "active": "true"
            }
            
            r = requests.get(BASE_URL, params=params, timeout=15)
            
            # Si ça échoue, on affiche l'URL exacte pour debug
            if r.status_code != 200:
                print(f"⚠️ Erreur {r.status_code} sur URL: {r.url}")
                break
                
            data = r.json()
            batch = data if isinstance(data, list) else data.get("markets", [])
            
            if not batch:
                break
                
            all_markets.extend(batch)
            print(f"   ↳ Batch reçu: {len(batch)} | Total: {len(all_markets)}")
            
            offset += limit
            time.sleep(0.1) 
            
        except Exception as e:
            print(f"⚠️ Erreur: {e}")
            break

    return all_markets
