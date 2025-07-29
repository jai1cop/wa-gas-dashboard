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
        
        results = {}
        
        # Scrape Daily Flows
        try:
            logger.info("Scraping Daily Flows...")
            await page.goto('https://gbbwa.aemo.com.au/#flows')
            await page.wait_for_selector('table', timeout=20000)
            
            # Wait for data to load
            await asyncio.sleep(3)
            
            # Extract table data
            flows_data = await page.evaluate("""
                () => {
                    const tables = document.querySelectorAll('table');
                    let data = [];
                    
                    tables.forEach(table => {
                        const rows = table.querySelectorAll('tr');
                        if (rows.length > 1) {
                            const headers = Array.from(rows[0].querySelectorAll('th, td')).map(cell => cell.textContent.trim());
                            
                            for (let i = 1; i < rows.length; i++) {
                                const cells = Array.from(rows[i].querySelectorAll('td')).map(cell => cell.textContent.trim());
                                if (cells.length === headers.length) {
                                    let rowData = {};
                                    headers.forEach((header, index) => {
                                        rowData[header] = cells[index];
                                    });
                                    data.push(rowData);
                                }
                            }
                        }
                    });
                    
                    return data;
                }
            """)
            
            if flows_data:
                df_flows = pd.DataFrame(flows_data)
                results['flows'] = df_flows
                logger.info(f"✅ Daily Flows: {len(df_flows)} records")
            else:
                logger.warning("⚠️ No Daily Flows data found")
                
        except Exception as e:
            logger.error(f"❌ Error scraping Daily Flows: {e}")
        
        # Scrape Medium Term Capacity
        try:
            logger.info("Scraping Medium Term Capacity...")
            await page.goto('https://gbbwa.aemo.com.au/#reports/mediumTermCapacity')
            await page.wait_for_selector('table', timeout=20000)
            await asyncio.sleep(3)
            
            capacity_data = await page.evaluate("""
                () => {
                    const tables = document.querySelectorAll('table');
                    let data = [];
                    
                    tables.forEach(table => {
                        const rows = table.querySelectorAll('tr');
                        if (rows.length > 1) {
                            const headers = Array.from(rows[0].querySelectorAll('th, td')).map(cell => cell.textContent.trim());
                            
                            for (let i = 1; i < rows.length; i++) {
                                const cells = Array.from(rows[i].querySelectorAll('td')).map(cell => cell.textContent.trim());
                                if (cells.length === headers.length) {
                                    let rowData = {};
                                    headers.forEach((header, index) => {
                                        rowData[header] = cells[index];
                                    });
                                    data.push(rowData);
                                }
                            }
                        }
                    });
                    
                    return data;
                }
            """)
            
            if capacity_data:
                df_capacity = pd.DataFrame(capacity_data)
                results['capacity'] = df_capacity
                logger.info(f"✅ Medium Term Capacity: {len(df_capacity)} records")
            else:
                logger.warning("⚠️ No Medium Term Capacity data found")
                
        except Exception as e:
            logger.error(f"❌ Error scraping Medium Term Capacity: {e}")
        
        # Scrape Storage Data
        try:
            logger.info("Scraping Storage Data...")
            await page.goto('https://gbbwa.aemo.com.au/#reports/actualFlow')
            await page.wait_for_selector('table', timeout=20000)
            await asyncio.sleep(3)
            
            storage_data = await page.evaluate("""
                () => {
                    const tables = document.querySelectorAll('table');
                    let data = [];
                    
                    tables.forEach(table => {
                        const rows = table.querySelectorAll('tr');
                        if (rows.length > 1) {
                            const headers = Array.from(rows[0].querySelectorAll('th, td')).map(cell => cell.textContent.trim());
                            
                            for (let i = 1; i < rows.length; i++) {
                                const cells = Array.from(rows[i].querySelectorAll('td')).map(cell => cell.textContent.trim());
                                if (cells.length === headers.length) {
                                    let rowData = {};
                                    headers.forEach((header, index) => {
                                        rowData[header] = cells[index];
                                    });
                                    data.push(rowData);
                                }
                            }
                        }
                    });
                    
                    return data;
                }
            """)
            
            if storage_data:
                df_storage = pd.DataFrame(storage_data)
                results['storage'] = df_storage
                logger.info(f"✅ Storage Data: {len(df_storage)} records")
            else:
                logger.warning("⚠️ No Storage data found")
                
        except Exception as e:
            logger.error(f"❌ Error scraping Storage Data: {e}")
        
        await browser.close()
        
        # Save data to CSV files
        os.makedirs('data', exist_ok=True)
        timestamp = datetime.now().isoformat()
        
        for data_type, df in results.items():
            if df is not None and not df.empty:
                # Add timestamp column
                df['last_updated'] = timestamp
                df.to_csv(f'data/{data_type}_data.csv', index=False)
                logger.info(f"💾 Saved {data_type} data to data/{data_type}_data.csv")
        
        # Create metadata file
        metadata = {
            'last_run': timestamp,
            'records_scraped': {k: len(v) if v is not None else 0 for k, v in results.items()},
            'status': 'success' if results else 'no_data'
        }
        
        with open('data/metadata.json', 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"📊 Scraping completed - {sum(len(v) if v is not None else 0 for v in results.values())} total records")

if __name__ == "__main__":
    asyncio.run(scrape_wa_gbb_data())
