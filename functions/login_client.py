from instagrapi import Client
import os
from config import *
from instagrapi.exceptions import TwoFactorRequired, ChallengeRequired

def login_client() -> Client:
    """
        This. function provides login to instagram client with instagrapi (module)
    """
    cl = Client()
    if os.path.exists(SESSION_FILE):
        try:
            cl.load_settings(SESSION_FILE)
        except Exception as e:
            print("Errore caricamento sessione:", e)
    try:
        cl.login(IG_USERNAME, IG_PASSWORD)
        cl.dump_settings(SESSION_FILE)
        print("Login Instagram OK")
        return cl
    except TwoFactorRequired:
        print("2FA richiesta, completa manualmente.")
        raise
    except ChallengeRequired:
        print("Challenge richiesta, accedi via app e riprova.")
        raise
    except Exception as e:
        print("Errore login IG:", e)
        raise
