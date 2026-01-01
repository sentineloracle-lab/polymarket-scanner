import os

# --- API KEYS ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq") # ou "openai"

# --- STRATEGIE ---
MAX_MARKETS_TO_FETCH = 2000  # On creuse profond (Gamma API supporte ça)
MAX_AI_ANALYSIS = 40         # Max marchés envoyés à l'IA par run (Budget Control)

# --- FILTRES MATHÉMATIQUES (ZOMBIE HUNTER) ---
# On vise les marchés avec peu de volume récent (Zombies) mais de la liquidité bloquée
MIN_VOLUME = 200        
MIN_LIQUIDITY = 300     

# --- FICHIERS ---
CSV_LOG_FILE = "scan_history.csv"
