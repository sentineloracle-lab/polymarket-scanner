import os

# --- API KEYS ---
# Ces clés doivent être configurées dans les secrets GitHub
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini") # "gemini" par défaut
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# --- STRATÉGIE ---
MAX_MARKETS_TO_FETCH = 500  
MAX_AI_ANALYSIS = 30         # Gemini permet d'analyser plus de marchés

# --- FILTRES MATHÉMATIQUES ---
MIN_VOLUME = 200        
MIN_LIQUIDITY = 300     

# --- FICHIERS ---
CSV_LOG_FILE = "scan_history.csv"
