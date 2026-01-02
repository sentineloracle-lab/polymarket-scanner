import requests
import logging

def fetch_markets():
    """
    Récupère les événements de marché actifs et liquides.
    Utilise l'endpoint /events pour une meilleure qualité de données.
    """
    logging.info("📡 Scraping Gamma API (Focus: Marchés Actifs & Liquides)...")
    
    # On utilise /events car c'est là que se trouvent les vrais volumes et questions claires
    url = "https://gamma-api.polymarket.com/events"
    
    params = {
        "limit": 500,
        "offset": 0,
        "active": "true",        # Uniquement ceux qui acceptent des paris
        "closed": "false",       # Pas ceux qui sont finis
        "order": "volume",       # Les plus populaires en premier
        "dir": "desc",
        "is_active": "true"      # Double sécurité pour le statut actif
    }
    
    # L'API Gamma peut parfois bloquer les requêtes sans User-Agent
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=15)
        
        if response.status_code == 200:
            events = response.json()
            markets_list = []
            
            for event in events:
                # Un 'event' contient souvent une liste de 'markets'
                # On extrait la question principale et les métriques
                question = event.get('title') or event.get('description')
                event_id = event.get('id')
                
                # On récupère les métriques de liquidité/volume de l'événement
                # L'API Gamma place souvent la liquidité ici
                liquidity = event.get('liquidity', 0)
                volume = event.get('volume', 0)
                
                if question and event_id:
                    markets_list.append({
                        'id': event_id,
                        'question': question,
                        'liquidity': liquidity,
                        'volume': volume,
                        'description': event.get('description', ''),
                        'active': event.get('active'),
                        'closed': event.get('closed')
                    })
            
            logging.info(f"✅ {len(markets_list)} événements récupérés avec succès.")
            return markets_list
            
        else:
            logging.error(f"❌ Erreur Gamma API: {response.status_code} - {response.text}")
            return []
            
    except Exception as e:
        logging.error(f"💥 Exception lors du fetch Gamma: {e}")
        return []
