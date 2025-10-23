/**
 * Simple Node.js API to run Python scraper
 * Run this with: node scraper_api.js
 * Then the extension can make HTTP requests to scrape
 */

const express = require('express');
const { spawn } = require('child_process');
const cors = require('cors');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = 3456;

app.use(cors());
app.use(express.json());

// Endpoint to trigger scraping
app.post('/scrape', (req, res) => {
  const { keywords } = req.body;

  if (!keywords || !Array.isArray(keywords)) {
    return res.status(400).json({ error: 'Keywords array required' });
  }

  console.log('Starting scraper with keywords:', keywords);

  // Update the keywords in the scraper file
  const scraperPath = path.join(__dirname, 'pinterest_scraper.py');
  let scraperCode = fs.readFileSync(scraperPath, 'utf8');

  // Find and replace KEYWORDS array
  const keywordsStr = JSON.stringify(keywords, null, 8).replace(/\n/g, '\n        ');
  scraperCode = scraperCode.replace(
    /KEYWORDS = \[[^\]]*\]/s,
    `KEYWORDS = ${keywordsStr}`
  );

  fs.writeFileSync(scraperPath, scraperCode);

  // Run the scraper
  const python = spawn('python', ['pinterest_scraper.py']);

  let output = '';
  let errorOutput = '';

  python.stdout.on('data', (data) => {
    output += data.toString();
    console.log(data.toString());
  });

  python.stderr.on('data', (data) => {
    errorOutput += data.toString();
    console.error(data.toString());
  });

  python.on('close', (code) => {
    if (code === 0) {
      // Count images in cache
      try {
        const cache = JSON.parse(fs.readFileSync('extension/data/pinterest_cache.json', 'utf8'));
        res.json({
          success: true,
          count: cache.length,
          message: 'Scraping completed successfully'
        });
      } catch (err) {
        res.json({
          success: true,
          message: 'Scraping completed but could not read cache'
        });
      }
    } else {
      res.status(500).json({
        success: false,
        error: 'Scraper failed',
        output: errorOutput
      });
    }
  });
});

// Check if scraper API is running
app.get('/health', (req, res) => {
  res.json({ status: 'ok', message: 'Scraper API is running' });
});

app.listen(PORT, () => {
  console.log(`Scraper API running on http://localhost:${PORT}`);
  console.log('Extension can now trigger scraping via this API');
});
