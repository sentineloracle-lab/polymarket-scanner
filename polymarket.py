import requests
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Endpoint officiel pour les développeurs (plus stable)
BASE_URL = "https://gamma-api.polymarket.com/markets"

def get_session():
    """Crée une session robuste avec retries automatiques."""
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retries))
    return session

def fetch_markets(max_markets=2000):
    """
    Récupère les marchés avec pagination (offset) pour aller chercher
    les 'Zombie Markets' oubliés au fond de la liste.
    """
    session = get_session()
    all_markets = []
    limit = 100  # Taille de page standard
    offset = 0
    
    print(f"📡 Démarrage du scraping Gamma API (Cible: {max_markets} marchés max)...")

    while len(all_markets) < max_markets:
        try:
            params = {
                "active": "true",
                "closed": "false",
                "limit": limit,
                "offset": offset,
                "order": "volume_24h", # On prend les plus actifs en premier, puis on descend
                "ascending": "false"
            }
            
            r = session.get(BASE_URL, params=params, timeout=10)
            r.raise_for_status()
            data = r.json()
            
            # L'API Gamma renvoie souvent une liste directe
            batch = data if isinstance(data, list) else data.get("markets", [])
            
            if not batch:
                print("🏁 Fin de la liste atteinte.")
                break
                
            all_markets.extend(batch)
            print(f"   ↳ Récupérés: {len(all_markets)} (Offset: {offset})")
            
            offset += limit
            time.sleep(0.2) # Petite pause pour respecter le rate limit
            
        except Exception as e:
            print(f"⚠️ Erreur pagination (offset {offset}): {e}")
            break

    print(f"✅ Total marchés récupérés : {len(all_markets)}")
    return all_markets
