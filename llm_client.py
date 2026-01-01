import os
from openai import OpenAI

def ask_llm(system_prompt, user_prompt):
    # Récupération des clés
    provider = os.getenv("LLM_PROVIDER", "groq")
    api_key = os.getenv("GROQ_API_KEY") if provider == "groq" else os.getenv("OPENAI_API_KEY")
    
    # Configuration de l'URL de base pour Groq
    base_url = "https://api.groq.com/openai/v1" if provider == "groq" else None
    
    # Nouvelle syntaxe OpenAI v1.0+
    client = OpenAI(api_key=api_key, base_url=base_url)
    
    try:
        model = "llama-3.3-70b-versatile" if provider == "groq" else "gpt-4"
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"❌ Erreur LLM: {e}")
        return "ERROR_AI_COMMUNICATION"

