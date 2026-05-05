from utils.logger import setup_logger
import asyncio
from playwright.async_api import async_playwright
import re

logger = setup_logger(__name__)

class WebScrapingService:
    """
    Servizio per scaricare da siti mirror pubblici
    """
    
    async def get_stories_by_browser(self, username: str="edisupiemonte"):
        logger.info(f"🌐 Avvio browser per storie di {username} su Picuki (SPA Mode)...")
        stories_urls: list = []
    
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
            )
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
                viewport={'width': 1280, 'height': 1000}
            )
            page = await context.new_page()
            target_url = "https://www.picuki.site" 
            
            try:
                logger.info(f"Navigazione verso {target_url}...")
                await page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
                input_box = await page.wait_for_selector(".main-form__input", timeout=15000)
                await input_box.fill(username)
                await page.click(".main-form__field-download")
                logger.info("⏳ Attendendo il rendering del profilo...")
                await page.wait_for_selector(".output-info, .tabs-component", timeout=20000)
                tab_stories = page.locator(".tabs-component__button").filter(has_text=re.compile(r"stories", re.I)).first
                
                await tab_stories.wait_for(state="visible", timeout=10000)
                await page.evaluate("window.scrollBy(0, 300)") 
                await tab_stories.click(force=True) # force=True aiuta se ci sono overlay trasparenti
                logger.info("🖱️ Tab STORIES cliccato.")
                
                img_selector = ".media-content__image"
                await page.wait_for_selector(img_selector, timeout=15000)
                await page.evaluate("window.scrollTo(0, 800)")
                await asyncio.sleep(2) # Pausa necessaria per il caricamento delle immagini reali
                media_elements = await page.locator(img_selector).all()
                logger.info(f"Elementi trovati: {media_elements}")
                logger.info(f"🔎 Elementi trovati: {len(media_elements)}")
                
                for i, elm in enumerate(media_elements):
                    url = (
                        await elm.get_attribute("src") or 
                        await elm.get_attribute("data-src") or 
                        await elm.get_attribute("data-original")
                    )
                    
                    if url and not url.startswith("data:image") and ("fbcdn" in url or "instagram" in url):
                        logger.debug(f"  [{i+1}] URL trovato: {url[:80]}")
                        stories_urls.append(url)
                
                logger.info(f"✅ Operazione completata: {len(stories_urls)} storie estratte.")

            except Exception as e:
                logger.error(f"❌ Errore scraping: {e}")
                await page.screenshot(path="data/debug_error.png")
            finally:
                await browser.close()
                
        return stories_urls