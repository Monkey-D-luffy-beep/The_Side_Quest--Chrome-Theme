# Pinterest X Side Quest - Chrome Extension


A Chrome extension that automatically updates your browser's new tab with beautiful aesthetic images from Pinterest.

## Features

- **Automatic Background Rotation**: Beautiful images change every hour (configurable)
- **High-Resolution Images**: Scrapes original quality images from Pinterest
- **Dark Mode Support**: Toggle between light and dark themes
- **Smart Retry Logic**: Automatically tries next image if one fails to load
- **Error Handling**: Robust error handling with user-friendly messages
- **No CORS Issues**: Properly configured to load Pinterest CDN images
- **Aesthetic UI**: Beautiful, modern interface with smooth animations

## Project Structure

```
side_quest/
├── extension/               # Chrome extension files
│   ├── manifest.json       # Extension configuration
│   ├── background.js       # Service worker for background tasks
│   ├── newtab.html         # New tab page HTML
│   ├── newtab.js           # New tab page logic
│   ├── popup.html          # Extension popup HTML
│   ├── popup.js            # Extension popup logic
│   ├── styles.css          # Styling for new tab page
│   ├── icons/              # Extension icons
│   └── data/
│       └── pinterest_cache.json  # Cached Pinterest images
├── pinterest_scraper.py    # Pinterest scraper with anti-bot measures
├── validate_images.py      # Image URL validator
├── quick_fix.py           # Utility to convert thumbnail URLs to originals
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## Installation

### 1. Set Up Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install
```

### 2. Scrape Pinterest Images

```bash
# Run the scraper (this will take a few minutes)
python pinterest_scraper.py
```

The scraper will:
- Search Pinterest for aesthetic keywords
- Extract high-resolution image URLs
- Filter out invalid/broken URLs
- Save results to `extension/data/pinterest_cache.json`

**Customize Scraping**: Edit `pinterest_scraper.py` to change keywords or add Pinterest board URLs.

### 3. Validate Image URLs (Optional but Recommended)

```bash
# Validate that all scraped URLs are accessible
python validate_images.py
```

This checks each URL to ensure images will actually load and removes dead links.

### 4. Load Extension in Chrome

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable "Developer mode" (toggle in top-right)
3. Click "Load unpacked"
4. Select the `extension` folder from this project
5. The extension is now installed!

### 5. Test It Out

- Open a new tab to see a random aesthetic image
- Click the extension icon to access controls:
  - **Next Image**: Skip to next random image
  - **Reload Local Cache**: Refresh the image cache
  - **Dark Mode**: Toggle dark/light theme

## Configuration

### Change Rotation Interval

Edit [`extension/background.js`](extension/background.js:9):

```javascript
const DEFAULT_PERIOD_MINUTES = 60; // Change this value
```

### Customize Scraping Keywords

Edit [`pinterest_scraper.py`](pinterest_scraper.py) and modify the `KEYWORDS` list:

```python
KEYWORDS = [
    "your custom keyword",
    "another aesthetic theme",
    "nature wallpaper",
]
```

### Scrape Specific Pinterest Boards

In `pinterest_scraper.py`, use the `scrape_board()` method:

```python
board_url = "https://www.pinterest.com/username/board-name/"
await scraper.scrape_board(board_url, max_pins=50)
```

## Troubleshooting

### Images Not Loading?

1. **Check CSP Settings**: The manifest.json is configured to allow Pinterest CDN images
2. **Validate Cache**: Run `python validate_images.py` to remove broken URLs
3. **Check Console**: Open DevTools (F12) on the new tab page to see errors
4. **Reload Extension**: Go to `chrome://extensions/` and click the reload icon

### Scraper Not Working?

1. **Pinterest Changes**: Pinterest frequently updates their site. The scraper may need adjustments
2. **Login Wall**: Pinterest sometimes requires login. The scraper handles this but results may be limited
3. **Rate Limiting**: If scraping fails, wait a few minutes and try again
4. **Headless Mode**: Try running with `headless=False` to see what's happening:
   ```python
   scraper = PinterestScraper(headless=False)
   ```

### CORS Errors?

- This is expected! Pinterest blocks cross-origin image analysis
- Images will still load, but color theme extraction won't work
- This is a deliberate tradeoff to ensure images display properly

### Extension Not Loading?

1. Check that `extension/data/pinterest_cache.json` exists and has valid entries
2. Go to `chrome://extensions/` and check for errors
3. Try clicking "Reload Cache" in the extension popup

## How It Works

### Pinterest Scraper (`pinterest_scraper.py`)

- Uses Playwright for realistic browser automation
- Anti-bot measures: realistic user agent, viewport, and behaviors
- Converts thumbnail URLs to original high-res versions
- Filters out videos, low-quality images, and blob URLs
- Handles Pinterest's login walls and anti-scraping measures

### Chrome Extension

**Background Service Worker** ([`background.js`](extension/background.js)):
- Loads Pinterest cache on installation
- Picks random images and stores current selection
- Sets up hourly rotation alarm
- Handles "next image" requests from UI
- Normalizes data from old/new cache formats

**New Tab Page** ([`newtab.js`](extension/newtab.js)):
- Renders current image/video
- Handles loading states and errors
- Auto-retries on failure (up to 3 times)
- Applies dark mode styling
- Attempts color sampling for theme (fails gracefully with CORS)

**Data Flow**:
1. Scraper saves images → `extension/data/pinterest_cache.json`
2. Extension loads cache → Chrome storage
3. Background picks random image → `currentItem`
4. New tab page renders → Shows image
5. Every hour OR on "Next" click → Repeat step 3

## Security & Privacy

- **No External Servers**: All data is local
- **No User Tracking**: Zero analytics or tracking
- **Pinterest CDN Only**: Images loaded directly from Pinterest's official CDN
- **Minimal Permissions**: Only requests necessary Chrome APIs
- **Open Source**: All code is visible and auditable

## Best Practices

### For Better Results

1. **Regular Updates**: Re-run scraper weekly for fresh images
2. **Validate URLs**: Run validator after scraping to ensure quality
3. **Diverse Keywords**: Use varied search terms for image variety
4. **Sufficient Cache**: Aim for 100+ images for good rotation
5. **Monitor Console**: Check for errors occasionally

### Performance Tips

- Keep cache under 500 images for best performance
- Don't set rotation interval below 5 minutes
- Clear old cache periodically: delete `pinterest_cache.json` and re-scrape

## Advanced Usage

### Scraping Multiple Boards

```python
async def scrape_multiple_boards():
    scraper = PinterestScraper(headless=True)

    boards = [
        "https://pinterest.com/user/aesthetic-board/",
        "https://pinterest.com/user/nature-board/",
        "https://pinterest.com/user/art-board/",
    ]

    for board_url in boards:
        await scraper.scrape_board(board_url, max_pins=30)
        await asyncio.sleep(5)  # Be polite

    scraper.save_results("extension/data/pinterest_cache.json")
    await scraper.close()
```

### Custom Image Filtering

Edit the `isValidImageUrl()` function in [`background.js`](extension/background.js:33) to add your own filters.

### Add Video Support

The extension already supports videos! Just ensure your scraper extracts video URLs and they'll work automatically.

## Known Limitations

- **Pinterest API**: This uses scraping, not an official API (Pinterest doesn't offer public API access)
- **Login Wall**: Pinterest may occasionally require login, limiting results
- **Rate Limiting**: Aggressive scraping may trigger rate limits
- **CORS Restrictions**: Color theme extraction doesn't work due to Pinterest CORS policies
- **Chrome Only**: This is a Chrome extension (may work in Edge/Brave with modifications)

## Contributing

Feel free to improve the scraper, add features, or fix bugs:

1. Better anti-bot detection handling
2. Support for other browsers (Firefox, Safari)
3. User-configurable keywords in extension popup
4. Image categories/moods
5. Local image upload support

## License

This project is for educational purposes. Respect Pinterest's Terms of Service and robots.txt. Don't overload their servers with requests.

## Changelog

### v1.1 (Current)
- Fixed image rendering issues
- Added comprehensive error handling
- Improved CSP configuration
- Added loading states and retry logic
- Enhanced UI with animations
- Created robust scraper with anti-bot measures
- Added image URL validator
- Better data structure handling

### v1.0
- Initial release
- Basic scraping functionality
- Simple extension with popup

## Support

If you encounter issues:

1. Check this README's troubleshooting section
2. Review console logs in DevTools
3. Ensure you're using the latest version
4. Try re-scraping with fresh data

---

Made with care for aesthetic browsing experiences.
