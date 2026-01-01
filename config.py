import os

# --- API KEYS ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq") # ou "openai"

# --- STRATEGIE ---
# Réduit pour éviter de saturer l'API dans le Cloud
MAX_MARKETS_TO_FETCH = 500  
# Très important : réduit à 10 pour ne pas dépasser le quota "Tokens Per Minute" de Groq Free
MAX_AI_ANALYSIS = 10         

# --- FILTRES MATHÉMATIQUES (ZOMBIE HUNTER) ---
# Seuils ajustés pour capturer les marchés avec liquidité dormante
MIN_VOLUME = 150        
MIN_LIQUIDITY = 150     

# --- FICHIERS ---
CSV_LOG_FILE = "scan_history.csv"
