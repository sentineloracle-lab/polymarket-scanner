import os

# --- API KEYS ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq") 

# --- STRATEGIE ---
MAX_MARKETS_TO_FETCH = 500  
MAX_AI_ANALYSIS = 10         # Limité à 10 pour éviter le spam de l'API gratuite

# --- FILTRES MATHÉMATIQUES (ZOMBIE HUNTER) ---
MIN_VOLUME = 150        
MIN_LIQUIDITY = 150     

# --- FICHIERS ---
CSV_LOG_FILE = "scan_history.csv"
