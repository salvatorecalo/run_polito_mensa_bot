"""
Utilities per elaborazione immagini
"""
import os
from PIL import Image, ImageDraw, ImageFont
from typing import Tuple, Optional
from utils.translate_text import translate_text
from config.constants import (
    IMAGE_WIDTH, IMAGE_HEIGHT, MIN_FONT_SIZE, 
    MAX_FONT_SIZE, BG_COLOR, TEXT_COLOR, IMAGE_MARGIN
)
from database.models import Canteen, Menu
try:
    import cairosvg
    SVG_SUPPORT = True
except ImportError:
    SVG_SUPPORT = False


def add_watermark(
    image: Image.Image,
    watermark_text: Optional[str] = None,
    watermark_image_path: Optional[str] = None,
    position: str = "top-left",
    font_size: int = 24,
    opacity: int = 255,
    logo_size: Tuple[int, int] = (150, 150)
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
"""
Utilities per elaborazione immagini - Versione Allineata agli Handler
"""
import os
import re
from PIL import Image, ImageDraw, ImageFont
from typing import Tuple, Optional, List
from config.constants import (
    IMAGE_WIDTH, IMAGE_HEIGHT, BG_COLOR, TEXT_COLOR, IMAGE_MARGIN
)

# ... (tieni la tua funzione add_watermark qui sopra senza modifiche) ...

def _get_font(size: int):
    """Helper per caricare i font del sistema Polito Mensa"""
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
    except:
        try:
            return ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", size)
        except:
            return ImageFont.load_default()

async def create_long_image(
    text: str,
    output_path: str,
    logo_text: Optional[str] = "@RunMensaBot on telegram",
    add_logo: bool = True,
    logo_image_path: Optional[str] = "assets/run_logo.png"
) -> str:
    """
    Crea l'immagine del menu con layout strutturato.
    Parametri allineati alla chiamata del bot handler.
    """
    # 1. Setup Immagine e Colori (Usa le tue costanti)
    image = Image.new("RGB", (IMAGE_WIDTH, IMAGE_HEIGHT), color=BG_COLOR)
    draw = ImageDraw.Draw(image)
    
    # Font proporzionati (basati sul layout EDISU)
    font_title = _get_font(60)   # Per la prima riga (Nome Mensa)
    font_items = _get_font(30)   # Per i piatti
    font_footer = _get_font(30)  # Per le note in fondo

    # 2. Elaborazione del testo
    # Dividiamo il testo in righe. Supponiamo che la prima riga sia il nome della mensa
    lines = [line.strip().upper() for line in text.split('\n') if line.strip()]
    
    if not lines:
        return ""

    curr_y = 250 # Lasciamo spazio in alto per il logo (top-left)

    # 3. Disegno Titolo (Prima riga del testo)
    title = lines[0]
    bbox_t = draw.textbbox((0, 0), title, font=font_title)
    draw.text(((IMAGE_WIDTH - (bbox_t[2] - bbox_t[0])) // 2, curr_y), title, fill=TEXT_COLOR, font=font_title)
    
    curr_y += 150
    draw.line((200, curr_y, IMAGE_WIDTH - 200, curr_y), fill=TEXT_COLOR, width=2)
    curr_y += 80

    # 4. Disegno dei Piatti (Resto del testo)
    # Raggruppiamo il resto del testo per disegnarlo centrato
    if len(lines) > 1:
        content_text = "\n".join(lines[1:])
        # Usiamo multiline_text per gestire tutto il corpo del menu
        bbox_c = draw.multiline_textbbox((0, 0), content_text, font=font_items, align="center", spacing=15)
        draw.multiline_text(
            ((IMAGE_WIDTH - (bbox_c[2] - bbox_c[0])) // 2, curr_y), 
            content_text, 
            fill=TEXT_COLOR, 
            font=font_items, 
            align="center", 
            spacing=10
        )

    # 5. Nota a piè di pagina (Footer fisso)
    footer_note = await translate_text("Verificare la presenza di allergeni presso i locali della mensa.", dest_language="en")
    # Disegniamo la linea sopra il footer
    draw.line((IMAGE_MARGIN, IMAGE_HEIGHT - 200, IMAGE_WIDTH - IMAGE_MARGIN, IMAGE_HEIGHT - 200), fill=TEXT_COLOR, width=3)
    
    bbox_f = draw.multiline_textbbox((0, 0), footer_note, font=font_footer, align="center")
    draw.multiline_text(
        ((IMAGE_WIDTH - (bbox_f[2] - bbox_f[0])) // 2, IMAGE_HEIGHT - 160), 
        footer_note, 
        fill=TEXT_COLOR, 
        font=font_footer, 
        align="center"
    )

    # 6. Aggiunta Logo/Watermark (Usa la tua funzione add_watermark)
    if add_logo:
        # Passiamo i parametri logo_image_path e logo_text alla tua funzione originale
        image = add_watermark(
            image, 
            watermark_text=logo_text, 
            watermark_image_path=logo_image_path,
            position="top-left", # Posizione stile EDISU
            logo_size=(100, 100),
            opacity=255
        )

    # 7. Conversione e Salvataggio (Supporto per JPEG)
    if image.mode == 'RGBA':
        image = image.convert('RGB')
        
    image.save(output_path, "JPEG", quality=95)
    return output_path