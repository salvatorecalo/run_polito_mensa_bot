"""
Utilities per elaborazione immagini
"""
import os
from PIL import Image, ImageDraw, ImageFont
from typing import Tuple, Optional
from config.constants import (
    IMAGE_WIDTH, IMAGE_HEIGHT, MIN_FONT_SIZE, 
    MAX_FONT_SIZE, BG_COLOR, TEXT_COLOR, IMAGE_MARGIN
)
try:
    import cairosvg
    SVG_SUPPORT = True
except ImportError:
    SVG_SUPPORT = False


def add_watermark(
    image: Image.Image,
    watermark_text: Optional[str] = None,
    watermark_image_path: Optional[str] = None,
    position: str = "bottom-right",
    font_size: int = 24,
    opacity: int = 180,
    logo_size: Tuple[int, int] = (120, 120)
) -> Image.Image:
    """
    Aggiunge un watermark/logo all'immagine (può essere testo o immagine).
    
    Args:
        image: Immagine PIL su cui aggiungere il watermark
        watermark_text: Testo del watermark (usato se watermark_image_path è None)
        watermark_image_path: Percorso dell'immagine logo (ha priorità su watermark_text)
        position: Posizione ("top-left", "top-right", "bottom-left", "bottom-right")
        font_size: Dimensione del font del watermark testuale
        opacity: Opacità del watermark (0-255)
        logo_size: Dimensione massima del logo immagine (width, height)
    
    Returns:
        Immagine con watermark aggiunto
    """
    # Converti l'immagine principale in RGBA
    if image.mode != 'RGBA':
        image = image.convert('RGBA')
    
    # Crea layer trasparente per il watermark
    watermark_layer = Image.new('RGBA', image.size, (0, 0, 0, 0))
    
    padding = 20
    
    # Se c'è un'immagine logo, usala
    if watermark_image_path and os.path.exists(watermark_image_path):
        try:
            logo = None
            
            # Gestisci file SVG
            if watermark_image_path.lower().endswith('.svg'):
                if SVG_SUPPORT:
                    # Converti SVG in PNG in memoria
                    import io
                    png_data = cairosvg.svg2png(url=watermark_image_path)
                    if png_data:
                        logo = Image.open(io.BytesIO(png_data))
                    else:
                        raise Exception("Failed to convert SVG to PNG")
                else:
                    raise Exception("SVG support not available (cairosvg not installed)")
            else:
                # Carica immagine normale (PNG, JPEG, etc.)
                logo = Image.open(watermark_image_path)
            
            # Converti in RGBA se necessario
            if logo.mode != 'RGBA':
                logo = logo.convert('RGBA')
            
            # Ridimensiona il logo mantenendo l'aspect ratio
            logo.thumbnail(logo_size, Image.Resampling.LANCZOS)
            
            # Applica opacità al logo
            alpha = logo.split()[3]
            alpha = alpha.point(lambda p: int(p * (opacity / 255.0)))
            logo.putalpha(alpha)
            
            logo_width, logo_height = logo.size
            
            # Calcola posizione
            if position == "bottom-right":
                x = image.width - logo_width - padding
                y = image.height - logo_height - padding
            elif position == "bottom-left":
                x = padding
                y = image.height - logo_height - padding
            elif position == "top-right":
                x = image.width - logo_width - padding
                y = padding
            elif position == "top-left":
                x = padding
                y = padding
            else:
                # Default: bottom-right
                x = image.width - logo_width - padding
                y = image.height - logo_height - padding
            
            # Incolla il logo sul layer
            watermark_layer.paste(logo, (x, y), logo)
            
        except Exception as e:
            # Se fallisce il caricamento del logo, fallback su testo
            print(f"Errore caricamento logo: {e}, uso testo fallback")
            watermark_text = watermark_text or "LOGO"
    
    # Se non c'è immagine o è fallita, usa il testo
    if watermark_text and not (watermark_image_path and os.path.exists(watermark_image_path)):
        draw = ImageDraw.Draw(watermark_layer)
        
        # Carica font per il watermark
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
        except:
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", font_size)
            except:
                try:
                    font = ImageFont.truetype("arialbd.ttf", font_size)
                except:
                    font = ImageFont.load_default()
        
        # Calcola dimensioni del testo
        bbox = draw.textbbox((0, 0), watermark_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Calcola posizione
        if position == "bottom-right":
            x = image.width - text_width - padding
            y = image.height - text_height - padding
        elif position == "bottom-left":
            x = padding
            y = image.height - text_height - padding
        elif position == "top-right":
            x = image.width - text_width - padding
            y = padding
        elif position == "top-left":
            x = padding
            y = padding
        else:
            # Default: bottom-right
            x = image.width - text_width - padding
            y = image.height - text_height - padding
        
        # Disegna il testo con opacità
        draw.text((x, y), watermark_text, fill=(255, 255, 255, opacity), font=font)
    
    # Componi le immagini
    watermarked = Image.alpha_composite(image, watermark_layer)
    
    return watermarked


def create_long_image(
    text: str, 
    output_path: str, 
    width: int = IMAGE_WIDTH,
    height: int = IMAGE_HEIGHT,
    min_font: int = MIN_FONT_SIZE,
    max_font: int = MAX_FONT_SIZE,
    bg_color: Tuple[int, int, int] = BG_COLOR,
    text_color: Tuple[int, int, int] = TEXT_COLOR,
    margin: int = IMAGE_MARGIN,
    add_logo: bool = True,
    logo_text: Optional[str] = None,
    logo_image_path: Optional[str] = None,
    logo_position: str = "bottom-right"
) -> str:
    """
    Crea un'immagine verticale con testo centrato, adattando automaticamente
    la dimensione del font per far entrare tutto il contenuto con margini adeguati.
    
    Args:
        text: Testo da visualizzare
        output_path: Percorso del file di output
        width: Larghezza immagine (default: 1080)
        height: Altezza immagine (default: 1920)
        min_font: Dimensione minima font
        max_font: Dimensione massima font
        bg_color: Colore sfondo RGB
        text_color: Colore testo RGB
        margin: Margine dai bordi in pixel
        add_logo: Se True, aggiunge il watermark/logo
        logo_text: Testo del logo (usato se logo_image_path è None)
        logo_image_path: Percorso dell'immagine logo (ha priorità su logo_text)
        logo_position: Posizione del logo ("top-left", "top-right", "bottom-left", "bottom-right")
    
    Returns:
        Percorso del file salvato
    """
    text = text.strip().upper()
    
    # Crea immagine
    image = Image.new("RGB", (width, height), color=bg_color)
    draw = ImageDraw.Draw(image)
    
    # Area disponibile per il testo (con margini + spazio per logo)
    logo_space = 60 if add_logo else 0
    available_width = width - (margin * 2)
    available_height = height - (margin * 2) - logo_space
    
    # Trova la dimensione font ottimale
    current_font_size = max_font
    font = None
    
    while current_font_size >= min_font:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", current_font_size)
        except:
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", current_font_size)
            except:
                try:
                    font = ImageFont.truetype("arialbd.ttf", current_font_size)
                except:
                    font = ImageFont.load_default()
                    break
        
        # Calcola dimensioni del testo con questo font
        bbox = draw.multiline_textbbox((0, 0), text, font=font, align="center")
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Verifica se il testo entra nell'area disponibile
        if text_width <= available_width and text_height <= available_height:
            break
        
        # Riduci font size
        current_font_size -= 2
    
    # Calcola dimensioni finali del testo
    bbox = draw.multiline_textbbox((0, 0), text, font=font, align="center")
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Centra il testo nell'immagine
    x = (width - text_width) // 2
    y = (height - text_height) // 2
    
    draw.multiline_text((x, y), text, fill=text_color, font=font, align="center")
    
    # Aggiungi watermark/logo se richiesto
    if add_logo:
        # Se non è specificato né logo_image_path né logo_text, usa default
        if not logo_image_path and not logo_text:
            logo_text = "RUN POLITO MENSA"
        
        image = add_watermark(
            image, 
            watermark_text=logo_text, 
            watermark_image_path=logo_image_path,
            position=logo_position
        )
    
    # Converti in RGB se necessario (per salvare come JPEG)
    if image.mode == 'RGBA':
        rgb_image = Image.new('RGB', image.size, bg_color)
        rgb_image.paste(image, mask=image.split()[3])  # Usa il canale alpha come maschera
        image = rgb_image
    
    # Salva immagine
    image.save(output_path, "JPEG", quality=95)
    return output_path