"""
Test suite per services.instagram_service
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from instagrapi.exceptions import TwoFactorRequired, ChallengeRequired
from services.instagram_service import InstagramService


@pytest.fixture
def instagram_service():
    """Crea un'istanza di InstagramService per i test"""
    return InstagramService()


@pytest.fixture
def mock_client():
    """Mock per Client Instagram"""
    client = Mock()
    client.login = Mock()
    client.load_settings = Mock()
    client.dump_settings = Mock()
    client.user_info_by_username = Mock()
    client.user_stories = Mock()
    return client


class TestInstagramServiceInit:
    """Test per inizializzazione InstagramService"""
    
    def test_initializes_with_none_client(self, instagram_service):
        """Verifica inizializzazione con client None"""
        assert instagram_service.client is None


class TestLogin:
    """Test per metodo login"""
    
    @patch('services.instagram_service.Client')
    @patch('os.path.exists')
    def test_login_success_with_session(self, mock_exists, mock_client_class, instagram_service):
        """Verifica login con sessione esistente"""
        mock_exists.return_value = True
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        result = instagram_service.login()
        
        assert result == mock_client
        mock_client.load_settings.assert_called_once()
        mock_client.login.assert_called_once()
    
    @patch('services.instagram_service.Client')
    @patch('os.path.exists')
    def test_login_success_without_session(self, mock_exists, mock_client_class, instagram_service):
        """Verifica login senza sessione esistente"""
        mock_exists.return_value = False
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        result = instagram_service.login()
        
        assert result == mock_client
        mock_client.load_settings.assert_not_called()
        mock_client.login.assert_called_once()
    
    @patch('services.instagram_service.Client')
    @patch('os.path.exists')
    def test_login_raises_two_factor_required(self, mock_exists, mock_client_class, instagram_service):
        """Verifica eccezione TwoFactorRequired"""
        mock_exists.return_value = False
        mock_client = Mock()
        mock_client.login.side_effect = TwoFactorRequired()
        mock_client_class.return_value = mock_client
        
        with pytest.raises(TwoFactorRequired):
            instagram_service.login()
    
    @patch('services.instagram_service.Client')
    @patch('os.path.exists')
    def test_login_raises_challenge_required(self, mock_exists, mock_client_class, instagram_service):
        """Verifica eccezione ChallengeRequired"""
        mock_exists.return_value = False
        mock_client = Mock()
        mock_client.login.side_effect = ChallengeRequired()
        mock_client_class.return_value = mock_client
        
        with pytest.raises(ChallengeRequired):
            instagram_service.login()
    
    @patch('services.instagram_service.Client')
    @patch('os.path.exists')
    def test_login_handles_corrupted_session(self, mock_exists, mock_client_class, instagram_service):
        """Verifica gestione sessione corrotta"""
        mock_exists.return_value = True
        mock_client = Mock()
        mock_client.load_settings.side_effect = Exception("Corrupted")
        mock_client_class.return_value = mock_client
        
        # Dovrebbe continuare con login normale
        result = instagram_service.login()
        
        assert result == mock_client
        mock_client.login.assert_called_once()
    
    @patch('services.instagram_service.Client')
    @patch('os.path.exists')
    def test_login_saves_session_file(self, mock_exists, mock_client_class, instagram_service):
        """Verifica salvataggio file sessione dopo login"""
        mock_exists.return_value = False
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        instagram_service.login()
        
        mock_client.dump_settings.assert_called_once()


class TestGetUserStories:
    """Test per metodo get_user_stories"""
    
    def test_raises_error_if_not_authenticated(self, instagram_service):
        """Verifica errore se client non autenticato"""
        with pytest.raises(RuntimeError, match="Client non autenticato"):
            instagram_service.get_user_stories("testuser")
    
    def test_raises_error_for_none_username(self, instagram_service, mock_client):
        """Verifica errore per username None"""
        instagram_service.client = mock_client
        
        with pytest.raises(ValueError, match="Username non può essere None o vuoto"):
            instagram_service.get_user_stories(None)
        
        # Verifica che non sia stata fatta nessuna chiamata al client
        mock_client.user_info_by_username.assert_not_called()
    
    def test_raises_error_for_empty_username(self, instagram_service, mock_client):
        """Verifica errore per username vuoto"""
        instagram_service.client = mock_client
        
        with pytest.raises(ValueError, match="Username non può essere None o vuoto"):
            instagram_service.get_user_stories("")
        
        # Verifica che non sia stata fatta nessuna chiamata al client
        mock_client.user_info_by_username.assert_not_called()
    
    def test_gets_stories_successfully(self, instagram_service, mock_client):
        """Verifica recupero storie con successo"""
        instagram_service.client = mock_client
        
        mock_user = Mock()
        mock_user.pk = 12345
        mock_user.username = "testuser"
        mock_client.user_info_by_username.return_value = mock_user
        
        mock_stories = [Mock(), Mock(), Mock()]
        mock_client.user_stories.return_value = mock_stories
        
        result = instagram_service.get_user_stories("testuser")
        
        assert len(result) == 3
        mock_client.user_info_by_username.assert_called_once_with("testuser")
        mock_client.user_stories.assert_called_once_with(12345)
    
    def test_handles_user_not_found(self, instagram_service, mock_client):
        """Verifica gestione utente non trovato"""
        instagram_service.client = mock_client
        mock_client.user_info_by_username.side_effect = Exception("User not found")
        
        with pytest.raises(Exception, match="User not found"):
            instagram_service.get_user_stories("nonexistent")
    
    def test_handles_no_stories(self, instagram_service, mock_client):
        """Verifica gestione nessuna storia disponibile"""
        instagram_service.client = mock_client
        
        mock_user = Mock()
        mock_user.pk = 12345
        mock_client.user_info_by_username.return_value = mock_user
        mock_client.user_stories.return_value = []
        
        result = instagram_service.get_user_stories("testuser")
        
        assert len(result) == 0
    
    def test_retrieves_user_info_before_stories(self, instagram_service, mock_client):
        """Verifica che user_info venga recuperato prima delle storie"""
        instagram_service.client = mock_client
        
        mock_user = Mock()
        mock_user.pk = 99999
        mock_client.user_info_by_username.return_value = mock_user
        mock_client.user_stories.return_value = []
        
        instagram_service.get_user_stories("testuser")
        
        # Verifica ordine delle chiamate
        assert mock_client.user_info_by_username.called
        assert mock_client.user_stories.called
        
        # user_info deve essere chiamato prima di user_stories
        calls = [str(call) for call in mock_client.method_calls]
        info_index = next(i for i, call in enumerate(calls) if 'user_info_by_username' in call)
        stories_index = next(i for i, call in enumerate(calls) if 'user_stories' in call)
        assert info_index < stories_index
