document.getElementById('next').addEventListener('click', () => {
  chrome.runtime.sendMessage({ type: 'next-image' }, (res) => {
    window.close(); // close popup, newtab will update if open
  });
});

document.getElementById('refreshCache').addEventListener('click', async () => {
  // Clear storage and force reload with proper normalization
  try {
    // Clear old cache
    await chrome.storage.local.remove(['cacheLoaded', 'pinterestCache', 'currentItem']);

    // Force background to reload
    chrome.runtime.reload();

    alert('Cache cleared! Extension will reload with fresh data.');
  } catch (err) {
    console.error(err);
    alert('Reload failed: ' + err.message);
  }
});

const darkCheckbox = document.getElementById('darkMode');
(async () => {
  const s = await chrome.storage.local.get(['darkMode']);
  darkCheckbox.checked = !!s.darkMode;
})();

darkCheckbox.addEventListener('change', async () => {
  await chrome.storage.local.set({ darkMode: darkCheckbox.checked });
  // tell open pages to update immediately
  chrome.runtime.sendMessage({ type: 'wallpaper-changed' });
  window.close();
});

// Display a random valid Pinterest image from cache
(async () => {
  try {
    let cache = await chrome.storage.local.get('pinterestCache');
    let data = cache.pinterestCache;

    if (!data || !Array.isArray(data) || data.length === 0) {
      // fallback: load bundled cache
      const url = chrome.runtime.getURL('data/pinterest_cache.json');
      const r = await fetch(url);
      data = await r.json();

      // Normalize entries
      data = data.map(item => {
        if (item.media && !item.url) {
          return {
            url: item.media,
            type: 'image',
            title: item.title || 'Aesthetic Image',
            source: 'Pinterest'
          };
        }
        return item;
      });
    }

    // Filter for valid image URLs (support both 'url' and 'media' fields)
    const validImages = data.filter(item => {
      const imgUrl = item.url || item.media;
      return (
        typeof imgUrl === 'string' &&
        !imgUrl.startsWith('blob:') &&
        !imgUrl.includes('video-thumbnails') &&
        /\.(jpg|jpeg|png|gif|webp)$/i.test(imgUrl.split('?')[0])
      );
    });

    const img = document.getElementById('themeImage');

    if (validImages.length > 0) {
      const randomIndex = Math.floor(Math.random() * validImages.length);
      const selectedItem = validImages[randomIndex];
      const imgUrl = selectedItem.url || selectedItem.media;

      img.src = imgUrl;
      img.onerror = () => {
        img.alt = 'Image failed to load';
        img.style.display = 'none';
      };
    } else {
      img.alt = 'No valid images found';
      img.style.display = 'none';
    }
  } catch (err) {
    console.error('Error loading popup image:', err);
    const img = document.getElementById('themeImage');
    img.alt = 'Error loading image';
    img.style.display = 'none';
  }
})();
