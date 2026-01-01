import os
import requests

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

def fetch_recent_news(query, days=7, max_results=5):
    url = "https://api.tavily.com/search"
    payload = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        "search_depth": "advanced",
        "max_results": max_results,
        "days": days
    }
    r = requests.post(url, json=payload, timeout=20)
    r.raise_for_status()
    return r.json().get("results", [])
  
