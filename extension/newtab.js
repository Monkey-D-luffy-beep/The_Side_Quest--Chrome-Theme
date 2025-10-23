// newtab logic:
// - load currentItem from chrome.storage
// - render image or video accordingly
// - compute quick dominant color and send to background to update theme
// - wire up "Next" and dark mode toggle
// - handle errors with fallback and retry logic

const mediaWrap = document.getElementById('media-wrap');
const nextBtn = document.getElementById('nextBtn');
const darkToggle = document.getElementById('darkToggle');
const credit = document.getElementById('credit');

let retryCount = 0;
const MAX_RETRIES = 3;

async function renderCurrent() {
  const s = await chrome.storage.local.get(['currentItem', 'darkMode']);
  const item = s.currentItem;
  const darkMode = s.darkMode || false;

  // Apply dark mode
  if (darkMode) {
    document.documentElement.classList.add('dark');
    darkToggle.checked = true;
  } else {
    document.documentElement.classList.remove('dark');
    darkToggle.checked = false;
  }

  mediaWrap.innerHTML = '';

  if (!item || !item.url) {
    mediaWrap.innerHTML = '<div class="placeholder">No images available. Click "Next" or open extension popup to load cache.</div>';
    return;
  }

  // item expected shape: { url: "...", type: "image"|"video", title: "...", source: "..." }
  const url = item.url;
  const type = item.type || guessType(url);

  // Show loading state
  mediaWrap.innerHTML = '<div class="loading">Loading aesthetic image...</div>';

  if (type === 'video') {
    renderVideo(url, item);
  } else {
    renderImage(url, item);
  }

  
}

function renderImage(url, item) {
  const img = document.createElement('img');
  img.id = 'bg-img';
  img.alt = item.title || 'Aesthetic Background';

  img.addEventListener('load', () => {
    mediaWrap.innerHTML = '';
    mediaWrap.appendChild(img);
    retryCount = 0; // Reset retry count on success

    // Try to sample color, but don't fail if CORS blocks it
    try {
      sampleColorFromImage(img);
    } catch (err) {
      console.warn('Color sampling failed (expected with CORS):', err);
    }
  });

  img.addEventListener('error', async () => {
    console.error('Image failed to load:', url);

    if (retryCount < MAX_RETRIES) {
      retryCount++;
      console.log(`Retrying... (${retryCount}/${MAX_RETRIES})`);

      // Try next image automatically
      setTimeout(() => {
        chrome.runtime.sendMessage({ type: 'next-image' });
      }, 1000);
    } else {
      mediaWrap.innerHTML = '<div class="error">Failed to load image. <button id="retry-btn">Try Next Image</button></div>';
      document.getElementById('retry-btn').addEventListener('click', () => {
        retryCount = 0;
        chrome.runtime.sendMessage({ type: 'next-image' });
      });
    }
  });

  // Don't use crossOrigin for Pinterest images to avoid CORS errors
  // This means color sampling won't work, but images will load
  img.src = url;
}

function renderVideo(url, item) {
  const v = document.createElement('video');
  v.id = 'bg-video';
  v.autoplay = true;
  v.loop = true;
  v.muted = true;
  v.playsInline = true;

  v.addEventListener('loadeddata', () => {
    mediaWrap.innerHTML = '';
    mediaWrap.appendChild(v);
    retryCount = 0;

    try {
      sampleColorFromVideo(v);
    } catch (err) {
      console.warn('Video color sampling failed:', err);
    }
  });

  v.addEventListener('error', async () => {
    console.error('Video failed to load:', url);

    if (retryCount < MAX_RETRIES) {
      retryCount++;
      setTimeout(() => {
        chrome.runtime.sendMessage({ type: 'next-image' });
      }, 1000);
    } else {
      mediaWrap.innerHTML = '<div class="error">Failed to load video. <button id="retry-btn">Try Next Image</button></div>';
      document.getElementById('retry-btn').addEventListener('click', () => {
        retryCount = 0;
        chrome.runtime.sendMessage({ type: 'next-image' });
      });
    }
  });

  v.src = url;
}

function guessType(url) {
  const l = url.split('?')[0].toLowerCase();
  if (l.endsWith('.mp4') || l.endsWith('.webm')) return 'video';
  return 'image';
}

async function sampleColorFromImage(img) {
  // Note: Color sampling will fail due to CORS restrictions on Pinterest images
  // This is expected behavior - we prioritize image loading over theme colors
  try {
    const color = getAverageColorFromImage(img, 16);
    if (color) {
      chrome.runtime.sendMessage({ type: 'update-theme', color });
    }
  } catch (err) {
    // Silent fail - CORS restrictions are expected
    console.log('Color sampling skipped due to CORS');
  }
}

function sampleColorFromVideo(video) {
  try {
    // grab current frame
    const canvas = document.createElement('canvas');
    canvas.width = 16;
    canvas.height = 16;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const data = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
    const avg = averageRGBAFromImageData(data);
    chrome.runtime.sendMessage({ type: 'update-theme', color: avg });
  } catch (err) {
    console.warn('video sampling failed', err);
  }
}

function getAverageColorFromImage(img, size = 16) {
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d');
  ctx.drawImage(img, 0, 0, size, size);
  const data = ctx.getImageData(0, 0, size, size).data;
  return averageRGBAFromImageData(data);
}

function averageRGBAFromImageData(data) {
  let r = 0,
    g = 0,
    b = 0,
    count = 0;
  for (let i = 0; i < data.length; i += 4) {
    const alpha = data[i + 3] / 255;
    if (alpha < 0.2) continue; // skip mostly-transparent pixels
    r += data[i];
    g += data[i + 1];
    b += data[i + 2];
    count++;
  }
  if (count === 0) count = 1;
  return { r: Math.round(r / count), g: Math.round(g / count), b: Math.round(b / count) };
}

// UI wiring
nextBtn.addEventListener('click', () => {
  chrome.runtime.sendMessage({ type: 'next-image' }, (res) => {
    // background will set storage and send wallpaper-changed; listen for that instead
  });
});

// reflect dark toggle changes
darkToggle.addEventListener('change', async () => {
  const isDark = darkToggle.checked;
  await chrome.storage.local.set({ darkMode: isDark });
  if (isDark) document.documentElement.classList.add('dark');
  else document.documentElement.classList.remove('dark');
});

// respond to wallpaper-changed message
chrome.runtime.onMessage.addListener((msg, sender) => {
  if (msg && msg.type === 'wallpaper-changed') {
    renderCurrent();
  }
});

// Draggable controls
let isDragging = false;
let currentX;
let currentY;
let initialX;
let initialY;
let xOffset = 0;
let yOffset = 0;

const controls = document.getElementById('controls');
const dragHandle = document.querySelector('.drag-handle');

// Load saved position
chrome.storage.local.get(['controlsPosition'], (result) => {
  if (result.controlsPosition) {
    controls.style.left = result.controlsPosition.x + 'px';
    controls.style.bottom = result.controlsPosition.y + 'px';
    controls.style.transform = 'none';
  }
});

dragHandle.addEventListener('mousedown', dragStart);
document.addEventListener('mousemove', drag);
document.addEventListener('mouseup', dragEnd);

function dragStart(e) {
  initialX = e.clientX - xOffset;
  initialY = e.clientY - yOffset;

  if (e.target === dragHandle) {
    isDragging = true;
    controls.classList.add('dragging');
  }
}

function drag(e) {
  if (isDragging) {
    e.preventDefault();
    currentX = e.clientX - initialX;
    currentY = e.clientY - initialY;
    xOffset = currentX;
    yOffset = currentY;

    controls.style.transform = `translate(${currentX}px, ${currentY}px)`;
  }
}

function dragEnd(e) {
  if (isDragging) {
    initialX = currentX;
    initialY = currentY;
    isDragging = false;
    controls.classList.remove('dragging');

    // Save position
    const rect = controls.getBoundingClientRect();
    chrome.storage.local.set({
      controlsPosition: {
        x: rect.left,
        y: window.innerHeight - rect.bottom
      }
    });
  }
}

// Favorites functionality
const favoriteBtn = document.getElementById('favoriteBtn');
const favoritesBtn = document.getElementById('favoritesBtn');
const favoritesModal = document.getElementById('favoritesModal');
const closeFavoritesBtn = document.getElementById('closeFavoritesBtn');
const favoritesGrid = document.getElementById('favoritesGrid');

async function checkIfFavorited() {
  const s = await chrome.storage.local.get(['currentItem', 'favorites']);
  const currentItem = s.currentItem;
  const favorites = s.favorites || [];

  if (currentItem && favorites.some(f => f.url === currentItem.url)) {
    favoriteBtn.classList.add('favorited');
  } else {
    favoriteBtn.classList.remove('favorited');
  }
}

favoriteBtn.addEventListener('click', async () => {
  const s = await chrome.storage.local.get(['currentItem', 'favorites']);
  const currentItem = s.currentItem;
  let favorites = s.favorites || [];

  if (!currentItem) return;

  const index = favorites.findIndex(f => f.url === currentItem.url);

  if (index !== -1) {
    // Remove from favorites
    favorites.splice(index, 1);
    favoriteBtn.classList.remove('favorited');
  } else {
    // Add to favorites
    favorites.push(currentItem);
    favoriteBtn.classList.add('favorited');
  }

  await chrome.storage.local.set({ favorites });
});

favoritesBtn.addEventListener('click', async () => {
  const s = await chrome.storage.local.get(['favorites']);
  const favorites = s.favorites || [];

  favoritesGrid.innerHTML = '';

  if (favorites.length === 0) {
    favoritesGrid.innerHTML = '<p style="text-align: center; color: var(--text); opacity: 0.6;">No favorites yet. Click ★ to bookmark images.</p>';
  } else {
    favorites.forEach((fav, index) => {
      const item = document.createElement('div');
      item.className = 'favorite-item';
      item.innerHTML = `
        <img src="${fav.url}" alt="${fav.title}">
        <button class="remove-fav" data-index="${index}">×</button>
      `;

      item.querySelector('img').addEventListener('click', async () => {
        await chrome.storage.local.set({ currentItem: fav });
        favoritesModal.classList.remove('show');
        renderCurrent();
      });

      item.querySelector('.remove-fav').addEventListener('click', async (e) => {
        e.stopPropagation();
        const s = await chrome.storage.local.get(['favorites']);
        const favs = s.favorites || [];
        favs.splice(index, 1);
        await chrome.storage.local.set({ favorites: favs });
        favoritesBtn.click(); // Refresh the grid
      });

      favoritesGrid.appendChild(item);
    });
  }

  favoritesModal.classList.add('show');
});

closeFavoritesBtn.addEventListener('click', () => {
  favoritesModal.classList.remove('show');
});

// Keyword modal functionality
const keywordBtn = document.getElementById('keywordBtn');
const keywordModal = document.getElementById('keywordModal');
const keywordInput = document.getElementById('keywordInput');
const scrapeBtn = document.getElementById('scrapeBtn');
const cancelBtn = document.getElementById('cancelBtn');
const scrapeStatus = document.getElementById('scrapeStatus');

keywordBtn.addEventListener('click', () => {
  keywordModal.classList.add('show');
  keywordInput.focus();
});

cancelBtn.addEventListener('click', () => {
  keywordModal.classList.remove('show');
});

scrapeBtn.addEventListener('click', async () => {
  const keywords = keywordInput.value.trim();

  if (!keywords) {
    showScrapeStatus('Please enter at least one keyword', 'error');
    return;
  }

  showScrapeStatus('Scraping new images... This will take a few minutes.', 'info');
  scrapeBtn.disabled = true;

  const keywordList = keywords.split(/[,\n]+/).map(k => k.trim()).filter(k => k);

  try {
    const response = await fetch('http://localhost:3456/scrape', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ keywords: keywordList })
    });

    if (response.ok) {
      const data = await response.json();
      if (data.success) {
        showScrapeStatus(`Success! Scraped ${data.count} landscape HD images. Click popup "Reload Cache" to see them.`, 'success');
        setTimeout(() => {
          keywordModal.classList.remove('show');
          keywordInput.value = '';
        }, 5000);
      } else {
        showScrapeStatus('Scraping failed: ' + (data.error || 'Unknown error'), 'error');
      }
    } else {
      throw new Error('API not responding');
    }
  } catch (err) {
    showScrapeStatus('Scraper API not running. Run: node scraper_api.js first, or manually update pinterest_scraper.py', 'error');
  }

  scrapeBtn.disabled = false;
});

function showScrapeStatus(message, type) {
  scrapeStatus.textContent = message;
  scrapeStatus.className = 'show ' + type;
}

// Settings functionality
const settingsBtn = document.getElementById('settingsBtn');
const settingsModal = document.getElementById('settingsModal');
const rotationInterval = document.getElementById('rotationInterval');
const autoChangeEnabled = document.getElementById('autoChangeEnabled');
const saveSettingsBtn = document.getElementById('saveSettingsBtn');
const cancelSettingsBtn = document.getElementById('cancelSettingsBtn');

settingsBtn.addEventListener('click', async () => {
  // Load current settings
  const settings = await chrome.storage.local.get(['rotationInterval', 'autoChangeEnabled']);
  rotationInterval.value = settings.rotationInterval || '60';
  autoChangeEnabled.checked = settings.autoChangeEnabled !== false;
  settingsModal.classList.add('show');
});

cancelSettingsBtn.addEventListener('click', () => {
  settingsModal.classList.remove('show');
});

saveSettingsBtn.addEventListener('click', async () => {
  const interval = parseInt(rotationInterval.value);
  const enabled = autoChangeEnabled.checked;

  await chrome.storage.local.set({
    rotationInterval: interval,
    autoChangeEnabled: enabled
  });

  // Tell background to update alarm
  chrome.runtime.sendMessage({
    type: 'update-rotation-interval',
    interval: interval,
    enabled: enabled
  });

  settingsModal.classList.remove('show');


});

// Close modals when clicking outside
[keywordModal, favoritesModal, settingsModal].forEach(modal => {
  modal.addEventListener('click', (e) => {
    if (e.target === modal) {
      modal.classList.remove('show');
    }
  });
});

// Check if current image is favorited on load
checkIfFavorited();

// initial render
renderCurrent();
