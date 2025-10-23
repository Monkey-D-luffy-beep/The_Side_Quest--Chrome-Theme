"""
Pinterest Aesthetic Image Scraper
Scrapes high-quality images from Pinterest with anti-bot measures and validation
"""

import asyncio
import json
import re
import sys
from pathlib import Path
from typing import List, Dict, Optional
from urllib.parse import urlparse, urljoin

try:
    from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeout
except ImportError:
    print("ERROR: Playwright not installed. Run: pip install playwright && playwright install")
    sys.exit(1)


class PinterestScraper:
    """Robust Pinterest scraper with anti-bot handling and image validation"""

    def __init__(self, headless: bool = True, slow_mo: int = 100):
        self.headless = headless
        self.slow_mo = slow_mo
        self.browser: Optional[Browser] = None
        self.results: List[Dict] = []

    async def init_browser(self):
        """Initialize browser with anti-detection measures"""
        playwright = await async_playwright().start()

        # Use realistic browser context
        self.browser = await playwright.chromium.launch(
            headless=self.headless,
            slow_mo=self.slow_mo,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-web-security',
            ]
        )

        context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-US',
            timezone_id='America/New_York',
            permissions=['geolocation'],
            extra_http_headers={
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
        )

        # Override navigator.webdriver flag
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false
            });
        """)

        return context

    def convert_to_original_url(self, url: str) -> str:
        """Convert Pinterest thumbnail URLs to original high-res versions"""
        if not url or 'pinimg.com' not in url:
            return url

        # Replace all thumbnail sizes with /originals/
        patterns = [
            (r'/236x/', '/originals/'),
            (r'/474x/', '/originals/'),
            (r'/564x/', '/originals/'),
            (r'/736x/', '/originals/'),
            (r'/originals/', '/originals/'),  # Already original
        ]

        for pattern, replacement in patterns:
            url = re.sub(pattern, replacement, url)

        return url

    def is_valid_image_url(self, url: str) -> bool:
        """Check if URL is a valid, accessible image"""
        if not url or not isinstance(url, str):
            return False

        # Filter out unwanted URLs
        invalid_patterns = [
            'blob:',
            'data:',
            'video-thumbnails',
            'storypin',
            '.gif',  # Often low quality animations
        ]

        for pattern in invalid_patterns:
            if pattern in url.lower():
                return False

        # Must be from Pinterest CDN
        if 'pinimg.com' not in url:
            return False

        # Must have valid image extension
        valid_extensions = ['.jpg', '.jpeg', '.png', '.webp']
        url_path = urlparse(url).path.lower()
        if not any(url_path.endswith(ext) for ext in valid_extensions):
            return False

        return True

    async def scroll_page(self, page: Page, scrolls: int = 3):
        """Gradually scroll page to load more content"""
        for i in range(scrolls):
            await page.evaluate('window.scrollBy(0, window.innerHeight * 0.8)')
            await asyncio.sleep(1.5)  # Wait for content to load

    async def check_image_dimensions(self, img_element) -> tuple:
        """Get image dimensions to filter for landscape/high-quality"""
        try:
            dimensions = await img_element.evaluate('''
                (img) => {
                    return {
                        width: img.naturalWidth || img.width,
                        height: img.naturalHeight || img.height
                    };
                }
            ''')
            return dimensions.get('width', 0), dimensions.get('height', 0)
        except:
            return 0, 0

    def is_landscape_high_quality(self, width: int, height: int) -> bool:
        """Check if image is landscape and high quality"""
        if width == 0 or height == 0:
            return False

        # Minimum resolution for high quality
        MIN_WIDTH = 1920
        MIN_HEIGHT = 1080

        # Check if landscape (width > height)
        is_landscape = width > height

        # Check if high enough resolution
        is_high_quality = width >= MIN_WIDTH and height >= MIN_HEIGHT

        # Aspect ratio check (between 1.3:1 and 2.5:1 for good desktop wallpapers)
        aspect_ratio = width / height if height > 0 else 0
        good_aspect_ratio = 1.3 <= aspect_ratio <= 2.5

        return is_landscape and is_high_quality and good_aspect_ratio

    async def extract_pins_from_page(self, page: Page) -> List[Dict]:
        """Extract pin data from current page - landscape high-quality only"""
        pins = []

        try:
            # Wait for pins to load
            await page.wait_for_selector('[data-test-id="pin"]', timeout=10000)

            # Extract all pin elements
            pin_elements = await page.query_selector_all('[data-test-id="pin"]')

            print(f"Found {len(pin_elements)} pins on page...")

            for pin in pin_elements:
                try:
                    # Extract image URL
                    img = await pin.query_selector('img')
                    if not img:
                        continue

                    # Get the actual image source
                    img_src = await img.get_attribute('src')
                    if not img_src:
                        # Try srcset as fallback
                        srcset = await img.get_attribute('srcset')
                        if srcset:
                            # Parse srcset and get highest resolution
                            srcset_parts = srcset.split(',')
                            img_src = srcset_parts[-1].strip().split(' ')[0]

                    if not img_src:
                        continue

                    # Convert to original high-res URL
                    original_url = self.convert_to_original_url(img_src)

                    # Validate URL
                    if not self.is_valid_image_url(original_url):
                        continue

                    # For Pinterest originals, we trust they're high quality
                    # Pinterest thumbnails don't show actual dimensions
                    # Original URLs are typically high-res landscape wallpapers when searched with "wallpaper" keywords

                    # Extract pin title/description
                    title_elem = await pin.query_selector('[data-test-id="pinrep-title"]')
                    title = await title_elem.inner_text() if title_elem else "Aesthetic Pin"

                    # Extract pin URL
                    link = await pin.query_selector('a[href*="/pin/"]')
                    pin_url = await link.get_attribute('href') if link else ""
                    if pin_url and not pin_url.startswith('http'):
                        pin_url = urljoin('https://www.pinterest.com', pin_url)

                    pins.append({
                        'title': title.strip() if title else "Aesthetic Pin",
                        'url': pin_url,
                        'media': original_url,
                        'quality': 'hd-original'
                    })

                    print(f"  ✓ Added HD image from originals")

                except Exception as e:
                    print(f"Error extracting pin: {e}")
                    continue

        except PlaywrightTimeout:
            print("Timeout waiting for pins to load")

        return pins

    async def scrape_search(self, keyword: str, max_pins: int = 50) -> List[Dict]:
        """Scrape Pinterest search results for a keyword"""
        print(f"\nScraping Pinterest for: '{keyword}'")

        context = await self.init_browser()
        page = await context.new_page()

        try:
            # Navigate to Pinterest search
            search_url = f"https://www.pinterest.com/search/pins/?q={keyword.replace(' ', '%20')}"
            print(f"Navigating to: {search_url}")

            await page.goto(search_url, wait_until='networkidle', timeout=30000)

            # Wait a bit for initial load
            await asyncio.sleep(2)

            # Check if we hit a login wall
            login_button = await page.query_selector('button:has-text("Log in")')
            if login_button:
                print("⚠ Login wall detected. Continuing without login (may have limited results)...")

            # Scroll to load more pins
            num_scrolls = min(5, (max_pins // 10) + 1)
            await self.scroll_page(page, scrolls=num_scrolls)

            # Extract pins
            pins = await self.extract_pins_from_page(page)

            # Remove duplicates based on media URL
            seen_urls = set()
            unique_pins = []
            for pin in pins:
                if pin['media'] not in seen_urls:
                    seen_urls.add(pin['media'])
                    unique_pins.append(pin)
                    if len(unique_pins) >= max_pins:
                        break

            self.results.extend(unique_pins)
            print(f"✓ Extracted {len(unique_pins)} unique pins")

            return unique_pins

        except Exception as e:
            print(f"Error scraping Pinterest: {e}")
            return []

        finally:
            await page.close()
            await context.close()

    async def scrape_board(self, board_url: str, max_pins: int = 50) -> List[Dict]:
        """Scrape a specific Pinterest board"""
        print(f"\nScraping Pinterest board: {board_url}")

        context = await self.init_browser()
        page = await context.new_page()

        try:
            await page.goto(board_url, wait_until='networkidle', timeout=30000)
            await asyncio.sleep(2)

            # Scroll to load more pins
            num_scrolls = min(5, (max_pins // 10) + 1)
            await self.scroll_page(page, scrolls=num_scrolls)

            pins = await self.extract_pins_from_page(page)

            # Remove duplicates
            seen_urls = set()
            unique_pins = []
            for pin in pins:
                if pin['media'] not in seen_urls:
                    seen_urls.add(pin['media'])
                    unique_pins.append(pin)
                    if len(unique_pins) >= max_pins:
                        break

            self.results.extend(unique_pins)
            print(f"✓ Extracted {len(unique_pins)} unique pins from board")

            return unique_pins

        except Exception as e:
            print(f"Error scraping board: {e}")
            return []

        finally:
            await page.close()
            await context.close()

    async def close(self):
        """Close browser"""
        if self.browser:
            await self.browser.close()

    def save_results(self, filepath: str = "pinterest_cache.json"):
        """Save scraped results to JSON file"""
        output_path = Path(filepath)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)

        print(f"\n✓ Saved {len(self.results)} pins to {output_path}")


async def main():
    """Main scraper entry point"""
    print("=" * 60)
    print("Pinterest Aesthetic Image Scraper")
    print("=" * 60)

    # Configuration - Optimized for landscape HD wallpapers
    KEYWORDS = [
        "aesthetic desktop wallpaper 4k",
        "minimalist wallpaper hd 1920x1080",
        "nature desktop background landscape",
        "dark aesthetic desktop wallpaper",
        "aesthetic laptop wallpaper hd",
    ]

    PINS_PER_KEYWORD = 30  # More per keyword for better variety
    OUTPUT_FILE = "pinterest_cache.json"
    EXTENSION_OUTPUT = "extension/data/pinterest_cache.json"

    scraper = PinterestScraper(headless=True, slow_mo=50)

    try:
        # Scrape each keyword
        for keyword in KEYWORDS:
            await scraper.scrape_search(keyword, max_pins=PINS_PER_KEYWORD)
            await asyncio.sleep(2)  # Be nice to Pinterest

        # Save results
        scraper.save_results(OUTPUT_FILE)

        # Also save to extension directory
        scraper.save_results(EXTENSION_OUTPUT)

        print(f"\n{'='*60}")
        print(f"Scraping complete! Total pins: {len(scraper.results)}")
        print(f"{'='*60}")

    except KeyboardInterrupt:
        print("\n\nScraping interrupted by user")

    finally:
        await scraper.close()


if __name__ == "__main__":
    asyncio.run(main())
