from telegram.ext import CallbackQueryHandler, ChatMemberHandler, CommandHandler, MessageHandler, filters
from bot import add_canteen, debug_menus, debug_user_in_a_canteen, delete_canteen, handle_callback, menu_command, refresh_menu, start_command, switch_user_role
from bot.send_messages_to_everyone import send_message_to_everyone
from bot.show_canteen_buttons import cancel_command, get_user_image_or_text_option, set_language, set_user_image_or_text_option, subscribe_canteen, unsubscribe_canteen
from utils.handle_private_message import handle_private_message
from utils.bot_added_to_group import bot_added_to_group

def define_all_handlers(app):
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("menu", menu_command))
    app.add_handler(CommandHandler("cancel", cancel_command))
    app.add_handler(CommandHandler("subscribe_canteen", subscribe_canteen))
    app.add_handler(CommandHandler("unsubscribe_canteen", unsubscribe_canteen))
    app.add_handler(CommandHandler("add_canteen", add_canteen))
    app.add_handler(CommandHandler("delete_canteen", delete_canteen))
    app.add_handler(CommandHandler("set_language", set_language))
    app.add_handler(CommandHandler("refresh_menu", refresh_menu))
    app.add_handler(CommandHandler("set_user_image_or_text_option", set_user_image_or_text_option))
    app.add_handler(CommandHandler("get_user_image_or_text_option", get_user_image_or_text_option))
    app.add_handler(CommandHandler("switch_user_role", switch_user_role))
    app.add_handler(CommandHandler("debug_menus", debug_menus))
    app.add_handler(CommandHandler("broadcast", send_message_to_everyone))
    app.add_handler(CommandHandler("debug_user_in_a_canteen", debug_user_in_a_canteen))
    app.add_handler(
        ChatMemberHandler(bot_added_to_group, ChatMemberHandler.MY_CHAT_MEMBER)
    )
    app.add_handler(
        MessageHandler(filters.ChatType.PRIVATE, handle_private_message)
    )
    