import os
import openai

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")

if LLM_PROVIDER == "qwen":
    openai.api_key = os.getenv("QWEN_API_KEY")
    openai.api_base = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    MODEL = "qwen-plus"

elif LLM_PROVIDER == "groq":
    openai.api_key = os.getenv("GROQ_API_KEY")
    openai.api_base = "https://api.groq.com/openai/v1"
    MODEL = "llama3-70b-8192"

else:
    raise ValueError("Unsupported LLM_PROVIDER")

def ask_llm(system_prompt, user_prompt):
    resp = openai.ChatCompletion.create(
        model=MODEL,
        temperature=0,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )
    return resp["choices"][0]["message"]["content"]
  
