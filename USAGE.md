# Usage Guide - Enhanced Features

## New Features

### 1. Draggable Control Panel
- Control panel starts centered at bottom
- Click and drag the handle (⋮⋮) to move it anywhere
- Position is saved automatically

### 2. Landscape HD Images Only
Scraper now filters for:
- Minimum 1920x1080 resolution
- Landscape orientation (width > height)
- Aspect ratio between 1.3:1 and 2.5:1
- Original quality URLs

### 3. Favorite/Bookmark Images
- Click ★ to bookmark current image
- Click "Favorites" button to view all bookmarked images
- Click any favorite to display it
- Remove favorites with × button

### 4. Custom Keywords (Live Scraping)
- Click "Keywords" button
- Enter keywords (comma or newline separated)
- Scraper runs automatically and fetches landscape HD images

## Setup for Custom Keywords Feature

### Option 1: With API (Recommended)

1. Install Node.js dependencies:
```bash
npm install
```

2. Start the scraper API:
```bash
node scraper_api.js
```

3. Keep the API running in background
4. Use "Keywords" button in extension - it will work automatically

### Option 2: Manual (Without API)

1. Edit `pinterest_scraper.py` and update KEYWORDS list
2. Run: `python pinterest_scraper.py`
3. Reload extension cache

## Quick Start

```bash
# Install Python dependencies
pip install -r requirements.txt
playwright install chromium

# Get initial images
python pinterest_scraper.py

# (Optional) Start API for live keyword scraping
npm install
node scraper_api.js

# Load extension in Chrome
# 1. Go to chrome://extensions/
# 2. Enable Developer Mode
# 3. Load unpacked → select 'extension' folder
```

## Controls

- **Next**: Skip to next random image
- **★ (Favorite)**: Bookmark current image
- **Dark**: Toggle dark mode
- **Keywords**: Add custom keywords to scrape
- **Favorites**: View and manage bookmarked images

## Image Quality

All images are now:
- Landscape orientation
- Minimum 1920x1080 pixels
- High resolution (originals, not thumbnails)
- Aesthetic/wallpaper optimized

## Tips

- Drag control panel to your preferred position
- Bookmark your favorite images for quick access
- Use specific keywords like "4k mountain wallpaper landscape"
- API must be running for live keyword scraping
- Reload extension cache after manual scraping
