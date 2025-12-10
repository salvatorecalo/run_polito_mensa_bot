"""
Test suite per services.instagram_service
"""

from unittest.mock import MagicMock, Mock, patch

import pytest
from instagrapi.exceptions import (
    ChallengeRequired,
    PleaseWaitFewMinutes,
    TwoFactorRequired,
)

# from services.instagram_service import InstagramService


@pytest.fixture
def mock_client_class():
    """Mock per la classe instagrapi.Client"""
    with patch("services.instagram_service.Client") as MockClient:
        yield MockClient


@pytest.fixture
def mock_client_instance(mock_client_class):
    """Mock per l'istanza di instagrapi.Client restituita da Client()"""
    return mock_client_class.return_value


# @pytest.fixture
# def instagram_service(mock_client_class):
#     """Crea un'istanza di InstagramService con client mockato"""
#     # La patch è attiva qui grazie alla fixture mock_client_class
#     return InstagramService()


class TestInstagramServiceInit:
    """Test per inizializzazione InstagramService"""

    def test_initializes_with_client(self, instagram_service, mock_client_instance):
        """Verifica che il client venga inizializzato"""
        assert instagram_service.client == mock_client_instance
        assert instagram_service.client is not None


class TestLogin:
    """Test per login"""

    @patch("services.instagram_service.Path")
    def test_login_success_with_session(
        self, mock_path, instagram_service, mock_client_instance
    ):
        """Verifica login con sessione valida"""
        mock_path.return_value.exists.return_value = True
        mock_client_instance.load_settings.return_value = True
        # Mock _is_session_valid to return True (via get_timeline_feed success)
        mock_client_instance.get_timeline_feed.return_value = []

        result = instagram_service.login()

        assert result == mock_client_instance
        mock_client_instance.load_settings.assert_called_once()
        # Se la sessione è valida, non deve chiamare login()
        mock_client_instance.login.assert_not_called()

    @patch("services.instagram_service.Path")
    @patch("services.instagram_service.os.makedirs")
    def test_login_success_without_session(
        self, mock_makedirs, mock_path, instagram_service, mock_client_instance
    ):
        """Verifica login senza sessione (o sessione invalida)"""
        mock_path.return_value.exists.return_value = False

        result = instagram_service.login()

        assert result == mock_client_instance
        mock_client_instance.login.assert_called_once()
        mock_client_instance.dump_settings.assert_called_once()

    @patch("services.instagram_service.Path")
    def test_login_raises_two_factor_required(
        self, mock_path, instagram_service, mock_client_instance
    ):
        """Verifica gestione 2FA"""
        mock_path.return_value.exists.return_value = False
        mock_client_instance.login.side_effect = TwoFactorRequired(
            response=Mock(), message="2FA"
        )

        with pytest.raises(TwoFactorRequired):
            instagram_service.login()

    @patch("services.instagram_service.Path")
    def test_login_raises_challenge_required(
        self, mock_path, instagram_service, mock_client_instance
    ):
        """Verifica gestione Challenge"""
        mock_path.return_value.exists.return_value = False
        mock_client_instance.login.side_effect = ChallengeRequired(
            response=Mock(), message="Challenge"
        )

        with pytest.raises(ChallengeRequired):
            instagram_service.login()

    @patch("services.instagram_service.Path")
    @patch("services.instagram_service.os.makedirs")
    def test_login_handles_corrupted_session(
        self, mock_makedirs, mock_path, instagram_service, mock_client_instance
    ):
        """Verifica gestione sessione corrotta"""
        mock_path.return_value.exists.return_value = True
        mock_client_instance.load_settings.side_effect = Exception("Corrupted")

        result = instagram_service.login()

        # Deve procedere con login normale
        assert result == mock_client_instance
        mock_client_instance.login.assert_called_once()

    @patch("services.instagram_service.Path")
    @patch("services.instagram_service.os.makedirs")
    def test_login_saves_session_file(
        self, mock_makedirs, mock_path, instagram_service, mock_client_instance
    ):
        """Verifica salvataggio sessione"""
        mock_path.return_value.exists.return_value = False

        instagram_service.login()

        mock_client_instance.dump_settings.assert_called_once()


class TestGetUserStories:
    """Test per get_user_stories"""

    def test_raises_error_for_none_username(self, instagram_service):
        """Verifica errore per username None"""
        with pytest.raises(ValueError, match="Username non può essere vuoto"):
            instagram_service.get_user_stories(None)

    def test_raises_error_for_empty_username(self, instagram_service):
        """Verifica errore per username vuoto"""
        with pytest.raises(ValueError, match="Username non può essere vuoto"):
            instagram_service.get_user_stories("")

    def test_gets_stories_successfully(self, instagram_service, mock_client_instance):
        """Verifica recupero storie con successo"""
        # Setup mock per login implicito (sessione valida)
        mock_client_instance.get_timeline_feed.return_value = []

        mock_stories = [Mock(pk=1), Mock(pk=2), Mock(pk=3)]
        mock_client_instance.user_stories.return_value = mock_stories
        mock_client_instance.user_id_from_username.return_value = "12345"

        stories = instagram_service.get_user_stories("testuser")

        assert len(stories) == 3
        mock_client_instance.user_id_from_username.assert_called_with("testuser")
        mock_client_instance.user_stories.assert_called_once()

    def test_handles_user_not_found(self, instagram_service, mock_client_instance):
        """Verifica gestione utente non trovato"""
        # Setup mock per login implicito
        mock_client_instance.get_timeline_feed.return_value = []

        mock_client_instance.user_id_from_username.side_effect = Exception(
            "User not found"
        )

        with pytest.raises(Exception, match="User not found"):
            instagram_service.get_user_stories("nonexistent")

    def test_handles_no_stories(self, instagram_service, mock_client_instance):
        """Verifica gestione nessuna storia"""
        # Setup mock per login implicito
        mock_client_instance.get_timeline_feed.return_value = []

        mock_client_instance.user_stories.return_value = []
        mock_client_instance.user_id_from_username.return_value = "12345"

        stories = instagram_service.get_user_stories("testuser")

        assert stories == []

    def test_retrieves_user_info_before_stories(
        self, instagram_service, mock_client_instance
    ):
        """Verifica che venga recuperato ID utente prima delle storie"""
        # Setup mock per login implicito
        mock_client_instance.get_timeline_feed.return_value = []
        mock_client_instance.user_id_from_username.return_value = "12345"

        instagram_service.get_user_stories("testuser")

        assert mock_client_instance.user_id_from_username.called
