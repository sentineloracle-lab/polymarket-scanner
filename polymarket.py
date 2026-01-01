import requests
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from config import MAX_MARKETS_TO_FETCH

# Endpoint Gamma (Standard 2026)
BASE_URL = "https://gamma-api.polymarket.com/markets"

def get_session():
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retries))
    return session

def fetch_markets():
    session = get_session()
    all_markets = []
    limit = 100
    offset = 0
    
    print(f"📡 Démarrage scraping Gamma (Cible: {MAX_MARKETS_TO_FETCH} marchés)...")

    while len(all_markets) < MAX_MARKETS_TO_FETCH:
        try:
            # Correction : Paramètres simplifiés pour éviter l'erreur 422
            params = {
                "active": "true",
                "closed": "false",
                "limit": limit,
                "offset": offset
                # On retire 'order' et 'ascending' car ils causent souvent le 422 si mal formatés
            }
            
            r = session.get(BASE_URL, params=params, timeout=15)
            
            # Debugging si l'erreur persiste
            if r.status_code != 200:
                print(f"⚠️ Erreur API {r.status_code}: {r.text}")
                break
                
            data = r.json()
            batch = data if isinstance(data, list) else data.get("markets", [])
            
            if not batch:
                break
                
            all_markets.extend(batch)
            print(f"   ↳ Batch reçu: {len(batch)} | Total: {len(all_markets)}")
            
            offset += limit
            time.sleep(0.2) 
            
        except Exception as e:
            print(f"⚠️ Erreur fetch critique : {e}")
            break

    return all_markets
