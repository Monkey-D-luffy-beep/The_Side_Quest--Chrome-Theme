// background service worker
// responsibilities:
// - on install/start: load local cache into storage if not present
// - set alarm for periodic wallpaper rotation
// - accept messages: "next-image" to pick a new image now, "update-theme" to run chrome.theme.update
// - validate image URLs and provide fallback handling

const CACHE_PATH = 'data/pinterest_cache.json';
const ALARM_NAME = 'rotate-wallpaper';
const DEFAULT_PERIOD_MINUTES = 60; // rotate every 60 minutes

// Normalize data structure: convert old format to new format
function normalizeEntry(entry) {
  // Support both old format {media, title, url} and new format {url, type, title, source}
  if (entry.media) {
    // Old format: has 'media' field
    return {
      url: entry.media,
      type: guessType(entry.media),
      title: entry.title || 'Aesthetic Image',
      source: entry.url || 'Pinterest'  // The 'url' field in old format is Pinterest page URL
    };
  }

  // Already in new format or needs url field
  if (!entry.url) {
    console.warn('Entry missing both media and url field:', entry);
    return null;
  }

  return {
    url: entry.url,
    type: entry.type || guessType(entry.url),
    title: entry.title || 'Aesthetic Image',
    source: entry.source || 'Pinterest'
  };
}

function guessType(url) {
  if (!url) return 'image';
  const l = url.split('?')[0].toLowerCase();
  if (l.endsWith('.mp4') || l.endsWith('.webm') || l.endsWith('.mov')) return 'video';
  return 'image';
}

function isValidImageUrl(url) {
  if (!url || typeof url !== 'string') return false;
  if (url.startsWith('blob:')) return false;
  if (url.includes('video-thumbnails')) return false;
  const validExtensions = /\.(jpg|jpeg|png|gif|webp|mp4|webm)$/i;
  const validDomain = /pinimg\.com|pinterest\.com/i;
  return validExtensions.test(url.split('?')[0]) && validDomain.test(url);
}

async function loadCacheIfMissing() {
  const s = await chrome.storage.local.get(['cacheLoaded', 'pinterestCache']);
  if (!s.cacheLoaded || !s.pinterestCache) {
    try {
      const url = chrome.runtime.getURL(CACHE_PATH);
      const res = await fetch(url);
      const data = await res.json();

      console.log('Raw cache loaded:', data.length, 'entries');

      // Normalize all entries and filter out invalid URLs
      const normalizedData = data
        .map(normalizeEntry)
        .filter(entry => entry !== null && isValidImageUrl(entry.url));

      console.log('After normalization and validation:', normalizedData.length, 'valid entries');

      // Debug: show first normalized entry
      if (normalizedData.length > 0) {
        console.log('Sample normalized entry:', JSON.stringify(normalizedData[0], null, 2));
      }

      if (normalizedData.length === 0) {
        console.error('No valid images found in cache! Check cache file format.');
        return;
      }

      await chrome.storage.local.set({
        pinterestCache: normalizedData,
        cacheLoaded: true
      });
      console.log('Pinterest cache loaded successfully:', normalizedData.length, 'images');
    } catch (err) {
      console.error('Failed to load cache:', err);
    }
  }
}

async function pickAndSetRandomImage() {
  const s = await chrome.storage.local.get(['pinterestCache']);
  const cache = s.pinterestCache || [];

  if (!cache || cache.length === 0) {
    console.warn('No images in cache. Please reload the extension or check cache file.');
    return;
  }

  // Cache is already validated and normalized, just pick one
  const idx = Math.floor(Math.random() * cache.length);
  const entry = cache[idx];

  console.log('Picked image:', idx, '/', cache.length, '-', entry.url);

  // store chosen item and the timestamp
  await chrome.storage.local.set({
    currentItem: entry,
    currentIndex: idx,
    lastUpdated: Date.now()
  });

  // notify open pages (newtab) to refresh immediately
  try {
    await chrome.runtime.sendMessage({ type: 'wallpaper-changed', item: entry });
  } catch (err) {
    // Tab might not be open, ignore error
    console.log('No tabs listening for wallpaper change');
  }
}

chrome.runtime.onInstalled.addListener(async (details) => {
  // Force reload cache on update/install to ensure we have correct format
  if (details.reason === 'update' || details.reason === 'install') {
    console.log('Extension installed/updated - forcing cache reload');
    await chrome.storage.local.remove(['cacheLoaded', 'pinterestCache', 'currentItem']);
  }

  await loadCacheIfMissing();
  // create periodic alarm
  chrome.alarms.create(ALARM_NAME, { periodInMinutes: DEFAULT_PERIOD_MINUTES });
  // pick initial image
  await pickAndSetRandomImage();
});

chrome.runtime.onStartup.addListener(async () => {
  await loadCacheIfMissing();
  chrome.alarms.create(ALARM_NAME, { periodInMinutes: DEFAULT_PERIOD_MINUTES });
});

chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === ALARM_NAME) {
    await pickAndSetRandomImage();
  }
});

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg && msg.type === 'next-image') {
    pickAndSetRandomImage().then(() => sendResponse({ ok: true }));
    return true;
  }

  if (msg && msg.type === 'update-theme') {
    const color = msg.color;
    if (!color) {
      sendResponse({ ok: false, error: 'no color' });
      return;
    }
    let hex;
    if (typeof color === 'string') hex = color;
    else if (color.r !== undefined) hex = rgbToHex(color.r, color.g, color.b);
    else hex = '#222222';

    try {
      chrome.theme.update({
        colors: {
          frame: hex,
          toolbar: hex,
          tab_background_text: '#ffffff'
        }
      });
      sendResponse({ ok: true });
    } catch (err) {
      console.error('theme update failed', err);
      sendResponse({ ok: false, error: err.message });
    }
    return true;
  }

  if (msg && msg.type === 'scrape-keywords') {
    // Handle scraping request
    const keywords = msg.keywords;
    console.log('Received scrape request for keywords:', keywords);

    // Note: Extension can't directly run Python scraper
    // User needs to manually run: python pinterest_scraper.py with their keywords
    // For now, just provide instructions
    sendResponse({
      success: false,
      error: 'Please run the scraper manually: python pinterest_scraper.py',
      instructions: 'Update the KEYWORDS list in pinterest_scraper.py with your keywords and run it.'
    });

    // Open a notification tab with instructions
    chrome.tabs.create({
      url: chrome.runtime.getURL('scrape_instructions.html'),
      active: false
    });

    return true;
  }
});

function rgbToHex(r, g, b) {
  return (
    '#' +
    [r, g, b]
      .map((x) => {
        const s = Math.max(0, Math.min(255, Math.round(x))).toString(16);
        return s.length === 1 ? '0' + s : s;
      })
      .join('')
  );
}
