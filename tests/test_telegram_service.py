"""
Test suite per services.telegram_service
"""

from unittest.mock import AsyncMock, MagicMock, Mock, mock_open, patch

import pytest

from services.telegram_service import TelegramService


@pytest.fixture
def telegram_service():
    """Crea un'istanza di TelegramService per i test"""
    return TelegramService()


@pytest.fixture
def mock_response():
    """Mock per response di httpx"""
    response = Mock()
    response.status_code = 200
    response.text = "OK"
    response.raise_for_status = Mock()
    return response


class TestTelegramServiceInit:
    """Test per inizializzazione TelegramService"""

    def test_initializes_without_arguments(self):
        """Verifica inizializzazione senza argomenti"""
        service = TelegramService()
        assert isinstance(service, TelegramService)
        assert "api.telegram.org" in service.BASE_URL


@pytest.mark.asyncio
class TestSendMessage:
    """Test per send_message"""

    @patch("services.telegram_service.httpx.AsyncClient")
    async def test_sends_message_successfully(
        self, mock_client_cls, telegram_service, mock_response
    ):
        """Verifica invio messaggio con successo"""
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_cls.return_value = mock_client

        result = await telegram_service.send_message("123456", "Hello!")

        assert result is True
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[1]["json"]["chat_id"] == "123456"
        assert call_args[1]["json"]["text"] == "Hello!"

    @patch("services.telegram_service.httpx.AsyncClient")
    async def test_returns_false_on_error(self, mock_client_cls, telegram_service):
        """Verifica ritorno False su errore"""
        mock_client = AsyncMock()
        error_response = Mock()
        error_response.status_code = 400
        error_response.raise_for_status.side_effect = Exception("HTTP Error")
        mock_client.post.return_value = error_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_cls.return_value = mock_client

        result = await telegram_service.send_message("123", "Test")

        assert result is False

    @patch("services.telegram_service.httpx.AsyncClient")
    async def test_handles_network_exception(self, mock_client_cls, telegram_service):
        """Verifica gestione eccezione di rete"""
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("Network error")
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_cls.return_value = mock_client

        result = await telegram_service.send_message("123", "Test")

        assert result is False

    @patch("services.telegram_service.httpx.AsyncClient")
    async def test_sends_with_correct_url(
        self, mock_client_cls, telegram_service, mock_response
    ):
        """Verifica URL corretto per l'invio"""
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_cls.return_value = mock_client

        await telegram_service.send_message("123", "Test")

        call_url = mock_client.post.call_args[0][0]
        assert "sendMessage" in call_url


@pytest.mark.asyncio
class TestSendMediaGroup:
    """Test per send_media_group"""

    async def test_returns_false_for_empty_list(self, telegram_service):
        """Verifica ritorno False per lista vuota"""
        result = await telegram_service.send_media_group("123", [])

        assert result is False

    @patch("services.telegram_service.httpx.AsyncClient")
    @patch("builtins.open", new_callable=mock_open, read_data=b"fake_image_data")
    async def test_sends_single_image(
        self, mock_file, mock_client_cls, telegram_service, mock_response
    ):
        """Verifica invio singola immagine"""
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_cls.return_value = mock_client

        result = await telegram_service.send_media_group("123", ["image1.jpg"])

        assert result is True
        mock_client.post.assert_called_once()

    @patch("services.telegram_service.httpx.AsyncClient")
    @patch("builtins.open", new_callable=mock_open, read_data=b"fake_image_data")
    @patch("asyncio.sleep", new_callable=AsyncMock)
    async def test_splits_into_batches(
        self, mock_sleep, mock_file, mock_client_cls, telegram_service, mock_response
    ):
        """Verifica divisione in batch per limite Telegram"""
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_cls.return_value = mock_client

        # 15 immagini = 2 batch (10 + 5)
        images = [f"image{i}.jpg" for i in range(15)]

        result = await telegram_service.send_media_group("123", images)

        assert result is True
        assert mock_client.post.call_count == 2  # Due batch

    @patch("services.telegram_service.httpx.AsyncClient")
    @patch("builtins.open", new_callable=mock_open, read_data=b"fake_image_data")
    async def test_returns_false_on_batch_failure(
        self, mock_file, mock_client_cls, telegram_service
    ):
        """Verifica ritorno False se un batch fallisce"""
        mock_client = AsyncMock()
        error_response = Mock()
        error_response.status_code = 400
        error_response.text = "Bad Request"
        mock_client.post.return_value = error_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_cls.return_value = mock_client

        result = await telegram_service.send_media_group("123", ["image.jpg"])

        assert result is False

    @patch("services.telegram_service.httpx.AsyncClient")
    @patch("builtins.open", side_effect=FileNotFoundError)
    async def test_handles_missing_file(
        self, mock_file, mock_client_cls, telegram_service
    ):
        """Verifica gestione file mancante"""
        result = await telegram_service.send_media_group("123", ["missing.jpg"])

        assert result is False

    @patch("services.telegram_service.httpx.AsyncClient")
    @patch("builtins.open", new_callable=mock_open, read_data=b"test_data")
    async def test_sends_exactly_ten_images_in_batch(
        self, mock_file, mock_client_cls, telegram_service, mock_response
    ):
        """Verifica che un batch contenga massimo 10 immagini"""
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_cls.return_value = mock_client

        images = [f"image{i}.jpg" for i in range(10)]

        await telegram_service.send_media_group("123", images)

        # Verifica che sia stato fatto un solo batch
        assert mock_client.post.call_count == 1


@pytest.mark.asyncio
class TestSendBatch:
    """Test per _send_batch (metodo interno)"""

    @patch("services.telegram_service.httpx.AsyncClient")
    @patch("builtins.open", new_callable=mock_open, read_data=b"test_data")
    async def test_closes_files_after_send(
        self, mock_file, mock_client_cls, telegram_service, mock_response
    ):
        """Verifica che i file vengano chiusi dopo l'invio"""
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_cls.return_value = mock_client

        mock_file_instance = mock_file.return_value

        result = await telegram_service._send_batch("123", ["img1.jpg", "img2.jpg"])

        # Verifica che close() sia stato chiamato
        assert mock_file_instance.close.called
        assert result["success"] is True

    @patch("services.telegram_service.httpx.AsyncClient")
    @patch("builtins.open", new_callable=mock_open, read_data=b"test_data")
    async def test_closes_files_on_exception(
        self, mock_file, mock_client_cls, telegram_service
    ):
        """Verifica chiusura file anche in caso di eccezione"""
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("Send failed")
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_cls.return_value = mock_client

        mock_file_instance = mock_file.return_value

        result = await telegram_service._send_batch("123", ["img.jpg"])

        # File deve essere chiuso anche in caso di errore
        assert mock_file_instance.close.called
        assert result["success"] is False

    @patch("services.telegram_service.httpx.AsyncClient")
    @patch("builtins.open", new_callable=mock_open, read_data=b"test_data")
    async def test_constructs_media_group_correctly(
        self, mock_file, mock_client_cls, telegram_service, mock_response
    ):
        """Verifica costruzione corretta del media group"""
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_cls.return_value = mock_client

        result = await telegram_service._send_batch("123", ["img1.jpg", "img2.jpg"])

        # Verifica la chiamata a httpx.post
        call_data = mock_client.post.call_args[1]["data"]
        assert "chat_id" in call_data
        assert "media" in call_data
        assert result["success"] is True

    @patch("services.telegram_service.httpx.AsyncClient")
    @patch("builtins.open", new_callable=mock_open, read_data=b"test_data")
    async def test_handles_rate_limit_429(
        self, mock_file, mock_client_cls, telegram_service
    ):
        """Verifica gestione rate limiting (status 429)"""
        mock_client = AsyncMock()
        response = Mock()
        response.status_code = 429
        response.json.return_value = {"parameters": {"retry_after": 10}}
        mock_client.post.return_value = response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_cls.return_value = mock_client

        result = await telegram_service._send_batch("123", ["img.jpg"])

        assert result["success"] is False
        assert result["rate_limited"] is True
        assert result["retry_after"] == 10

    @patch("services.telegram_service.httpx.AsyncClient")
    @patch("builtins.open", new_callable=mock_open, read_data=b"test_data")
    async def test_handles_rate_limit_without_retry_after(
        self, mock_file, mock_client_cls, telegram_service
    ):
        """Verifica gestione rate limiting senza retry_after nella risposta"""
        mock_client = AsyncMock()
        response = Mock()
        response.status_code = 429
        response.json.side_effect = Exception("Invalid JSON")
        mock_client.post.return_value = response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_cls.return_value = mock_client

        result = await telegram_service._send_batch("123", ["img.jpg"])

        assert result["success"] is False
        assert result["rate_limited"] is True
        assert "retry_after" in result
