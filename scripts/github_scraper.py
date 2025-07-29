import asyncio
import pandas as pd
from playwright.async_api import async_playwright
import json
from datetime import datetime
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def scrape_wa_gbb_data():
    """
    Scrape data from WA GBB website using Playwright
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Set longer timeout for JS-heavy pages
        page.set_default_timeout(30000)
        
        results = {
            'flows': pd.DataFrame(),
            'capacity': pd.DataFrame(), 
            'storage': pd.DataFrame()
        }
        
        # Scraping logic here (same as before)...
        # [Previous scraping code]
        
        await browser.close()
        
        # Ensure data directory exists
        os.makedirs('data', exist_ok=True)
        timestamp = datetime.now().isoformat()
        
        # Always save CSV files, even if empty
        data_files = {
            'flows': 'flows_data.csv',
            'capacity': 'capacity_data.csv', 
            'storage': 'storage_data.csv'
        }
        
        for data_type, filename in data_files.items():
            df = results.get(data_type, pd.DataFrame())
            
            # Add timestamp column if data exists
            if not df.empty:
                df['last_updated'] = timestamp
            else:
                # Create empty DataFrame with expected columns
                if data_type == 'flows':
                    df = pd.DataFrame(columns=['Facility', 'Date', 'Flow_TJ', 'last_updated'])
                elif data_type == 'capacity':
                    df = pd.DataFrame(columns=['Facility', 'Date', 'Capacity_TJ', 'last_updated'])
                elif data_type == 'storage':
                    df = pd.DataFrame(columns=['Facility', 'Date', 'Storage_TJ', 'last_updated'])
                
                df['last_updated'] = timestamp
            
            # Always save the file
            filepath = f'data/{filename}'
            df.to_csv(filepath, index=False)
            logger.info(f"💾 Saved {data_type} data to {filepath} ({len(df)} records)")
        
        # Create metadata file
        metadata = {
            'last_run': timestamp,
            'records_scraped': {k: len(v) if not v.empty else 0 for k, v in results.items()},
            'status': 'success' if any(not df.empty for df in results.values()) else 'no_data',
            'files_created': list(data_files.values())
        }
        
        with open('data/metadata.json', 'w') as f:
            json.dump(metadata, f, indent=2)
        
        total_records = sum(len(v) if not v.empty else 0 for v in results.values())
        logger.info(f"📊 Scraping completed - {total_records} total records, all files created")

if __name__ == "__main__":
    asyncio.run(scrape_wa_gbb_data())

