import asyncio
import pandas as pd
from playwright.async_api import async_playwright
import json
from datetime import datetime
import logging
import os

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

async def debug_page_content(page, page_name):
    """Debug what's actually on the page"""
    logger.info(f"🔍 Debugging {page_name} page content...")
    
    # Check page title
    title = await page.title()
    logger.info(f"📄 Page title: '{title}'")
    
    # Check if page loaded
    content = await page.content()
    logger.info(f"📊 Page content length: {len(content)} characters")
    
    # Look for common elements
    tables = await page.query_selector_all('table')
    divs = await page.query_selector_all('div')
    spans = await page.query_selector_all('span')
    
    logger.info(f"🔢 Found: {len(tables)} tables, {len(divs)} divs, {len(spans)} spans")
    
    # Check for any text containing "gas", "flow", "capacity"
    gas_text = await page.evaluate("""
        () => {
            const text = document.body.innerText.toLowerCase();
            const gasCount = (text.match(/gas/g) || []).length;
            const flowCount = (text.match(/flow/g) || []).length;
            const capacityCount = (text.match(/capacity/g) || []).length;
            const dataCount = (text.match(/data/g) || []).length;
            
            return {
                gas: gasCount,
                flow: flowCount,
                capacity: capacityCount,
                data: dataCount,
                firstWords: text.substring(0, 500)
            };
        }
    """)
    
    logger.info(f"📝 Keywords found - Gas: {gas_text['gas']}, Flow: {gas_text['flow']}, Capacity: {gas_text['capacity']}, Data: {gas_text['data']}")
    logger.info(f"📖 First 500 characters: {gas_text['firstWords'][:200]}...")
    
    # Check for error messages
    error_elements = await page.query_selector_all('[class*="error"], [class*="Error"], .alert, .warning')
    if error_elements:
        logger.warning(f"⚠️ Found {len(error_elements)} potential error elements")

async def scrape_with_multiple_strategies(page, url, page_name):
    """Try multiple scraping strategies"""
    logger.info(f"🌐 Scraping {page_name} from: {url}")
    
    try:
        # Strategy 1: Basic navigation
        await page.goto(url, wait_until='networkidle', timeout=60000)
        await asyncio.sleep(5)  # Wait for JS to load
        
        await debug_page_content(page, page_name)
        
        # Strategy 2: Look for tables
        tables = await page.query_selector_all('table')
        if tables:
            logger.info(f"✅ Found {len(tables)} table(s), attempting extraction...")
            
            table_data = await page.evaluate("""
                () => {
                    const tables = document.querySelectorAll('table');
                    let allData = [];
                    
                    tables.forEach((table, tableIndex) => {
                        const rows = table.querySelectorAll('tr');
                        console.log(`Table ${tableIndex + 1}: ${rows.length} rows`);
                        
                        if (rows.length > 1) {
                            // Extract headers
                            const headerCells = rows[0].querySelectorAll('th, td');
                            const headers = Array.from(headerCells).map(cell => 
                                cell.textContent.trim()
                            );
                            
                            // Extract data rows
                            for (let i = 1; i < Math.min(rows.length, 11); i++) { // Limit to first 10 rows for debugging
                                const cells = rows[i].querySelectorAll('td');
                                if (cells.length > 0) {
                                    const rowData = {
                                        table_index: tableIndex,
                                        row_index: i
                                    };
                                    
                                    Array.from(cells).forEach((cell, cellIndex) => {
                                        const header = headers[cellIndex] || `column_${cellIndex}`;
                                        rowData[header] = cell.textContent.trim();
                                    });
                                    
                                    allData.push(rowData);
                                }
                            }
                        }
                    });
                    
                    return allData;
                }
            """)
            
            if table_data and len(table_data) > 0:
                logger.info(f"✅ Extracted {len(table_data)} rows from tables")
                return pd.DataFrame(table_data)
            else:
                logger.warning("⚠️ No data extracted from tables")
        
        # Strategy 3: Look for divs with data attributes
        data_divs = await page.query_selector_all('[data-*], .data, .table-row, .grid-row')
        if data_divs:
            logger.info(f"🔍 Found {len(data_divs)} potential data containers")
        
        # Strategy 4: Wait longer and try again
        logger.info("⏳ Waiting additional 10 seconds for dynamic content...")
        await asyncio.sleep(10)
        
        # Try table extraction again
        final_tables = await page.query_selector_all('table')
        if len(final_tables) != len(tables):
            logger.info(f"📊 Table count changed from {len(tables)} to {len(final_tables)}")
        
        return pd.DataFrame()
        
    except Exception as e:
        logger.error(f"❌ Error scraping {page_name}: {str(e)}")
        return pd.DataFrame()

async def scrape_wa_gbb_data():
    """Enhanced scraper with comprehensive debugging"""
    logger.info("🚀 Starting enhanced WA GBB data scraping with debugging...")
    
    async with async_playwright() as p:
        # Launch browser with more options
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        
        page = await browser.new_page()
        page.set_default_timeout(60000)
        
        # Set user agent to avoid bot detection
        await page.set_extra_http_headers({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        results = {}
        
        # Test URLs
        urls_to_test = {
            'flows': 'https://gbbwa.aemo.com.au/#flows',
            'capacity': 'https://gbbwa.aemo.com.au/#reports/mediumTermCapacity', 
            'storage': 'https://gbbwa.aemo.com.au/#reports/actualFlow'
        }
        
        for data_type, url in urls_to_test.items():
            logger.info(f"\n{'='*50}")
            logger.info(f"🎯 Processing {data_type.upper()}")
            logger.info(f"{'='*50}")
            
            df = await scrape_with_multiple_strategies(page, url, data_type)
            results[data_type] = df
            
            if not df.empty:
                logger.info(f"✅ SUCCESS: {data_type} - {len(df)} records extracted")
            else:
                logger.warning(f"⚠️ NO DATA: {data_type} - 0 records extracted")
            
            # Small delay between pages
            await asyncio.sleep(3)
        
        await browser.close()
        
        # Create output files
        os.makedirs('data', exist_ok=True)
        timestamp = datetime.now().isoformat()
        
        file_mapping = {
            'flows': 'flows_data.csv',
            'capacity': 'capacity_data.csv',
            'storage': 'storage_data.csv'
        }
        
        for data_type, filename in file_mapping.items():
            df = results.get(data_type, pd.DataFrame())
            
            if df.empty:
                # Create debug info file
                df = pd.DataFrame({
                    'debug_status': ['no_data_found'],
                    'timestamp': [timestamp],
                    'url_tested': [urls_to_test.get(data_type, 'unknown')],
                    'scraper_version': ['enhanced_debug_v1.0']
                })
            else:
                df['scraped_at'] = timestamp
            
            filepath = f'data/{filename}'
            df.to_csv(filepath, index=False)
            logger.info(f"💾 Saved {data_type} to {filepath}: {len(df)} records")
        
        # Enhanced metadata
        total_records = sum(len(df) if not df.empty else 0 for df in results.values())
        metadata = {
            'scrape_timestamp': timestamp,
            'records_by_type': {k: len(v) if not v.empty else 0 for k, v in results.items()},
            'total_records': total_records,
            'status': 'data_found' if total_records > 0 else 'no_data_extracted',
            'urls_tested': urls_to_test,
            'scraper_version': 'enhanced_debug_v1.0'
        }
        
        with open('data/metadata.json', 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"\n🏁 FINAL SUMMARY:")
        logger.info(f"📊 Total records extracted: {total_records}")
        for data_type, df in results.items():
            logger.info(f"   - {data_type}: {len(df) if not df.empty else 0} records")
        
        if total_records == 0:
            logger.error("🚨 NO DATA EXTRACTED - Check logs above for specific page issues")
            logger.error("🔧 This indicates the WA GBB website structure may have changed")

if __name__ == "__main__":
    asyncio.run(scrape_wa_gbb_data())
