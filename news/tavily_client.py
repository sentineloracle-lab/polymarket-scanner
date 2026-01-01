import requests
import os
import logging

def get_market_news(query):
    """Recherche des news via Tavily avec gestion d'erreur robuste."""
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return "No Tavily API Key found."
    
    url = "https://api.tavily.com/search"
    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": "advanced",
        "max_results": 3
    }
    
    try:
        response = requests.post(url, json=payload, timeout=15)
        # Si erreur 401 ou autre, on ne crash pas, on retourne une info vide
        if response.status_code != 200:
            logging.warning(f"Tavily API Error {response.status_code}")
            return "No recent news available (API limit/error)."
            
        data = response.json()
        results = data.get("results", [])
        
        news_text = ""
        for res in results:
            news_text += f"- {res['title']}: {res['content'][:200]}...\n"
        
        return news_text if news_text else "No specific news found."
        
    except Exception as e:
        logging.error(f"Error fetching news: {e}")
        return "Search failed."
