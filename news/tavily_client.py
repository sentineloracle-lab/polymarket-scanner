import os
import requests

def fetch_recent_news(query):
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return []

    url = "https://api.tavily.com/search"
    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": "advanced", # Corrigé: 'advanced' au lieu de 'news'
        "max_results": 3
    }

    try:
        response = requests.post(url, json=payload, timeout=15)
        if response.status_code == 200:
            results = response.json().get("results", [])
            return [f"{r['title']}: {r['content']}" for r in results]
        return []
    except:
        return []
