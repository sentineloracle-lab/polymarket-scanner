import os
import requests

def fetch_recent_news(query):
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        print("⚠️ TAVILY_API_KEY manquante.")
        return []

    url = "https://api.tavily.com/search"
    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": "news",
        "max_results": 3
    }

    try:
        response = requests.post(url, json=payload, timeout=15)
        if response.status_code == 200:
            results = response.json().get("results", [])
            return [f"{r['title']}: {r['content']}" for r in results]
        else:
            print(f"⚠️ Erreur Tavily {response.status_code}: {response.text}")
            return []
    except Exception as e:
        print(f"❌ Exception Tavily: {e}")
        return []
