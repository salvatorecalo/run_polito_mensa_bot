"""
Test suite per bot.handlers
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from telegram import Update, Message, Chat, User
from telegram.ext import ContextTypes
from bot.handlers import start_command, help_command, cancel_command


@pytest.fixture
def mock_update():
    """Mock per Update di Telegram"""
    update = Mock(spec=Update)
    update.effective_chat = Mock(spec=Chat)
    update.effective_chat.id = 12345
    update.message = Mock(spec=Message)
    update.message.reply_text = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    """Mock per Context di Telegram"""
    context = Mock(spec=ContextTypes.DEFAULT_TYPE)
    return context


class TestStartCommand:
    """Test per comando /start"""
    
    @pytest.mark.asyncio
    async def test_sends_welcome_message(self, mock_update, mock_context):
        """Verifica invio messaggio di benvenuto"""
        mock_update.effective_user = Mock(spec=User)
        mock_update.effective_user.username = "testuser"
        
        with patch('bot.handlers.add_subscriber', return_value=True):
            await start_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        args = mock_update.message.reply_text.call_args[0]
        assert "iscritto" in args[0].lower() or "success" in args[0].lower()
    
    @pytest.mark.asyncio
    async def test_handles_missing_message(self, mock_context):
        """Verifica gestione Update senza message"""
        update = Mock(spec=Update)
        update.effective_chat = None
        update.message = None
        
        # Non dovrebbe sollevare eccezione
        await start_command(update, mock_context)
    
    @pytest.mark.asyncio
    async def test_handles_missing_chat(self, mock_context):
        """Verifica gestione Update senza chat"""
        update = Mock(spec=Update)
        update.effective_chat = None
        update.message = Mock(spec=Message)
        
        # Non dovrebbe sollevare eccezione
        await start_command(update, mock_context)


class TestHelpCommand:
    """Test per comando /help"""
    
    @pytest.mark.asyncio
    async def test_sends_help_message(self, mock_update, mock_context):
        """Verifica invio messaggio di aiuto"""
        await help_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        args = mock_update.message.reply_text.call_args[0]
        help_text = args[0]
        
        # Verifica che contenga i comandi principali
        assert "/start" in help_text or "/help" in help_text
    
    @pytest.mark.asyncio
    async def test_handles_missing_message(self, mock_context):
        """Verifica gestione Update senza message"""
        update = Mock(spec=Update)
        update.effective_chat = None
        update.message = None
        
        # Non dovrebbe sollevare eccezione
        await help_command(update, mock_context)


class TestSubscribeCommand:
    """Test per comando /start (che iscrive)"""
    
    @pytest.mark.asyncio
    @patch('bot.handlers.add_subscriber')
    async def test_subscribes_new_user(self, mock_add_sub, mock_update, mock_context):
        """Verifica sottoscrizione nuovo utente"""
        mock_add_sub.return_value = True
        mock_update.effective_user = Mock(spec=User)
        mock_update.effective_user.username = "testuser"
        
        await start_command(mock_update, mock_context)
        
        mock_add_sub.assert_called_once_with(12345)
        mock_update.message.reply_text.assert_called_once()
        args = mock_update.message.reply_text.call_args[0]
        assert "iscritto" in args[0].lower() or "success" in args[0].lower()
    
    @pytest.mark.asyncio
    @patch('bot.handlers.add_subscriber')
    async def test_handles_already_subscribed(self, mock_add_sub, mock_update, mock_context):
        """Verifica gestione utente già iscritto"""
        mock_add_sub.return_value = False
        mock_update.effective_user = Mock(spec=User)
        mock_update.effective_user.username = "testuser"
        
        await start_command(mock_update, mock_context)
        
        mock_add_sub.assert_called_once_with(12345)
        mock_update.message.reply_text.assert_called_once()
        args = mock_update.message.reply_text.call_args[0]
        assert "già" in args[0].lower() or "already" in args[0].lower()
    
    @pytest.mark.asyncio
    async def test_handles_missing_chat(self, mock_context):
        """Verifica gestione Update senza chat"""
        update = Mock(spec=Update)
        update.effective_chat = None
        update.message = Mock(spec=Message)
        
        # Non dovrebbe sollevare eccezione
        await start_command(update, mock_context)
    
    @pytest.mark.asyncio
    @patch('bot.handlers.add_subscriber')
    async def test_handles_exception(self, mock_add_sub, mock_update, mock_context):
        """Verifica gestione eccezioni"""
        mock_add_sub.side_effect = Exception("Database error")
        mock_update.effective_user = Mock(spec=User)
        
        # Dovrebbe sollevare eccezione (non gestita nel codice)
        with pytest.raises(Exception):
            await start_command(mock_update, mock_context)


class TestUnsubscribeCommand:
    """Test per comando /cancel (che disiscrive)"""
    
    @pytest.mark.asyncio
    @patch('bot.handlers.remove_subscriber')
    async def test_unsubscribes_user(self, mock_remove_sub, mock_update, mock_context):
        """Verifica disiscrizione utente"""
        mock_remove_sub.return_value = True
        mock_update.effective_user = Mock(spec=User)
        mock_update.effective_user.username = "testuser"
        
        await cancel_command(mock_update, mock_context)
        
        mock_remove_sub.assert_called_once_with(12345)
        mock_update.message.reply_text.assert_called_once()
        args = mock_update.message.reply_text.call_args[0]
        assert "disiscritto" in args[0].lower() or "unsubscri" in args[0].lower()
    
    @pytest.mark.asyncio
    @patch('bot.handlers.remove_subscriber')
    async def test_handles_not_subscribed(self, mock_remove_sub, mock_update, mock_context):
        """Verifica gestione utente non iscritto"""
        mock_remove_sub.return_value = False
        mock_update.effective_user = Mock(spec=User)
        mock_update.effective_user.username = "testuser"
        
        await cancel_command(mock_update, mock_context)
        
        mock_remove_sub.assert_called_once_with(12345)
        mock_update.message.reply_text.assert_called_once()
        args = mock_update.message.reply_text.call_args[0]
        assert "non" in args[0].lower() or "not" in args[0].lower()
    
    @pytest.mark.asyncio
    async def test_handles_missing_chat(self, mock_context):
        """Verifica gestione Update senza chat"""
        update = Mock(spec=Update)
        update.effective_chat = None
        update.message = Mock(spec=Message)
        
        # Non dovrebbe sollevare eccezione
        await cancel_command(update, mock_context)
    
    @pytest.mark.asyncio
    @patch('bot.handlers.remove_subscriber')
    async def test_handles_exception(self, mock_remove_sub, mock_update, mock_context):
        """Verifica gestione eccezioni"""
        mock_remove_sub.side_effect = Exception("Database error")
        mock_update.effective_user = Mock(spec=User)
        
        # Dovrebbe sollevare eccezione (non gestita nel codice)
        with pytest.raises(Exception):
            await cancel_command(mock_update, mock_context)


class TestEdgeCases:
    """Test per casi limite"""
    
    @pytest.mark.asyncio
    async def test_all_commands_handle_none_update(self, mock_context):
        """Verifica che tutti i comandi gestiscano update None"""
        commands = [start_command, help_command, cancel_command]
        
        for command in commands:
            # Non dovrebbe sollevare eccezione
            with patch('bot.handlers.add_subscriber'), patch('bot.handlers.remove_subscriber'):
                update = Mock(spec=Update)
                update.effective_chat = None
                update.message = None
                await command(update, mock_context)
    
    @pytest.mark.asyncio
    async def test_commands_with_different_chat_types(self, mock_context):
        """Verifica comandi con diversi tipi di chat"""
        chat_types = ['private', 'group', 'supergroup', 'channel']
        
        for chat_type in chat_types:
            update = Mock(spec=Update)
            update.effective_chat = Mock(spec=Chat)
            update.effective_chat.id = 99999
            update.effective_chat.type = chat_type
            update.message = Mock(spec=Message)
            update.message.reply_text = AsyncMock()
            
            # Tutti i comandi dovrebbero funzionare
            await start_command(update, mock_context)
            assert update.message.reply_text.called
