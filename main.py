import json
from polymarket import fetch_markets
from scanners.aggressive_scanner import run_aggressive_scanner
from telegram_client import send_message

def load_prompts():
    def r(p): return open(p).read()
    return {
        "system": r("prompts/system.txt"),
        "normalize": r("prompts/normalize.txt"),
        "hard_filter": r("prompts/hard_filter.txt"),
        "type4": r("prompts/type4_hard.txt"),
        "resolution": r("prompts/resolution_edge.txt"),
        "edge_quant": r("prompts/edge_quantification.txt"),
        "news_risk": r("prompts/news_resolution_risk.txt"),
        "checklist": r("prompts/checklist.txt"),
        "final": r("prompts/final_select_hard.txt")
    }

def main():
    markets = fetch_markets()
    prompts = load_prompts()
    result = run_aggressive_scanner(markets, prompts)
    send_message(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
