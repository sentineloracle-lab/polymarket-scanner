import requests
import os
import logging

def send_message(message):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        logging.error("Variables Telegram manquantes")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    # On essaie en Markdown, si ça échoue on envoie en texte brut
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            # Deuxième essai sans Markdown (au cas où le texte contient des caractères interdits)
            payload.pop("parse_mode")
            requests.post(url, json=payload)
            logging.info("Message envoyé en texte brut (Markdown échec)")
        else:
            logging.info("✅ Message Telegram envoyé")
    except Exception as e:
        logging.error(f"Erreur envoi: {e}")
