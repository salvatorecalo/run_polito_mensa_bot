import google.generativeai as genai
from config import GOOGLE_API_KEY
from google.generativeai.types import HarmCategory, HarmBlockThreshold
class AiModel:
    def __init__(self):
        genai.configure(api_key=GOOGLE_API_KEY) # type: ignore
        # 2. Impostiamo i filtri di sicurezza al minimo per l'OCR dei menu
        self.safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }
        self.model = genai.GenerativeModel('gemini-3-flash-preview') # type: ignore