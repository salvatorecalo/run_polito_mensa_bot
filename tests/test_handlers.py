"""
Test suite for bot handlers
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram import Chat, Message, Update, User, CallbackQuery
from telegram.ext import ContextTypes

from bot.handlers import (
    cancel_command, menu_command, start_command, handle_callback,
    show_canteen_buttons, handle_canteen_toggle, show_language_buttons,
    handle_language_change, get_user_image_or_text_option, set_language,
    subscribe_canteen, unsubscribe_canteen, set_user_image_or_text_option,
    get_user_image_or_text_option_cmd, refresh_menu, add_canteen,
    delete_canteen, switch_user_role, debug_menus
)
from database.connection import init_db


@pytest.fixture
def mock_update():
    update = MagicMock(spec=Update)
    update.effective_user = MagicMock(spec=User)
    update.effective_user.id = 123456789
    update.effective_user.first_name = "TestUser"
    update.effective_user.username = "testuser"
    update.message = MagicMock(spec=Message)
    update.message.chat = MagicMock(spec=Chat)
    update.message.chat.id = 123456789
    update.effective_chat = update.message.chat
    update.effective_message = update.message
    update.message.reply_text = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    return context


@pytest.fixture
async def init_test_db():
    await init_db("sqlite+aiosqlite:///:memory:")
    yield
    # Cleanup if needed


@pytest.fixture
def mock_callback_update():
    update = MagicMock(spec=Update)
    update.callback_query = MagicMock(spec=CallbackQuery)
    update.callback_query.from_user = MagicMock(spec=User)
    update.callback_query.from_user.id = 123456789
    update.callback_query.data = "menu"
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    update.callback_query.message = MagicMock(spec=Message)
    update.callback_query.message.reply_text = AsyncMock()
    return update


@pytest.mark.asyncio
async def test_start_command(mock_update, mock_context):
    """Test /start command"""
    with patch("bot.handlers.UserRepository") as MockRepo:
        mock_repo_instance = MockRepo.return_value
        mock_repo_instance.get_or_create = AsyncMock(
            return_value=MagicMock(is_active=True, first_name="TestUser")
        )
        mock_repo_instance.update_status = AsyncMock()
        # Mock get_session_maker to yield a mock session
        with patch("database.connection.get_session_maker") as mock_get_session_maker:
            mock_session_maker = AsyncMock()
            mock_session = AsyncMock()
            mock_session_maker.return_value = mock_session
            mock_get_session_maker.return_value = mock_session_maker

            await start_command(mock_update, mock_context)

        mock_repo_instance.get_or_create.assert_called_once()
        mock_update.message.reply_text.assert_called_once()
        assert (
            "Benvenuto" in mock_update.message.reply_text.call_args[0][0]
            or "Ciao" in mock_update.message.reply_text.call_args[0][0]
        )


@pytest.mark.asyncio
async def test_menu_command_no_menu(mock_update, mock_context):
    """Test /menu command when no menu is available"""
    with (
        patch("bot.handlers.UserRepository") as MockUserRepo,
        patch("bot.handlers.MenuRepository") as MockMenuRepo,
        patch("bot.handlers.CanteenRepository") as MockCanteenRepo,
    ):
        mock_user_repo = MockUserRepo.return_value
        mock_user_repo.get_by_telegram_id = AsyncMock(
            return_value=MagicMock(selected_canteen_id=1)
        )

        mock_menu_repo = MockMenuRepo.return_value
        mock_menu_repo.get_menu_by_date = AsyncMock(return_value=None)

        mock_canteen_repo = MockCanteenRepo.return_value
        mock_canteen_repo.get_by_id = AsyncMock(return_value=MagicMock(name="Mensa"))

        with patch("database.connection.get_session_maker") as mock_get_session_maker:
            mock_session_maker = AsyncMock()
            mock_session = AsyncMock()
            mock_session_maker.return_value = mock_session
            mock_get_session_maker.return_value = mock_session_maker

            await menu_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        assert (
            "non è ancora disponibile" in mock_update.message.reply_text.call_args[0][0]
        )


@pytest.mark.asyncio
async def test_menu_command_with_menu(mock_update, mock_context):
    """Test /menu command with available menu"""
    with (
        patch("bot.handlers.UserRepository") as MockUserRepo,
        patch("bot.handlers.MenuRepository") as MockMenuRepo,
        patch("bot.handlers.CanteenRepository") as MockCanteenRepo,
    ):
        mock_user_repo = MockUserRepo.return_value
        mock_user_repo.get_by_telegram_id = AsyncMock(
            return_value=MagicMock(selected_canteen_id=1)
        )

        mock_menu_repo = MockMenuRepo.return_value
        mock_menu = MagicMock()
        mock_menu.date = "2023-10-27"
        mock_menu.translated_text = "Menu content"
        mock_menu_repo.get_menu_by_date = AsyncMock(return_value=mock_menu)

        mock_canteen_repo = MockCanteenRepo.return_value
        mock_canteen_repo.get_by_id = AsyncMock(return_value=MagicMock(name="Mensa"))

        with patch("database.connection.get_session_maker") as mock_get_session_maker:
            mock_session_maker = AsyncMock()
            mock_session = AsyncMock()
            mock_session_maker.return_value = mock_session
            mock_get_session_maker.return_value = mock_session_maker

            mock_update.message.reply_text.assert_called_once()
            assert "Menu content" in mock_update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_cancel_command(mock_update, mock_context):
    """Test /cancel command"""
    with patch("bot.handlers.UserRepository") as MockRepo:
        mock_repo_instance = MockRepo.return_value
        mock_repo_instance.update_status = AsyncMock(return_value=True)

        with patch("database.connection.get_session_maker") as mock_get_session_maker:
            mock_session_maker = AsyncMock()
            mock_session = AsyncMock()
            mock_session_maker.return_value = mock_session
            mock_get_session_maker.return_value = mock_session_maker

            await cancel_command(mock_update, mock_context)

        mock_repo_instance.update_status.assert_called_once_with(
            123456789, is_active=False
        )
        mock_update.message.reply_text.assert_called_once()
        assert "disiscritto" in mock_update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_handle_callback_menu(mock_callback_update, mock_context):
    """Test handle_callback with data='menu'"""
    mock_callback_update.callback_query.data = "menu"
    with patch("bot.handlers.UserRepository") as MockUserRepo, \
         patch("bot.handlers.menu_command") as mock_menu_command:
        mock_user_repo = MockUserRepo.return_value
        mock_user_repo.get_by_telegram_id = AsyncMock(return_value=MagicMock())

        with patch("database.connection.get_session_maker") as mock_get_session_maker:
            mock_session_maker = AsyncMock()
            mock_session = AsyncMock()
            mock_session_maker.return_value = mock_session
            mock_get_session_maker.return_value = mock_session_maker

            await handle_callback(mock_callback_update, mock_context)

        mock_menu_command.assert_called_once_with(mock_callback_update, mock_context)


@pytest.mark.asyncio
async def test_handle_callback_subscribe_canteen(mock_callback_update, mock_context):
    """Test handle_callback with data='subscribe_canteen'"""
    mock_callback_update.callback_query.data = "subscribe_canteen"
    with patch("bot.handlers.UserRepository") as MockUserRepo, \
         patch("bot.handlers.show_canteen_buttons") as mock_show_canteen:
        mock_user_repo = MockUserRepo.return_value
        mock_user_repo.get_by_telegram_id = AsyncMock(return_value=MagicMock())

        with patch("database.connection.get_session_maker") as mock_get_session_maker:
            mock_session_maker = AsyncMock()
            mock_session = AsyncMock()
            mock_session_maker.return_value = mock_session
            mock_get_session_maker.return_value = mock_session_maker

            await handle_callback(mock_callback_update, mock_context)

        mock_show_canteen.assert_called_once()


@pytest.mark.asyncio
async def test_handle_callback_toggle_canteen(mock_callback_update, mock_context):
    """Test handle_callback with toggle_canteen_1"""
    mock_callback_update.callback_query.data = "toggle_canteen_1"
    with patch("bot.handlers.UserRepository") as MockUserRepo, \
         patch("bot.handlers.handle_canteen_toggle") as mock_toggle:
        mock_user_repo = MockUserRepo.return_value
        mock_user_repo.get_by_telegram_id = AsyncMock(return_value=MagicMock())

        with patch("database.connection.get_session_maker") as mock_get_session_maker:
            mock_session_maker = AsyncMock()
            mock_session = AsyncMock()
            mock_session_maker.return_value = mock_session
            mock_get_session_maker.return_value = mock_session_maker

            await handle_callback(mock_callback_update, mock_context)

        mock_toggle.assert_called_once_with(mock_callback_update, mock_context, session=mock_session, canteen_id=1)


@pytest.mark.asyncio
async def test_handle_callback_set_language(mock_callback_update, mock_context):
    """Test handle_callback with data='set_language'"""
    mock_callback_update.callback_query.data = "set_language"
    with patch("bot.handlers.UserRepository") as MockUserRepo, \
         patch("bot.handlers.show_language_buttons") as mock_show_lang:
        mock_user_repo = MockUserRepo.return_value
        mock_user_repo.get_by_telegram_id = AsyncMock(return_value=MagicMock())

        with patch("database.connection.get_session_maker") as mock_get_session_maker:
            mock_session_maker = AsyncMock()
            mock_session = AsyncMock()
            mock_session_maker.return_value = mock_session
            mock_get_session_maker.return_value = mock_session_maker

            await handle_callback(mock_callback_update, mock_context)

        mock_show_lang.assert_called_once_with(mock_callback_update, mock_context)


@pytest.mark.asyncio
async def test_handle_callback_lang_change(mock_callback_update, mock_context):
    """Test handle_callback with lang_en"""
    mock_callback_update.callback_query.data = "lang_en"
    with patch("bot.handlers.UserRepository") as MockUserRepo, \
         patch("bot.handlers.handle_language_change") as mock_lang_change:
        mock_user_repo = MockUserRepo.return_value
        mock_user_repo.get_by_telegram_id = AsyncMock(return_value=MagicMock())

        with patch("database.connection.get_session_maker") as mock_get_session_maker:
            mock_session_maker = AsyncMock()
            mock_session = AsyncMock()
            mock_session_maker.return_value = mock_session
            mock_get_session_maker.return_value = mock_session_maker

            await handle_callback(mock_callback_update, mock_context)

        mock_lang_change.assert_called_once_with(mock_callback_update, mock_context, new_lang="en")


@pytest.mark.asyncio
async def test_handle_callback_get_format(mock_callback_update, mock_context):
    """Test handle_callback with data='get_format'"""
    mock_callback_update.callback_query.data = "get_format"
    with patch("bot.handlers.UserRepository") as MockUserRepo, \
         patch("bot.handlers.get_user_image_or_text_option") as mock_get_format:
        mock_user_repo = MockUserRepo.return_value
        mock_user_repo.get_by_telegram_id = AsyncMock(return_value=MagicMock())

        with patch("database.connection.get_session_maker") as mock_get_session_maker:
            mock_session_maker = AsyncMock()
            mock_session = AsyncMock()
            mock_session_maker.return_value = mock_session
            mock_get_session_maker.return_value = mock_session_maker

            await handle_callback(mock_callback_update, mock_context)

        mock_get_format.assert_called_once_with(mock_callback_update, mock_context)


@pytest.mark.asyncio
async def test_handle_callback_set_format(mock_callback_update, mock_context):
    """Test handle_callback with set_format_image"""
    mock_callback_update.callback_query.data = "set_format_image"
    with patch("bot.handlers.UserRepository") as MockUserRepo, \
         patch("bot.handlers.start_command") as mock_start:
        mock_user = MagicMock()
        mock_user_repo = MockUserRepo.return_value
        mock_user_repo.get_by_telegram_id = AsyncMock(return_value=mock_user)

        with patch("database.connection.get_session_maker") as mock_get_session_maker:
            mock_session_maker = AsyncMock()
            mock_session = AsyncMock()
            mock_session_maker.return_value = mock_session
            mock_get_session_maker.return_value = mock_session_maker

            await handle_callback(mock_callback_update, mock_context)

        assert mock_user.image_or_text == "image"
        mock_callback_update.callback_query.edit_message_text.assert_called_once()
        mock_start.assert_called_once_with(mock_callback_update, mock_context)


@pytest.mark.asyncio
async def test_handle_callback_cancel(mock_callback_update, mock_context):
    """Test handle_callback with data='cancel'"""
    mock_callback_update.callback_query.data = "cancel"
    with patch("bot.handlers.UserRepository") as MockUserRepo:
        mock_user_repo = MockUserRepo.return_value
        mock_user_repo.get_by_telegram_id = AsyncMock(return_value=MagicMock())
        mock_user_repo.update_status = AsyncMock()

        with patch("database.connection.get_session_maker") as mock_get_session_maker:
            mock_session_maker = AsyncMock()
            mock_session = AsyncMock()
            mock_session_maker.return_value = mock_session
            mock_get_session_maker.return_value = mock_session_maker

            await handle_callback(mock_callback_update, mock_context)

        mock_user_repo.update_status.assert_called_once_with(123456789, is_active=False)
        mock_callback_update.callback_query.edit_message_text.assert_called_once()


@pytest.mark.asyncio
async def test_handle_callback_start_back(mock_callback_update, mock_context):
    """Test handle_callback with data='start_back'"""
    mock_callback_update.callback_query.data = "start_back"
    with patch("bot.handlers.UserRepository") as MockUserRepo, \
         patch("bot.handlers.start_command") as mock_start:
        mock_user_repo = MockUserRepo.return_value
        mock_user_repo.get_by_telegram_id = AsyncMock(return_value=MagicMock())

        with patch("database.connection.get_session_maker") as mock_get_session_maker:
            mock_session_maker = AsyncMock()
            mock_session = AsyncMock()
            mock_session_maker.return_value = mock_session
            mock_get_session_maker.return_value = mock_session_maker

            await handle_callback(mock_callback_update, mock_context)

        mock_start.assert_called_once_with(mock_callback_update, mock_context)


@pytest.mark.asyncio
async def test_handle_callback_no_user(mock_callback_update, mock_context):
    """Test handle_callback when user not found"""
    with patch("bot.handlers.UserRepository") as MockUserRepo:
        mock_user_repo = MockUserRepo.return_value
        mock_user_repo.get_by_telegram_id = AsyncMock(return_value=None)

        with patch("database.connection.get_session_maker") as mock_get_session_maker:
            mock_session_maker = AsyncMock()
            mock_session = AsyncMock()
            mock_session_maker.return_value = mock_session
            mock_get_session_maker.return_value = mock_session_maker

            await handle_callback(mock_callback_update, mock_context)

        # Should not call any further functions
        mock_callback_update.callback_query.edit_message_text.assert_not_called()


# Add more tests for other handlers as needed
