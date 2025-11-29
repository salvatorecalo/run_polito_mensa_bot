# utils/translations.py
"""
Translation utilities for multi-language support
"""

from typing import Dict

# Dizionario delle traduzioni
TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "italiano": {
        # Messaggi di benvenuto
        "welcome_back": "👋 Bentornato! Ti ho riattivato il servizio notifiche.",
        "welcome_new": "👋 Ciao {name}! Ti sei iscritto con successo.\n\n"
                      "Riceverai i menu delle mense che configuri ogni giorno.\n"
                      "Usa /menu per vedere il menu di oggi.\n"
                      "Usa /cancel per disiscriverti.\n"
                      "Usa /subscribe_canteen [NOME_MENSA] per ricevere i menù di quella mensa.\n"
                      "Usa /unsubscribe_canteen [NOME_MENSA] per smettere di ricevere i menù di quella mensa.\n"
                      "Puoi ricevere contemporaneamente il menù di più mense\n"
                      "Lingua impostata: 🇮🇹",
        
        # Errori
        "not_registered": "⚠️ Non sei registrato. Usa /start prima.",
        "no_canteens_subscribed": "⚠️ Non sei iscritto a nessuna mensa.\nUsa /subscribe_canteen per iscriverti.",
        "canteen_not_found": "❌ Mensa '{name}' non trovata nel database.\n\nDevi inserire una di queste mense:",
        "no_menu_available": "📅 <b>Menu del {date} ({meal_type})</b>\n\n❌ Nessun menu disponibile per le tue mense.\nRiprova più tardi.",
        
        # Subscribe/Unsubscribe
        "subscribe_success": "✅ Iscritto con successo alla mensa <b>{name}</b>!\n\n📋 <b>Sei iscritto a {count} mensa/e:</b>\n",
        "already_subscribed": "ℹ️ Sei già iscritto alla mensa <b>{name}</b>.",
        "unsubscribe_success": "✅ Disiscritto correttamente da <b>{name}</b>.\n\n",
        "not_subscribed": "⚠️ Non eri iscritto alla mensa <b>{name}</b>.",
        "still_subscribed_to": "📋 <b>Sei ancora iscritto a {count} mensa/e:</b>\n",
        "no_more_subscriptions": "ℹ️ Non sei più iscritto a nessuna mensa.",
        
        # Language
        "language_set": "Lingua impostata correttamente a {language}",
        "language_not_supported": "Lingua non supportata dall'attuale versione del bot.\nLe lingue supportate sono:\n",
        
        # Menu
        "menu_title": "🍽️ <b>Menu del {date} ({meal_type})</b>\n\n",
        "lunch": "pranzo",
        "dinner": "cena",
        "specify_canteen_name": "⚠️ Devi specificare il nome della mensa.\nEsempio: /subscribe_canteen Nome Mensa",
"cancel_success": "👋 Ti sei disiscritto correttamente.\nNon riceverai più notifiche automatiche.",
"not_subscribed_service": "ℹ️ Non eri iscritto.",
"no_permission": "❌ Non hai i permessi per eseguire questo comando.",
"add_mensa_syntax": "⚠️ Sintassi: /add_mensa [NOME_MENSA] [INDIRIZZO]",
"delete_mensa_syntax": "⚠️ Sintassi: /delete_mensa [NOME_MENSA]",
"canteen_already_exists": "⚠️ Questa mensa esiste già nel database.",
"canteen_added_success": "✅ Mensa <b>{name}</b> in {location} aggiunta correttamente!",
"canteen_deleted_success": "✅ Mensa <b>{name}</b> eliminata correttamente.",
"canteen_delete_error": "⚠️ Errore durante l'eliminazione della mensa.",
"no_canteens_in_db": "⚠️ Nessuna mensa configurata nel database.",
"all_canteens_list": "🍽️ <b>Tutte le mense disponibili:</b>",
"subscribed_canteens_list": "🍽️ <b>Le tue mense:</b>",
"set_language_syntax": "⚠️ Sintassi: /set_language [italiano/english]",
    },
    
    "english": {
        # Welcome messages
        "welcome_back": "👋 Welcome back! I've reactivated your notification service.",
        "welcome_new": "👋 Hello {name}! You've successfully registered.\n\n"
                      "You'll receive menus from the canteens you configure every day.\n"
                      "Use /menu to see today's menu.\n"
                      "Use /cancel to unsubscribe.\n"
                      "Use /subscribe_canteen [CANTEEN_NAME] to receive menus from that canteen.\n"
                      "Use /unsubscribe_canteen [CANTEEN_NAME] to stop receiving menus from that canteen.\n"
                      "You can receive menus from multiple canteens simultaneously\n"
                      "Language set: 🇬🇧",
        
        # Errors
        "not_registered": "⚠️ You're not registered. Use /start first.",
        "no_canteens_subscribed": "⚠️ You're not subscribed to any canteen.\nUse /subscribe_canteen to subscribe.",
        "canteen_not_found": "❌ Canteen '{name}' not found in database.\n\nYou must enter one of these canteens:",
        "no_menu_available": "📅 <b>Menu for {date} ({meal_type})</b>\n\n❌ No menu available for your canteens.\nPlease try again later.",
        
        # Subscribe/Unsubscribe
        "subscribe_success": "✅ Successfully subscribed to canteen <b>{name}</b>!\n\n📋 <b>You're subscribed to {count} canteen(s):</b>\n",
        "already_subscribed": "ℹ️ You're already subscribed to canteen <b>{name}</b>.",
        "unsubscribe_success": "✅ Successfully unsubscribed from <b>{name}</b>.\n\n",
        "not_subscribed": "⚠️ You weren't subscribed to canteen <b>{name}</b>.",
        "still_subscribed_to": "📋 <b>You're still subscribed to {count} canteen(s):</b>\n",
        "no_more_subscriptions": "ℹ️ You're no longer subscribed to any canteen.",
        
        # Language
        "language_set": "Language successfully set to {language}",
        "language_not_supported": "Language not supported by the current version of the bot.\nSupported languages are:\n",
        
        # Menu
        "menu_title": "🍽️ <b>Menu for {date} ({meal_type})</b>\n\n",
        "lunch": "lunch",
        "dinner": "dinner",
        "specify_canteen_name": "⚠️ You must specify the canteen name.\nExample: /subscribe_canteen Canteen Name",
"cancel_success": "👋 You've successfully unsubscribed.\nYou won't receive automatic notifications anymore.",
"not_subscribed_service": "ℹ️ You weren't subscribed.",
"no_permission": "❌ You don't have permission to execute this command.",
"add_mensa_syntax": "⚠️ Syntax: /add_mensa [CANTEEN_NAME] [ADDRESS]",
"delete_mensa_syntax": "⚠️ Syntax: /delete_mensa [CANTEEN_NAME]",
"canteen_already_exists": "⚠️ This canteen already exists in the database.",
"canteen_added_success": "✅ Canteen <b>{name}</b> at {location} added successfully!",
"canteen_deleted_success": "✅ Canteen <b>{name}</b> deleted successfully.",
"canteen_delete_error": "⚠️ Error while deleting the canteen.",
"no_canteens_in_db": "⚠️ No canteens configured in the database.",
"all_canteens_list": "🍽️ <b>All available canteens:</b>",
"subscribed_canteens_list": "🍽️ <b>Your canteens:</b>",
"set_language_syntax": "⚠️ Syntax: /set_language [italiano/english]",
    }
}


def get_text(language: str, key: str, **kwargs) -> str:
    """
    Get translated text for a given key
    
    Args:
        language: Language code ('italiano' or 'english')
        key: Translation key
        **kwargs: Format arguments for the string
    
    Returns:
        Translated and formatted string
    
    Example:
        get_text('italiano', 'subscribe_success', name='Mensa Centrale', count=2)
    """
    # Default to italiano if language not found
    lang = language if language in TRANSLATIONS else "italiano"
    
    # Get translation, default to key if not found
    text = TRANSLATIONS[lang].get(key, key)
    
    # Format with provided kwargs
    try:
        return text.format(**kwargs)
    except KeyError:
        return text