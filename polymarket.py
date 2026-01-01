import requests
import time

# VERSION CORRIGEE 2026.01.01 - SANS PARAMETRE ORDER
def fetch_markets():
    all_markets = []
    limit = 100
    offset = 0
    
    print(f"📡 Scraping Gamma (Cible: 500)...")

    while len(all_markets) < 500:
        try:
            params = {
                "active": "true",
                "limit": limit,
                "offset": offset
            }
            
            # Appel direct sans variables de session complexes pour tester
            r = requests.get("https://gamma-api.polymarket.com/markets", params=params, timeout=15)
            
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
            time.sleep(0.2) 
            
        except Exception as e:
            print(f"⚠️ Erreur: {e}")
            break

    return all_markets
