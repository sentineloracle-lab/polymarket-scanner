import requests

def fetch_markets():
    url = "https://polymarket.com/api/markets"
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    return r.json()
  
