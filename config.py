import os

# --- API KEYS ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini") # Changé de "groq" à "gemini"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") # À ajouter dans tes secrets GitHub

# --- STRATEGIE ---
MAX_MARKETS_TO_FETCH = 500  
MAX_AI_ANALYSIS = 30         # Avec Gemini, on peut se permettre d'analyser plus de marchés

# --- FILTRES MATHÉMATIQUES ---
MIN_VOLUME = 200        
MIN_LIQUIDITY = 300     

# --- FICHIERS ---
CSV_LOG_FILE = "scan_history.csv"
