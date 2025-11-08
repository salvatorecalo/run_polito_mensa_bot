"""
Test suite per data.subscribers
"""
import os
import json
import pytest
from pathlib import Path
from data.subscribers import (
    load_subscribers,
    save_subscribers,
    add_subscriber,
    remove_subscriber
)


@pytest.fixture
def temp_subscribers_file(tmp_path, monkeypatch):
    """Crea un file subscribers temporaneo per i test"""
    test_file = tmp_path / "data" / "test_subscribers.json"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Modifica temporaneamente il path del file
    monkeypatch.setattr('data.subscribers.SUBSCRIBERS_FILE', str(test_file))
    
    yield str(test_file)


class TestLoadSubscribers:
    """Test per load_subscribers"""
    
    def test_loads_existing_subscribers(self, temp_subscribers_file):
        """Verifica caricamento subscribers esistenti"""
        test_data = [123, 456, 789]
        with open(temp_subscribers_file, 'w') as f:
            json.dump(test_data, f)
        
        result = load_subscribers()
        
        assert result == test_data
    
    def test_returns_empty_list_for_nonexistent_file(self, temp_subscribers_file):
        """Verifica ritorno lista vuota se file non esiste"""
        if os.path.exists(temp_subscribers_file):
            os.remove(temp_subscribers_file)
        
        result = load_subscribers()
        
        assert result == []
    
    def test_handles_empty_file(self, temp_subscribers_file):
        """Verifica gestione file vuoto"""
        with open(temp_subscribers_file, 'w') as f:
            f.write("")
        
        result = load_subscribers()
        
        assert result == []
    
    def test_handles_corrupted_json(self, temp_subscribers_file):
        """Verifica gestione JSON corrotto"""
        with open(temp_subscribers_file, 'w') as f:
            f.write("{invalid json")
        
        result = load_subscribers()
        
        assert result == []


class TestSaveSubscribers:
    """Test per save_subscribers"""
    
    def test_saves_subscribers_correctly(self, temp_subscribers_file):
        """Verifica salvataggio corretto subscribers"""
        test_data = [111, 222, 333]
        
        save_subscribers(test_data)
        
        with open(temp_subscribers_file, 'r') as f:
            saved_data = json.load(f)
        assert saved_data == test_data
    
    def test_overwrites_existing_data(self, temp_subscribers_file):
        """Verifica sovrascrittura dati esistenti"""
        save_subscribers([100, 200])
        new_data = [300, 400, 500]
        
        save_subscribers(new_data)
        
        with open(temp_subscribers_file, 'r') as f:
            saved_data = json.load(f)
        assert saved_data == new_data
    
    def test_saves_empty_list(self, temp_subscribers_file):
        """Verifica salvataggio lista vuota"""
        save_subscribers([])
        
        with open(temp_subscribers_file, 'r') as f:
            saved_data = json.load(f)
        assert saved_data == []
    
    def test_creates_directory_if_not_exists(self, tmp_path, monkeypatch):
        """Verifica creazione directory se non esiste"""
        nested_path = tmp_path / "nested" / "dir" / "subscribers.json"
        monkeypatch.setattr('data.subscribers.SUBSCRIBERS_FILE', str(nested_path))
        
        save_subscribers([123])
        
        assert nested_path.exists()


class TestAddSubscriber:
    """Test per add_subscriber"""
    
    def test_adds_new_subscriber(self, temp_subscribers_file):
        """Verifica aggiunta nuovo iscritto"""
        result = add_subscriber(12345)
        
        assert result is True
        subscribers = load_subscribers()
        assert 12345 in subscribers
    
    def test_returns_false_for_existing_subscriber(self, temp_subscribers_file):
        """Verifica ritorno False per iscritto esistente"""
        add_subscriber(12345)
        
        result = add_subscriber(12345)
        
        assert result is False
        subscribers = load_subscribers()
        assert subscribers.count(12345) == 1
    
    def test_adds_multiple_subscribers(self, temp_subscribers_file):
        """Verifica aggiunta multipli iscritti"""
        add_subscriber(111)
        add_subscriber(222)
        add_subscriber(333)
        
        subscribers = load_subscribers()
        assert len(subscribers) == 3
        assert 111 in subscribers
        assert 222 in subscribers
        assert 333 in subscribers


class TestRemoveSubscriber:
    """Test per remove_subscriber"""
    
    def test_removes_existing_subscriber(self, temp_subscribers_file):
        """Verifica rimozione iscritto esistente"""
        add_subscriber(12345)
        
        result = remove_subscriber(12345)
        
        assert result is True
        subscribers = load_subscribers()
        assert 12345 not in subscribers
    
    def test_returns_false_for_nonexistent_subscriber(self, temp_subscribers_file):
        """Verifica ritorno False per iscritto non esistente"""
        result = remove_subscriber(99999)
        
        assert result is False
    
    def test_removes_only_specified_subscriber(self, temp_subscribers_file):
        """Verifica rimozione solo dell'iscritto specificato"""
        add_subscriber(111)
        add_subscriber(222)
        add_subscriber(333)
        
        remove_subscriber(222)
        
        subscribers = load_subscribers()
        assert len(subscribers) == 2
        assert 111 in subscribers
        assert 333 in subscribers
        assert 222 not in subscribers
    
    def test_removes_from_empty_list(self, temp_subscribers_file):
        """Verifica rimozione da lista vuota"""
        result = remove_subscriber(123)
        
        assert result is False


class TestIntegration:
    """Test di integrazione per il flusso completo"""
    
    def test_full_subscriber_lifecycle(self, temp_subscribers_file):
        """Test completo: aggiungi -> carica -> rimuovi -> carica"""
        # Aggiungi
        add_subscriber(100)
        add_subscriber(200)
        
        # Verifica
        subscribers = load_subscribers()
        assert subscribers == [100, 200]
        
        # Rimuovi uno
        remove_subscriber(100)
        
        # Verifica
        subscribers = load_subscribers()
        assert subscribers == [200]
        
        # Rimuovi l'altro
        remove_subscriber(200)
        
        # Verifica lista vuota
        subscribers = load_subscribers()
        assert subscribers == []
    
    def test_persistence_across_operations(self, temp_subscribers_file):
        """Verifica persistenza dati tra operazioni"""
        # Aggiungi alcuni subscribers
        for i in range(1, 6):
            add_subscriber(i * 100)
        
        # Rimuovi alcuni
        remove_subscriber(200)
        remove_subscriber(400)
        
        # Ricarica e verifica
        subscribers = load_subscribers()
        assert len(subscribers) == 3
        assert set(subscribers) == {100, 300, 500}
