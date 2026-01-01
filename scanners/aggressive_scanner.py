import json
from llm_client import ask_llm
from quant.liquidity_score import compute_liquidity_score
from news.tavily_client import fetch_recent_news

def run_aggressive_scanner(markets, prompts):
    candidates = []

    for m in markets[:50]:
        norm = ask_llm(prompts["system"], prompts["normalize"].replace("{{DATA}}", json.dumps(m)))
        if "REJECTED" in ask_llm(prompts["system"], prompts["hard_filter"].replace("{{DATA}}", norm)):
            continue

        market = json.loads(norm)

        t4 = json.loads(ask_llm(prompts["system"], prompts["type4"].replace("{{DATA}}", json.dumps(market))))
        if t4["score"] < 80:
            continue

        res = json.loads(ask_llm(prompts["system"], prompts["resolution"].replace("{{DATA}}", json.dumps(market))))
        if res["score"] < 70:
            continue

        liq = compute_liquidity_score(market.get("volume"), market.get("liquidity"))
        if liq < 60:
            continue

        edge = json.loads(ask_llm(prompts["system"], prompts["edge_quant"].replace("{{DATA}}", json.dumps(market))))
        if edge["edge_percent"] < 10:
            continue

        news = fetch_recent_news(market["question"])
        news_eval = json.loads(
            ask_llm(
                prompts["system"],
                prompts["news_risk"]
                .replace("{{MARKET}}", json.dumps(market))
                .replace("{{NEWS}}", json.dumps(news))
            )
        )
        if news_eval["news_resolution_risk"] == "HIGH":
            continue

        checklist = json.loads(
            ask_llm(prompts["system"], prompts["checklist"].replace("{{DATA}}", json.dumps(market)))
        )
        if not checklist["checklist_passed"]:
            continue

        market.update({
            "type4": t4,
            "resolution": res,
            "liquidity_score": liq,
            "edge_quant": edge,
            "news_risk": news_eval,
            "checklist": checklist
        })

        candidates.append(market)

    if not candidates:
        return {"decision": "NO TRADE", "emoji": "⚪"}

    final = ask_llm(
        prompts["system"],
        prompts["final"].replace("{{DATA}}", json.dumps(candidates))
    )

    return json.loads(final)
