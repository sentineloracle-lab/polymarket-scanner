import os

# --- API KEYS ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")

# --- STRATEGIE ---
SCANNER_MODE = "aggressive"
MAX_MARKETS_TO_FETCH = 2000  # Profondeur du chalut (Gamma API)
MAX_AI_ANALYSIS = 40         # Nombre max de marchés envoyés à l'IA par run

# --- FILTRES MATHÉMATIQUES ---
# Optimisé pour attraper les "Zombie Markets" (faible volume récent mais liquidité présente)
MIN_VOLUME = 200        
MIN_LIQUIDITY = 300     

# --- FICHIERS ---
CSV_LOG_FILE = "scan_history.csv"
