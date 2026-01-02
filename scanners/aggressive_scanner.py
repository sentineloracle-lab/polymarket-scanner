# Dans run_aggressive_scanner, remplacez la ligne system_prompt par :

    prompt_path = os.path.join("prompts", "mega_analysis.txt")
    if not os.path.exists(prompt_path):
        prompt_path = os.path.join("prompts", "system.txt")
    
    with open(prompt_path, "r", encoding="utf-8") as f:
        instructions = f.read()

    system_prompt = f"{instructions}\n\nIMPORTANT: Tu dois analyser chaque marché du batch et répondre UNIQUEMENT au format JSON : {{'results': [{{'id': '...', 'decision': 'OPPORTUNITY' ou 'REJECTED', 'confidence_score': 0-100, 'strategy': '...'}}, ...]}}"
