from utils.logger import setup_logger
import asyncio
from playwright.async_api import async_playwright

logger = setup_logger(__name__)

class WebScrapingService:
    """
    Servizio per scaricare da siti mirror pubblici
    """
    
    async def get_stories_by_browser(self, username: str="edisu_piemonte"):
        """
        Function for downloading stories by a mirror and not direcly from instagram
        
        :param username: username of user from which we download stories. If not provided default is edisu_piemonte
        :type username: str
        """
        
        logger.info(f"🌐 Avvio browser per cercare storie di {username} su mirror web...")
        stories_urls:list = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
            )
            page = await context.new_page()
            target_url = f"https://storynavigation.com/user/{username}"
            try:
                logger.info(f"Navigazione verso {target_url}...")
                await page.goto(target_url, wait_until='domcontentloaded', timeout=60000)
                await page.wait_for_selector(".profile-stories-item img", timeout=10000)
                # Aspetta che appaiano gli elementi delle storie (o i tab)
                # Nota: I selettori (.story-item, img) cambiano da sito a sito.
                # Qui cerchiamo immagini che potrebbero essere storie.
                # A volte bisogna cliccare un tab "Stories". 
                # Instanavigation di solito le carica di default o dopo lo scroll.
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(3) # Aspetta rendering Javascript
                # Sul loro sito hanno un div con la classe profile-stories-item che wrappa le img interessate
                media_elements = await page.locator(".profile-stories-item > img").all()
                logger.info(f"Trovati questi elementi {media_elements}")
                for i,elm in enumerate(media_elements):
                    url = (
                        await elm.get_attribute("data-src") or
                        await elm.get_attribute("data-lazy-src") or
                        await elm.get_attribute("data-original") or
                        await elm.get_attribute("src")
                    )  
                    if url and not url.startswith("data:image"):
                        logger.debug(f"  [{i+1}] URL trovato: {url[:80]}")
                        stories_urls.append(url)
                    else:
                        logger.warning(f"  [{i+1}] Nessun URL valido (url={url[:50] if url else 'None'})")
                logger.info(f"✅ Estratti {len(stories_urls)} URL da {len(media_elements)} elementi")
            except Exception as e:
                logger.error(f"Errore durante lo scraping: {e}")
                await page.screenshot(path="data/debug_error.png")
            finally:
                await browser.close()
        return stories_urls