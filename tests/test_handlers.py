"""
Test suite for bot handlers
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram import Chat, Message, Update, User
from telegram.ext import ContextTypes

from bot.handlers import cancel_command, menu_command, start_command


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


@pytest.mark.asyncio
async def test_start_command(mock_update, mock_context):
    """Test /start command"""
    with patch("bot.handlers.UserRepository") as MockRepo:
        mock_repo_instance = MockRepo.return_value
        mock_repo_instance.get_or_create = AsyncMock(
            return_value=MagicMock(is_active=True, first_name="TestUser")
        )
        mock_repo_instance.update_status = AsyncMock()

        # Mock get_session to yield a mock session
        with patch("bot.handlers.get_session") as mock_get_session:
            mock_session = AsyncMock()

            async def session_gen():
                yield mock_session

            mock_get_session.return_value = session_gen()

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

        with patch("bot.handlers.get_session") as mock_get_session:
            mock_session = AsyncMock()

            async def session_gen():
                yield mock_session

            mock_get_session.return_value = session_gen()

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

        with patch("bot.handlers.get_session") as mock_get_session:
            mock_session = AsyncMock()

            async def session_gen():
                yield mock_session

            mock_get_session.return_value = session_gen()

            await menu_command(mock_update, mock_context)

            mock_update.message.reply_text.assert_called_once()
            assert "Menu content" in mock_update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_cancel_command(mock_update, mock_context):
    """Test /cancel command"""
    with patch("bot.handlers.UserRepository") as MockRepo:
        mock_repo_instance = MockRepo.return_value
        mock_repo_instance.update_status = AsyncMock(return_value=True)

        with patch("bot.handlers.get_session") as mock_get_session:
            mock_session = AsyncMock()

            async def session_gen():
                yield mock_session

            mock_get_session.return_value = session_gen()

            await cancel_command(mock_update, mock_context)

        mock_repo_instance.update_status.assert_called_once_with(
            123456789, is_active=False
        )
        mock_update.message.reply_text.assert_called_once()
        assert "disiscritto" in mock_update.message.reply_text.call_args[0][0]
