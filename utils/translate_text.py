from googletrans import Translator
from utils.logger import setup_logger
import re

logger = setup_logger(__name__)
translator = Translator()

async def translate_text(text: str, dest_language: str) -> str:
    try:
        if not text or not dest_language or dest_language == "it":
            return text
        
        # Keeps bot commands during translation
        command_pattern = r'(/[a-zA-Z_]+)'
        commands = re.findall(command_pattern, text)
        text_with_placeholders = text
        placeholders = {}
        for i, command in enumerate(commands):
            placeholder = f"__CMD{i}__"
            placeholders[placeholder] = command
            text_with_placeholders = text_with_placeholders.replace(command, placeholder, 1)
            
        result = await translator.translate(text_with_placeholders, dest=dest_language, src='it')
        if not result: return text
        
        translated_text = result.text
        for placeholder, command in placeholders.items():
            translated_text = translated_text.replace(placeholder, command)
        return translated_text
    except Exception as e:
        logger.error(f"Translation error: {e}")
        return text
