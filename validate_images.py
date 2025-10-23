"""
Image URL Validator
Validates Pinterest image URLs by checking if they're accessible
Removes dead/expired URLs from cache
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import List, Dict

try:
    import aiohttp
except ImportError:
    print("ERROR: aiohttp not installed. Run: pip install aiohttp")
    sys.exit(1)


class ImageValidator:
    """Validate image URLs and filter out inaccessible ones"""

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.session = None

    async def init_session(self):
        """Initialize HTTP session with realistic headers"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://www.pinterest.com/',
                'DNT': '1',
            }
        )

    async def check_url(self, url: str) -> bool:
        """Check if an image URL is accessible"""
        if not url or not isinstance(url, str):
            return False

        try:
            async with self.session.head(url, allow_redirects=True) as response:
                # Consider 200-299 and some 300s as valid
                if response.status < 400:
                    content_type = response.headers.get('Content-Type', '').lower()
                    # Verify it's actually an image
                    if 'image' in content_type:
                        return True

                # If HEAD fails, try GET for first few bytes
                async with self.session.get(url, allow_redirects=True) as response:
                    if response.status < 400:
                        content_type = response.headers.get('Content-Type', '').lower()
                        return 'image' in content_type

        except Exception as e:
            print(f"  ✗ Failed: {url[:80]}... ({type(e).__name__})")
            return False

        return False

    async def validate_cache(self, cache_file: str) -> List[Dict]:
        """Validate all URLs in cache file"""
        print(f"\nValidating image URLs in: {cache_file}")
        print("=" * 60)

        cache_path = Path(cache_file)
        if not cache_path.exists():
            print(f"ERROR: Cache file not found: {cache_file}")
            return []

        # Load cache
        with open(cache_path, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)

        print(f"Loaded {len(cache_data)} entries from cache")

        await self.init_session()

        valid_entries = []
        tasks = []

        # Create validation tasks
        for entry in cache_data:
            url = entry.get('media') or entry.get('url')
            if url:
                tasks.append(self.validate_entry(entry))

        # Run validations concurrently (in batches to avoid overwhelming server)
        batch_size = 10
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i + batch_size]
            results = await asyncio.gather(*batch)

            for entry, is_valid in results:
                if is_valid:
                    valid_entries.append(entry)
                    print(f"  ✓ Valid ({len(valid_entries)}/{len(cache_data)})")
                else:
                    print(f"  ✗ Invalid ({len(cache_data) - len(valid_entries)} removed)")

            # Small delay between batches
            await asyncio.sleep(0.5)

        await self.session.close()

        print("\n" + "=" * 60)
        print(f"Validation complete:")
        print(f"  Valid URLs: {len(valid_entries)}")
        print(f"  Invalid URLs removed: {len(cache_data) - len(valid_entries)}")
        print("=" * 60)

        return valid_entries

    async def validate_entry(self, entry: Dict) -> tuple:
        """Validate a single cache entry"""
        url = entry.get('media') or entry.get('url')
        is_valid = await self.check_url(url)
        return (entry, is_valid)

    def save_validated_cache(self, entries: List[Dict], output_file: str):
        """Save validated entries to file"""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)

        print(f"\n✓ Saved {len(entries)} valid entries to {output_file}")


async def main():
    """Main validator entry point"""
    print("=" * 60)
    print("Pinterest Image URL Validator")
    print("=" * 60)

    # Files to validate
    FILES_TO_VALIDATE = [
        "pinterest_cache.json",
        "extension/data/pinterest_cache.json"
    ]

    validator = ImageValidator(timeout=10)

    for cache_file in FILES_TO_VALIDATE:
        if not Path(cache_file).exists():
            print(f"Skipping {cache_file} (not found)")
            continue

        valid_entries = await validator.validate_cache(cache_file)

        if valid_entries:
            # Backup original
            backup_file = cache_file.replace('.json', '_backup.json')
            Path(cache_file).rename(backup_file)
            print(f"✓ Backed up original to {backup_file}")

            # Save validated cache
            validator.save_validated_cache(valid_entries, cache_file)

    print("\n✓ Validation complete!")


if __name__ == "__main__":
    asyncio.run(main())
