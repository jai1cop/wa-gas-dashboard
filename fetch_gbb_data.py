from playwright.sync_api import sync_playwright
import pandas as pd
from bs4 import BeautifulSoup
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def scrape_wa_gbb_page(url, page_name, wait_time=15):
    """
    Generic scraper for WA GBB pages using Playwright.
    Returns the first valid pandas.DataFrame parsed from tables on the page.
    """
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
            page = context.new_page()

            logger.info(f"Scraping {page_name} from: {url}")
            page.goto(url, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(wait_time * 1000)  # Wait for JS to load the tables

            content = page.content()
            browser.close()

            soup = BeautifulSoup(content, 'html.parser')
            tables = soup.find_all('table')

            for i, table in enumerate(tables):
                try:
                    df = pd.read_html(str(table))[0]
                    if not df.empty and df.shape[1] > 1:
                        logger.info(f"Successfully scraped {page_name} - Table {i}, shape: {df.shape}")
                        return df
                except Exception:
                    continue

            logger.warning(f"No valid tables found for {page_name}")
            return pd.DataFrame()
    except Exception as e:
        logger.error(f"Error scraping {page_name}: {e}")
        return pd.DataFrame()

def get_daily_flows():
    url = "https://gbbwa.aemo.com.au/#flows"
    return scrape_wa_gbb_page(url, "Daily Flows", wait_time=20)

def get_medium_term_constraints():
    url = "https://gbbwa.aemo.com.au/#reports/mediumTermCapacity"
    return scrape_wa_gbb_page(url, "Medium Term Capacity", wait_time=20)

def get_storage_history():
    url = "https://gbbwa.aemo.com.au/#reports/actualFlow"
    return scrape_wa_gbb_page(url, "Storage Data", wait_time=20)

def get_all_gbb_data():
    logger.info("Starting WA GBB data scraping...")
    start_time = time.time()
    flows = get_daily_flows()
    constraints = get_medium_term_constraints()
    storage = get_storage_history()
    logger.info(f"Scraping completed in {time.time() - start_time:.1f} seconds")
    return flows, constraints, storage
