"""
Development Tools
Helper utilities for development and debugging
"""

import json
import sys
from pathlib import Path
from collections import Counter


def analyze_cache(filepath="extension/data/pinterest_cache.json"):
    """Analyze cache file and print statistics"""
    cache_path = Path(filepath)

    if not cache_path.exists():
        print(f"Error: Cache file not found: {filepath}")
        return

    print("="*60)
    print(f"Cache Analysis: {filepath}")
    print("="*60)

    with open(cache_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"\n📊 Statistics:")
    print(f"  Total entries: {len(data)}")

    # Analyze URLs
    url_domains = []
    url_types = []
    has_media = 0
    has_url_field = 0

    for item in data:
        # Check structure
        if 'media' in item:
            has_media += 1
            url = item['media']
        elif 'url' in item:
            has_url_field += 1
            url = item.get('url', '')
        else:
            continue

        # Domain analysis
        if 'pinimg.com' in url:
            url_domains.append('pinimg.com')
        elif 'pinterest.com' in url:
            url_domains.append('pinterest.com')
        else:
            url_domains.append('other')

        # Type analysis
        if '/originals/' in url:
            url_types.append('original')
        elif any(size in url for size in ['/236x/', '/474x/', '/564x/', '/736x/']):
            url_types.append('thumbnail')
        else:
            url_types.append('unknown')

    print(f"\n🏗️ Structure:")
    print(f"  Items with 'media' field: {has_media}")
    print(f"  Items with 'url' field: {has_url_field}")

    print(f"\n🌐 Domains:")
    for domain, count in Counter(url_domains).items():
        print(f"  {domain}: {count}")

    print(f"\n📸 Image Quality:")
    for url_type, count in Counter(url_types).items():
        print(f"  {url_type}: {count}")

    # Check for potential issues
    print(f"\n⚠️ Potential Issues:")

    blob_urls = sum(1 for item in data if 'blob:' in str(item.get('media', '') or item.get('url', '')))
    if blob_urls > 0:
        print(f"  {blob_urls} blob URLs (will not work)")

    video_urls = sum(1 for item in data if 'video' in str(item.get('media', '') or item.get('url', '')))
    if video_urls > 0:
        print(f"  {video_urls} video URLs (may not load)")

    thumbnails = sum(1 for t in url_types if t == 'thumbnail')
    if thumbnails > 0:
        print(f"  {thumbnails} thumbnail URLs (consider upgrading with quick_fix.py)")

    print(f"\n✓ Analysis complete!")


def sample_entries(filepath="extension/data/pinterest_cache.json", count=3):
    """Display sample entries from cache"""
    cache_path = Path(filepath)

    if not cache_path.exists():
        print(f"Error: Cache file not found: {filepath}")
        return

    with open(cache_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print("="*60)
    print(f"Sample Entries from {filepath}")
    print("="*60)

    for i, item in enumerate(data[:count]):
        print(f"\n📌 Entry {i+1}:")
        print(json.dumps(item, indent=2))


def remove_duplicates(filepath="extension/data/pinterest_cache.json"):
    """Remove duplicate entries based on image URL"""
    cache_path = Path(filepath)

    if not cache_path.exists():
        print(f"Error: Cache file not found: {filepath}")
        return

    print(f"Removing duplicates from: {filepath}")

    # Backup original
    backup_path = cache_path.with_suffix('.backup.json')
    cache_path.rename(backup_path)
    print(f"  Backed up to: {backup_path}")

    with open(backup_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    original_count = len(data)
    print(f"  Original entries: {original_count}")

    # Remove duplicates
    seen_urls = set()
    unique_data = []

    for item in data:
        url = item.get('media') or item.get('url')
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_data.append(item)

    print(f"  Unique entries: {len(unique_data)}")
    print(f"  Removed: {original_count - len(unique_data)} duplicates")

    # Save
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(unique_data, f, indent=2, ensure_ascii=False)

    print(f"✓ Saved to: {filepath}")


def test_cache_structure():
    """Test if cache file has correct structure for extension"""
    filepath = "extension/data/pinterest_cache.json"
    cache_path = Path(filepath)

    print("="*60)
    print("Testing Cache Structure")
    print("="*60)

    if not cache_path.exists():
        print(f"\n✗ FAIL: Cache file not found: {filepath}")
        print("\n  Run: python pinterest_scraper.py")
        return False

    with open(cache_path, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"\n✗ FAIL: Invalid JSON: {e}")
            return False

    if not isinstance(data, list):
        print(f"\n✗ FAIL: Cache must be a JSON array, got {type(data)}")
        return False

    if len(data) == 0:
        print(f"\n✗ FAIL: Cache is empty")
        return False

    print(f"\n✓ Valid JSON array with {len(data)} entries")

    # Check first entry structure
    first_entry = data[0]
    required_fields = ['media', 'title', 'url']  # Old format
    new_fields = ['url', 'type', 'title', 'source']  # New format

    has_old_format = all(field in first_entry for field in ['media', 'title'])
    has_new_format = all(field in first_entry for field in ['url', 'type'])

    if has_old_format:
        print("✓ Using old format (media field) - will be auto-converted")
    elif has_new_format:
        print("✓ Using new format (url field)")
    else:
        print(f"⚠ Warning: Unexpected format. First entry: {first_entry}")

    # Check URL validity
    first_url = first_entry.get('media') or first_entry.get('url')
    if first_url:
        if 'pinimg.com' in first_url:
            print(f"✓ Valid Pinterest CDN URL")
        else:
            print(f"⚠ Warning: URL not from Pinterest CDN: {first_url}")

        if 'blob:' in first_url:
            print(f"✗ FAIL: Blob URL detected (will not work)")
            return False

        if '/originals/' in first_url:
            print(f"✓ Original quality URL")
        else:
            print(f"⚠ Thumbnail URL (consider running quick_fix.py)")

    print(f"\n✓ Cache structure is valid!")
    return True


def main():
    """Main CLI"""
    if len(sys.argv) < 2:
        print("Development Tools")
        print("\nUsage:")
        print("  python dev_tools.py analyze [filepath]    - Analyze cache statistics")
        print("  python dev_tools.py sample [filepath]     - Show sample entries")
        print("  python dev_tools.py dedup [filepath]      - Remove duplicates")
        print("  python dev_tools.py test                  - Test cache structure")
        return

    command = sys.argv[1]
    filepath = sys.argv[2] if len(sys.argv) > 2 else "extension/data/pinterest_cache.json"

    if command == "analyze":
        analyze_cache(filepath)
    elif command == "sample":
        sample_entries(filepath)
    elif command == "dedup":
        remove_duplicates(filepath)
    elif command == "test":
        test_cache_structure()
    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
