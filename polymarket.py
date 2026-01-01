import requests

def fetch_markets(limit=500):
    # On force un limit plus élevé et on demande les marchés actifs
    # Note: L'API publique de Polymarket change parfois, on utilise ici une requête large
    url = f"https://polymarket.com/api/markets?limit={limit}&active=true&closed=false"
    
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        data = r.json()
        
        # Gestion des différents formats de réponse possibles de l'API
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and "markets" in data:
            return data["markets"]
        else:
            print("⚠️ Format API inattendu, retour brut.")
            return []
            
    except Exception as e:
        print(f"❌ Erreur fetch_markets: {e}")
        return []

