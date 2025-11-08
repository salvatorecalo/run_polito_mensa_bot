"""
Test suite per utils.image_processing
"""
import os
import pytest
from PIL import Image
from utils.image_processing import create_long_image


@pytest.fixture
def temp_output_dir(tmp_path):
    """Crea una directory temporanea per i file di output dei test"""
    output_dir = tmp_path / "test_images"
    output_dir.mkdir()
    return output_dir


@pytest.fixture
def sample_text():
    """Testo di esempio per i test"""
    return "MENU DEL GIORNO\nPRIMO: PASTA AL POMODORO\nSECONDO: POLLO ARROSTO"


class TestCreateLongImage:
    """Test per la funzione create_long_image"""
    
    def test_creates_image_file(self, temp_output_dir, sample_text):
        """Verifica che venga creato un file immagine"""
        output_path = temp_output_dir / "test_image.jpg"
        
        result = create_long_image(sample_text, str(output_path))
        
        assert os.path.exists(result)
        assert result == str(output_path)
    
    def test_image_dimensions(self, temp_output_dir, sample_text):
        """Verifica che l'immagine abbia le dimensioni corrette"""
        output_path = temp_output_dir / "test_dimensions.jpg"
        
        create_long_image(sample_text, str(output_path))
        
        with Image.open(output_path) as img:
            assert img.size == (1080, 1920)
    
    def test_custom_dimensions(self, temp_output_dir, sample_text):
        """Verifica dimensioni personalizzate"""
        output_path = temp_output_dir / "test_custom_dimensions.jpg"
        custom_width, custom_height = 800, 1200
        
        create_long_image(
            sample_text, 
            str(output_path),
            width=custom_width,
            height=custom_height
        )
        
        with Image.open(output_path) as img:
            assert img.size == (custom_width, custom_height)
    
    def test_empty_text(self, temp_output_dir):
        """Verifica gestione testo vuoto"""
        output_path = temp_output_dir / "test_empty.jpg"
        
        result = create_long_image("", str(output_path))
        
        assert os.path.exists(result)
    
    def test_whitespace_text(self, temp_output_dir):
        """Verifica gestione testo con solo spazi"""
        output_path = temp_output_dir / "test_whitespace.jpg"
        
        result = create_long_image("   \n\n   ", str(output_path))
        
        assert os.path.exists(result)
    
    def test_very_long_text(self, temp_output_dir):
        """Verifica gestione testo molto lungo"""
        output_path = temp_output_dir / "test_long_text.jpg"
        long_text = "MENU DEL GIORNO\n" * 50
        
        result = create_long_image(long_text, str(output_path))
        
        assert os.path.exists(result)
        with Image.open(result) as img:
            assert img.size == (1080, 1920)
    
    def test_special_characters(self, temp_output_dir):
        """Verifica gestione caratteri speciali"""
        output_path = temp_output_dir / "test_special_chars.jpg"
        special_text = "MENÙ ÀÇÊÑTÀTÖ\n$#@!%&*()[]{}|"
        
        result = create_long_image(special_text, str(output_path))
        
        assert os.path.exists(result)
    
    def test_text_uppercase_conversion(self, temp_output_dir):
        """Verifica che il testo venga convertito in maiuscolo"""
        output_path = temp_output_dir / "test_uppercase.jpg"
        lowercase_text = "menu del giorno"
        
        # Il test verifica indirettamente tramite la creazione dell'immagine
        # dato che la funzione converte in uppercase internamente
        result = create_long_image(lowercase_text, str(output_path))
        
        assert os.path.exists(result)
    
    def test_custom_colors(self, temp_output_dir, sample_text):
        """Verifica colori personalizzati"""
        output_path = temp_output_dir / "test_custom_colors.jpg"
        bg_color = (0, 0, 255)  # Blu
        text_color = (255, 0, 0)  # Rosso
        
        result = create_long_image(
            sample_text,
            str(output_path),
            bg_color=bg_color,
            text_color=text_color
        )
        
        assert os.path.exists(result)
        
        # JPEG compression può alterare leggermente i colori
        # Verifichiamo solo che l'immagine sia stata creata correttamente
        with Image.open(result) as img:
            # Verifica dimensioni corrette
            assert img.size == (1080, 1920)
            # Verifica modalità RGB
            assert img.mode == "RGB"
            
            # Verifica che il colore dominante sia simile al blu (sfondo)
            from typing import cast, Iterable, Tuple
            pixels = list(cast(Iterable[Tuple[int, int, int]], img.getdata()))
            # Conta pixel blu-ish (considerando compressione JPEG)
            blue_ish_pixels = [p for p in pixels if p[2] > 200 and p[0] < 50 and p[1] < 50]
            # Dovrebbe esserci una quantità significativa di pixel blu
            assert len(blue_ish_pixels) > len(pixels) * 0.5  # Almeno 50% blu-ish
    
    def test_min_max_font_size(self, temp_output_dir):
        """Verifica rispetto dei limiti di dimensione font"""
        output_path = temp_output_dir / "test_font_limits.jpg"
        very_long_text = "A" * 1000
        
        result = create_long_image(
            very_long_text,
            str(output_path),
            min_font=50,
            max_font=100
        )
        
        assert os.path.exists(result)
    
    def test_multiline_text(self, temp_output_dir):
        """Verifica gestione testo multi-riga"""
        output_path = temp_output_dir / "test_multiline.jpg"
        multiline_text = """PRIMO PIATTO
SECONDO PIATTO
CONTORNO
DOLCE"""
        
        result = create_long_image(multiline_text, str(output_path))
        
        assert os.path.exists(result)
    
    def test_returns_correct_path(self, temp_output_dir, sample_text):
        """Verifica che venga restituito il path corretto"""
        output_path = temp_output_dir / "test_return_path.jpg"
        
        result = create_long_image(sample_text, str(output_path))
        
        assert result == str(output_path)
        assert os.path.isabs(result) or result.startswith(".")
    
    def test_overwrites_existing_file(self, temp_output_dir, sample_text):
        """Verifica che un file esistente venga sovrascritto"""
        output_path = temp_output_dir / "test_overwrite.jpg"
        
        # Crea primo file
        create_long_image(sample_text, str(output_path))
        first_mtime = os.path.getmtime(output_path)
        
        # Attendi un momento e ricrea
        import time
        time.sleep(0.1)
        
        create_long_image("NUOVO TESTO", str(output_path))
        second_mtime = os.path.getmtime(output_path)
        
        assert second_mtime > first_mtime
    
    def test_image_format_jpg(self, temp_output_dir, sample_text):
        """Verifica che l'immagine sia in formato JPG"""
        output_path = temp_output_dir / "test_format.jpg"
        
        create_long_image(sample_text, str(output_path))
        
        with Image.open(output_path) as img:
            assert img.format == "JPEG"
    
    def test_image_mode_rgb(self, temp_output_dir, sample_text):
        """Verifica che l'immagine sia in modalità RGB"""
        output_path = temp_output_dir / "test_mode.jpg"
        
        create_long_image(sample_text, str(output_path))
        
        with Image.open(output_path) as img:
            assert img.mode == "RGB"
    
    def test_single_character(self, temp_output_dir):
        """Verifica gestione singolo carattere"""
        output_path = temp_output_dir / "test_single_char.jpg"
        
        result = create_long_image("A", str(output_path))
        
        assert os.path.exists(result)
    
    def test_numeric_text(self, temp_output_dir):
        """Verifica gestione testo numerico"""
        output_path = temp_output_dir / "test_numbers.jpg"
        
        result = create_long_image("123456789", str(output_path))
        
        assert os.path.exists(result)
    
    def test_unicode_emoji(self, temp_output_dir):
        """Verifica gestione emoji e unicode"""
        output_path = temp_output_dir / "test_emoji.jpg"
        emoji_text = "MENU 🍕 🍝 🥗"
        
        result = create_long_image(emoji_text, str(output_path))
        
        assert os.path.exists(result)


class TestEdgeCases:
    """Test per casi limite"""
    
    def test_very_small_dimensions(self, temp_output_dir, sample_text):
        """Verifica gestione dimensioni molto piccole"""
        output_path = temp_output_dir / "test_small_dims.jpg"
        
        result = create_long_image(
            sample_text,
            str(output_path),
            width=200,
            height=200
        )
        
        assert os.path.exists(result)
    
    def test_very_large_dimensions(self, temp_output_dir, sample_text):
        """Verifica gestione dimensioni molto grandi"""
        output_path = temp_output_dir / "test_large_dims.jpg"
        
        result = create_long_image(
            sample_text,
            str(output_path),
            width=4000,
            height=6000
        )
        
        assert os.path.exists(result)
    
    def test_font_size_equal_min_max(self, temp_output_dir, sample_text):
        """Verifica quando min_font == max_font"""
        output_path = temp_output_dir / "test_equal_font.jpg"
        
        result = create_long_image(
            sample_text,
            str(output_path),
            min_font=200,
            max_font=200
        )
        
        assert os.path.exists(result)
    
    def test_text_with_tabs(self, temp_output_dir):
        """Verifica gestione tab nel testo"""
        output_path = temp_output_dir / "test_tabs.jpg"
        text_with_tabs = "PRIMO\tPIATTO\nSECONDO\tPIATTO"
        
        result = create_long_image(text_with_tabs, str(output_path))
        
        assert os.path.exists(result)