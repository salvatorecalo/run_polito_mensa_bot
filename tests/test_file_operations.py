"""
Test suite per utils.file_operations
"""
import os
import pytest
from pathlib import Path
from utils.file_operations import save_bytes_to_file, clean_directory


@pytest.fixture
def temp_dir(tmp_path):
    """Crea una directory temporanea per i test"""
    test_dir = tmp_path / "test_files"
    test_dir.mkdir()
    return test_dir


class TestSaveBytesToFile:
    """Test per la funzione save_bytes_to_file"""
    
    def test_saves_bytes_correctly(self, temp_dir):
        """Verifica che i bytes vengano salvati correttamente"""
        test_data = b"Hello, World!"
        file_path = temp_dir / "test.txt"
        
        save_bytes_to_file(test_data, str(file_path))
        
        assert file_path.exists()
        with open(file_path, "rb") as f:
            content = f.read()
        assert content == test_data
    
    def test_saves_empty_bytes(self, temp_dir):
        """Verifica salvataggio di bytes vuoti"""
        file_path = temp_dir / "empty.bin"
        
        save_bytes_to_file(b"", str(file_path))
        
        assert file_path.exists()
        assert file_path.stat().st_size == 0
    
    def test_overwrites_existing_file(self, temp_dir):
        """Verifica sovrascrittura di file esistente"""
        file_path = temp_dir / "overwrite.bin"
        
        save_bytes_to_file(b"first", str(file_path))
        save_bytes_to_file(b"second", str(file_path))
        
        with open(file_path, "rb") as f:
            content = f.read()
        assert content == b"second"
    
    def test_saves_binary_data(self, temp_dir):
        """Verifica salvataggio dati binari"""
        binary_data = bytes(range(256))
        file_path = temp_dir / "binary.bin"
        
        save_bytes_to_file(binary_data, str(file_path))
        
        with open(file_path, "rb") as f:
            content = f.read()
        assert content == binary_data
    
    def test_saves_large_file(self, temp_dir):
        """Verifica salvataggio file grande (1MB)"""
        large_data = b"x" * (1024 * 1024)  # 1MB
        file_path = temp_dir / "large.bin"
        
        save_bytes_to_file(large_data, str(file_path))
        
        assert file_path.exists()
        assert file_path.stat().st_size == len(large_data)
    
    def test_creates_file_in_subdirectory(self, temp_dir):
        """Verifica creazione file in sottodirectory esistente"""
        subdir = temp_dir / "subdir"
        subdir.mkdir()
        file_path = subdir / "file.bin"
        
        save_bytes_to_file(b"test", str(file_path))
        
        assert file_path.exists()


class TestCleanDirectory:
    """Test per la funzione clean_directory"""
    
    def test_removes_all_files(self, temp_dir):
        """Verifica rimozione di tutti i file"""
        for i in range(5):
            (temp_dir / f"file{i}.txt").write_text(f"content{i}")
        
        count = clean_directory(str(temp_dir))
        
        assert count == 5
        assert len(list(temp_dir.iterdir())) == 0
    
    def test_returns_zero_for_nonexistent_directory(self):
        """Verifica comportamento con directory inesistente"""
        count = clean_directory("/nonexistent/path/12345")
        
        assert count == 0
    
    def test_returns_zero_for_empty_directory(self, temp_dir):
        """Verifica comportamento con directory vuota"""
        count = clean_directory(str(temp_dir))
        
        assert count == 0
    
    def test_filters_by_single_extension(self, temp_dir):
        """Verifica filtro per singola estensione"""
        (temp_dir / "image1.jpg").write_text("jpg1")
        (temp_dir / "image2.jpg").write_text("jpg2")
        (temp_dir / "doc.txt").write_text("text")
        (temp_dir / "data.json").write_text("json")
        
        count = clean_directory(str(temp_dir), extensions=['.jpg'])
        
        assert count == 2
        assert (temp_dir / "doc.txt").exists()
        assert (temp_dir / "data.json").exists()
        assert not (temp_dir / "image1.jpg").exists()
        assert not (temp_dir / "image2.jpg").exists()
    
    def test_filters_multiple_extensions(self, temp_dir):
        """Verifica filtro con multiple estensioni"""
        (temp_dir / "file1.jpg").write_text("jpg")
        (temp_dir / "file2.png").write_text("png")
        (temp_dir / "file3.txt").write_text("txt")
        (temp_dir / "file4.gif").write_text("gif")
        
        count = clean_directory(str(temp_dir), extensions=['.jpg', '.png'])
        
        assert count == 2
        assert (temp_dir / "file3.txt").exists()
        assert (temp_dir / "file4.gif").exists()
    
    def test_does_not_remove_subdirectories(self, temp_dir):
        """Verifica che le subdirectory non vengano rimosse"""
        (temp_dir / "file.txt").write_text("content")
        subdir = temp_dir / "subdir"
        subdir.mkdir()
        (subdir / "nested.txt").write_text("nested")
        
        count = clean_directory(str(temp_dir))
        
        assert count == 1
        assert subdir.exists()
        assert (subdir / "nested.txt").exists()
    
    def test_with_hidden_files(self, temp_dir):
        """Verifica rimozione file nascosti"""
        (temp_dir / ".hidden").write_text("hidden")
        (temp_dir / ".gitignore").write_text("git")
        (temp_dir / "visible.txt").write_text("visible")
        
        count = clean_directory(str(temp_dir))
        
        assert count == 3
        assert len(list(temp_dir.iterdir())) == 0
    
    def test_with_empty_extension_filter(self, temp_dir):
        """Verifica comportamento con lista estensioni vuota"""
        (temp_dir / "file1.txt").write_text("text")
        (temp_dir / "file2.jpg").write_text("image")
        
        count = clean_directory(str(temp_dir), extensions=[])
        
        # Con lista vuota, la condizione `if extensions` è False, quindi rimuove tutto
        # Questo è il comportamento attuale dell'implementazione
        assert count == 2
        assert len(list(temp_dir.iterdir())) == 0
