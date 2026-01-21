import base64
import re
from groq import Groq
from config.settings import GROQ_API_KEY
from utils.logger import setup_logger

logger = setup_logger(__name__)

class AiModel:
    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY)
        self.model_id = "meta-llama/llama-4-scout-17b-16e-instruct"
    
    def _clean_output(self, text: str) -> str:
        """
        Estrae solo il contenuto tra i tag <MENU> e </MENU>.
        Se i tag mancano, applica una pulizia aggressiva sulle prime righe.
        """
        match = re.search(r"<MENU>(.*?)</MENU>", text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()

        # Fallback: Pulizia riga per riga se il modello ignora i tag
        lines = text.split('\n')
        cleaned_lines = []
        
        # Parole che indicano l'inizio di una frase introduttiva
        intro_keywords = ["ecco", "certamente", "testo estratto", "menu della mensa", "ho estratto", "Ecco il testo pulito del menu della mensa:", "Ecco il testo pulito:"]
        
        for line in lines:
            line_strip = line.strip()
            # Saltiamo righe vuote o frasi che iniziano con le keyword e finiscono con i due punti
            is_intro = any(line_strip.lower().startswith(kw) for kw in intro_keywords)
            if is_intro and (line_strip.endswith(':') or len(line_strip) < 60):
                continue
            cleaned_lines.append(line)
            
        return "\n".join(cleaned_lines).strip()
    
    def extracted_text(self, image_path: str) -> str:
        try:
            with open(image_path, "rb") as image_file:
                image_base64 = base64.b64encode(image_file.read()).decode('utf-8')

            completion = self.client.chat.completions.create(
                model=self.model_id,
                messages=[
                    {
                        "role": "system", 
                        "content": (
                            "Sei un estrattore OCR robotico. Estrai il testo dall'immagine e "
                            "racchiudilo ESCLUSIVAMENTE tra i tag <MENU> e </MENU>. "
                            "Esempio: <MENU>\nTesto trovato...\n</MENU>\n"
                            "NON aggiungere nient'altro fuori dai tag."
                        )
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Estrai il testo dell'immagine tra i tag <MENU>."},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
                            }
                        ]
                    }
                ],
                temperature=0.0, # 0.0 riduce la "parlantina" del modello
                max_tokens=2048,
            )

            raw_text = completion.choices[0].message.content
            if not raw_text:
                return ""
                
            return self._clean_output(raw_text)
            
        except Exception as e:
            logger.error(f"❌ Errore Groq API: {e}")
            return ""