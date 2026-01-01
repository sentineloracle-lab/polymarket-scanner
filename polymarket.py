import requests
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from config import MAX_MARKETS_TO_FETCH

# Endpoint Gamma (Stable & Officiel 2025)
BASE_URL = "https://gamma-api.polymarket.com/markets"

def get_session():
    """Session HTTP blindée contre les micro-coupures."""
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
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
            params = {
                "active": "true",
                "closed": "false",
                "limit": limit,
                "offset": offset,
                "order": "volume_24h", # On prend les plus actifs en premier
                "ascending": "false"
            }
            
            r = session.get(BASE_URL, params=params, timeout=15)
            r.raise_for_status()
            data = r.json()
            
            # Gestion souple du format de réponse
            batch = data if isinstance(data, list) else data.get("markets", [])
            
            if not batch:
                break # Fin de la liste
                
            all_markets.extend(batch)
            print(f"   ↳ Batch reçu: {len(batch)} | Total: {len(all_markets)}")
            
            offset += limit
            time.sleep(0.1) # Respect poli du rate-limit
            
        except Exception as e:
            print(f"⚠️ Erreur fetch offset {offset}: {e}")
            break

    return all_markets
