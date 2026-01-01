import os
from telegram_client import send_message

def test():
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    print("--- TEST TELEGRAM ---")
    print(f"Token présent : {'OUI' if token else 'NON'}")
    print(f"Chat ID présent : {'OUI' if chat_id else 'NON'}")
    
    test_msg = "🚀 Test de connexion Polymarket Scanner !\n\nSi vous recevez ce message, votre setup Telegram est VALIDE."
    
    try:
        send_message(test_msg)
        print("✅ Message envoyé avec succès ! Vérifie ton Telegram.")
    except Exception as e:
        print(f"❌ Échec de l'envoi : {e}")

if __name__ == "__main__":
    test()
