import json
import time
import csv
import os
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from llm_client import ask_llm
from news.tavily_client import fetch_recent_news
from config import MIN_VOLUME, MIN_LIQUIDITY, CSV_LOG_FILE, MAX_AI_ANALYSIS

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def clean_json_response(raw_text):
    try:
        match = re.search(r'(\{.*\}|\[.*\])', raw_text, re.DOTALL)
        if match:
            return match.group(0)
        return raw_text.strip()
    except:
        return raw_text.strip()

def append_to_csv(rows):
    file_exists = os.path.isfile(CSV_LOG_FILE)
    with open(CSV_LOG_FILE, mode='a', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Timestamp", "Question", "ID", "Volume", "Liquidity", "Decision", "Strategy", "Confidence", "Edge", "Risk_Flags"])
        writer.writerows(rows)

def analyze_single_market(market, prompts):
    # Petite pause pour éviter le Rate Limit Groq
    time.sleep(2) 
    try:
        analysis_raw = ask_llm(prompts["system"], prompts["mega_analysis"].replace("{{DATA}}", json.dumps(market)))
        content = clean_json_response(analysis_raw)
        analysis = json.loads(content)

        if not analysis.get("is_interesting") or analysis.get("confidence_score", 0) < 80:
            return {"status": "REJECTED_AI", "market": market, "analysis": analysis}

        news = fetch_recent_news(market['question'])
        
        checklist_raw = ask_llm(prompts["system"], prompts["checklist"].replace("{{DATA}}", json.dumps(market)).replace("{{NEWS}}", json.dumps(news)))
        checklist = json.loads(clean_json_response(checklist_raw))
        
        if not checklist.get("checklist_passed", False):
            analysis["risk_flags"] = str(checklist.get("risk_flags", []))
            return {"status": "REJECTED_CHECKLIST", "market": market, "analysis": analysis}

        return {"status": "ACCEPTED", "market": market, "analysis": analysis}
    except Exception as e:
        return {"status": f"ERROR: {str(e)[:50]}", "market": market, "analysis": None}

def run_aggressive_scanner(markets, prompts):
    logging.info(f"🔄 Filtrage de {len(markets)} marchés...")
    pre_filtered = [m for m in markets if float(m.get("volume") or 0) >= MIN_VOLUME]
    pre_filtered.sort(key=lambda x: float(x.get("liquidity") or 0), reverse=True)
    
    targets = pre_filtered[:MAX_AI_ANALYSIS]
    candidates, csv_buffer = [], []
    
    # max_workers=1 pour ne pas saturer Groq Free
    with ThreadPoolExecutor(max_workers=1) as executor:
        future_to_market = {executor.submit(analyze_single_market, m, prompts): m for m in targets}
        for future in as_completed(future_to_market):
            m = future_to_market[future]
            res = future.result()
            status, an = res["status"], res["analysis"]
            
            csv_buffer.append([time.strftime("%Y-%m-%d %H:%M:%S"), m.get("question"), m.get("id"), m.get("volume"), m.get("liquidity"), status, an.get("strategy_type", "N/A") if an else "N/A", an.get("confidence_score", 0) if an else 0, an.get("estimated_edge", 0) if an else 0, an.get("risk_flags", "") if an else ""])
            if status == "ACCEPTED":
                candidates.append(res["market"])

    append_to_csv(csv_buffer)
    if not candidates: return {"decision": "NO_OPPORTUNITY"}

    final_msg = ask_llm(prompts["system"], prompts["final_summary"].replace("{{DATA}}", json.dumps(candidates)))
    return {"decision": "OPPORTUNITY_FOUND", "count": len(candidates), "telegram_message": final_msg}
