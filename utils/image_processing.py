"""
Utilities per elaborazione immagini - Versione Ottimizzata
"""
import os
from PIL import Image, ImageDraw, ImageFont
from typing import Tuple, Optional
from utils.translate_text import translate_text
from config.constants import (
    IMAGE_WIDTH, IMAGE_HEIGHT, BG_COLOR, TEXT_COLOR, IMAGE_MARGIN
)

try:
    import cairosvg
    SVG_SUPPORT = True
except ImportError:
    SVG_SUPPORT = False

def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> str:
    """Divide il testo in più righe per adattarsi alla larghezza massima."""
    lines = []
    for paragraph in text.split('\n'):
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        
        current_line = []
        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = font.getbbox(test_line)
            width = bbox[2] - bbox[0]
            
            if width <= max_width:
                current_line.append(word)
            else:
                lines.append(' '.join(current_line))
                current_line = [word]
        lines.append(' '.join(current_line))
    return '\n'.join(lines)

def add_watermark(
    image: Image.Image,
    watermark_text: Optional[str] = None,
    watermark_image_path: Optional[str] = None,
    position: str = "top-left",
    font_size: int = 24,
    opacity: int = 255,
    logo_size: Tuple[int, int] = (150, 150)
) -> Image.Image:
    if image.mode != 'RGBA':
        image = image.convert('RGBA')
    
    watermark_layer = Image.new('RGBA', image.size, (0, 0, 0, 0))
    padding = 20
    
    if watermark_image_path and os.path.exists(watermark_image_path):
        try:
            if watermark_image_path.lower().endswith('.svg') and SVG_SUPPORT:
                import io
                png_data = cairosvg.svg2png(url=watermark_image_path)
                logo = Image.open(io.BytesIO(png_data))
            else:
                logo = Image.open(watermark_image_path)
            
            if logo.mode != 'RGBA':
                logo = logo.convert('RGBA')
            
            logo.thumbnail(logo_size, Image.Resampling.LANCZOS)
            alpha = logo.split()[3].point(lambda p: int(p * (opacity / 255.0)))
            logo.putalpha(alpha)
            
            lw, lh = logo.size
            pos_map = {
                "bottom-right": (image.width - lw - padding, image.height - lh - padding),
                "bottom-left": (padding, image.height - lh - padding),
                "top-right": (image.width - lw - padding, padding),
                "top-left": (padding, padding)
            }
            watermark_layer.paste(logo, pos_map.get(position, pos_map["bottom-right"]), logo)
        except:
            watermark_text = watermark_text or "LOGO"

    if watermark_text and not (watermark_image_path and os.path.exists(watermark_image_path)):
        draw = ImageDraw.Draw(watermark_layer)
        font = _get_font(font_size)
        bbox = draw.textbbox((0, 0), watermark_text, font=font)
        tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
        pos_map = {
            "bottom-right": (image.width - tw - padding, image.height - th - padding),
            "bottom-left": (padding, image.height - th - padding),
            "top-right": (image.width - tw - padding, padding),
            "top-left": (padding, padding)
        }
        draw.text(pos_map.get(position, pos_map["bottom-right"]), watermark_text, fill=(255, 255, 255, opacity), font=font)
    
    return Image.alpha_composite(image, watermark_layer)

def _get_font(size: int):
    for path in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 
                 "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 
                 "arialbd.ttf"]:
        try: return ImageFont.truetype(path, size)
        except: continue
    return ImageFont.load_default()

async def create_long_image(
    text: str,
    output_path: str,
    logo_text: Optional[str] = "@RunMensaBot on telegram",
    add_logo: bool = True,
    logo_image_path: Optional[str] = "assets/run_logo.png"
) -> str:
    # Setup
    image = Image.new("RGB", (IMAGE_WIDTH, IMAGE_HEIGHT), color=BG_COLOR)
    draw = ImageDraw.Draw(image)
    font_title = _get_font(60)
    font_items = _get_font(30)
    font_footer = _get_font(30)

    # Pulizia testo
    lines = [line.strip().upper() for line in text.split('\n') if line.strip()]
    if not lines: return ""

    curr_y = 250 

    # Titolo
    title = lines[0].replace("MENSA UNIVERSITARIA", "").replace("DEL POLITECNICO", "").strip()
    bbox_t = draw.textbbox((0, 0), title, font=font_title)
    draw.text(((IMAGE_WIDTH - (bbox_t[2] - bbox_t[0])) // 2, curr_y), title, fill=TEXT_COLOR, font=font_title)
    
    curr_y += 150
    draw.line((200, curr_y, IMAGE_WIDTH - 200, curr_y), fill=TEXT_COLOR, width=2)
    curr_y += 80

    # Piatti con Wrapping (Fix logico qui)
    if len(lines) > 1:
        raw_content = "\n".join(lines[1:])
        max_w = IMAGE_WIDTH - (IMAGE_MARGIN * 2)
        content_text = wrap_text(raw_content, font_items, max_w)
        
        line_spacing = 15
        bbox_c = draw.multiline_textbbox((0, 0), content_text, font=font_items, align="center", spacing=line_spacing)
        
        draw.multiline_text(
            ((IMAGE_WIDTH - (bbox_c[2] - bbox_c[0])) // 2, curr_y), 
            content_text, 
            fill=TEXT_COLOR, 
            font=font_items, 
            align="center", 
            spacing=line_spacing
        )

    # Footer
    footer_note = await translate_text("Verificare la presenza di allergeni presso i locali della mensa.", dest_language="en")
    draw.line((IMAGE_MARGIN, IMAGE_HEIGHT - 200, IMAGE_WIDTH - IMAGE_MARGIN, IMAGE_HEIGHT - 200), fill=TEXT_COLOR, width=3)
    
    bbox_f = draw.multiline_textbbox((0, 0), footer_note, font=font_footer, align="center")
    draw.multiline_text(
        ((IMAGE_WIDTH - (bbox_f[2] - bbox_f[0])) // 2, IMAGE_HEIGHT - 160), 
        footer_note, 
        fill=TEXT_COLOR, 
        font=font_footer, 
        align="center"
    )

    # Logo
    if add_logo:
        image = add_watermark(image, watermark_text=logo_text, watermark_image_path=logo_image_path, position="top-left", logo_size=(100, 100))

    # Salvataggio
    if image.mode == 'RGBA': image = image.convert('RGB')
    image.save(output_path, "JPEG", quality=95)
    return output_path