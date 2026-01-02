import requests
import logging

def fetch_markets():
    """Récupère les marchés actifs et liquides directement depuis l'API Gamma."""
    logging.info("📡 Scraping Gamma (Focus: Marchés Actifs)...")
    
    # URL avec filtres : Actifs seulement, classés par volume, excluant les marchés terminés
    # On limite à 500 pour la qualité
    url = "https://gamma-api.polymarket.com/markets"
    params = {
        "active": "true",
        "closed": "false",
        "order": "volume",
        "dir": "desc",
        "limit": 500,
        "offset": 0
    }
    
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            markets = response.json()
            # Nettoyage basique : s'assurer qu'il y a une question et un ID
            valid_markets = [m for m in markets if m.get('question') and m.get('id')]
            return valid_markets
        else:
            logging.error(f"Erreur Gamma API: {response.status_code}")
            return []
    except Exception as e:
        logging.error(f"Exception lors du fetch: {e}")
        return []
