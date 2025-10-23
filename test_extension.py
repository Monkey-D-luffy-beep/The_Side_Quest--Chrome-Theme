"""
Extension Testing Script
Verifies the extension is ready to load
"""

import json
import sys
from pathlib import Path


class ExtensionTester:
    """Test extension files and configuration"""

    def __init__(self):
        self.errors = []
        self.warnings = []
        self.tests_passed = 0
        self.tests_total = 0

    def test(self, name, condition, error_msg=None, warning_msg=None):
        """Run a test and track results"""
        self.tests_total += 1
        print(f"\n[{self.tests_total}] Testing: {name}")

        if condition:
            self.tests_passed += 1
            print("  ✓ PASS")
            return True
        else:
            if error_msg:
                self.errors.append(error_msg)
                print(f"  ✗ FAIL: {error_msg}")
            elif warning_msg:
                self.warnings.append(warning_msg)
                print(f"  ⚠ WARNING: {warning_msg}")
            return False

    def test_file_exists(self, filepath, required=True):
        """Test if a file exists"""
        path = Path(filepath)
        name = f"File exists: {filepath}"

        if required:
            self.test(
                name,
                path.exists(),
                f"Required file missing: {filepath}"
            )
        else:
            self.test(
                name,
                path.exists(),
                warning_msg=f"Optional file missing: {filepath}"
            )

        return path.exists()

    def test_manifest(self):
        """Test manifest.json"""
        filepath = "extension/manifest.json"

        if not self.test_file_exists(filepath):
            return

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                manifest = json.load(f)

            # Check required fields
            required_fields = [
                "manifest_version",
                "name",
                "version",
                "permissions",
                "background",
                "chrome_url_overrides"
            ]

            for field in required_fields:
                self.test(
                    f"Manifest has '{field}'",
                    field in manifest,
                    f"Missing required field in manifest: {field}"
                )

            # Check manifest version
            self.test(
                "Manifest version 3",
                manifest.get("manifest_version") == 3,
                "Must use manifest version 3"
            )

            # Check CSP
            csp = manifest.get("content_security_policy", {})
            if isinstance(csp, dict):
                ext_pages = csp.get("extension_pages", "")
                self.test(
                    "CSP allows HTTPS images",
                    "https:" in ext_pages and "img-src" in ext_pages,
                    warning_msg="CSP may not allow external images"
                )

            # Check permissions
            perms = manifest.get("permissions", [])
            required_perms = ["storage", "alarms"]

            for perm in required_perms:
                self.test(
                    f"Has permission: {perm}",
                    perm in perms,
                    f"Missing permission: {perm}"
                )

        except json.JSONDecodeError as e:
            self.test(
                "Valid JSON in manifest",
                False,
                f"Invalid JSON in manifest.json: {e}"
            )

    def test_cache(self):
        """Test Pinterest cache"""
        filepath = "extension/data/pinterest_cache.json"

        if not self.test_file_exists(filepath):
            self.errors.append("Run: python pinterest_scraper.py")
            return

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                cache = json.load(f)

            # Check it's an array
            self.test(
                "Cache is JSON array",
                isinstance(cache, list),
                "Cache must be a JSON array"
            )

            if not isinstance(cache, list):
                return

            # Check not empty
            self.test(
                "Cache has entries",
                len(cache) > 0,
                "Cache is empty - run pinterest_scraper.py"
            )

            if len(cache) == 0:
                return

            # Check sufficient entries
            self.test(
                "Cache has 10+ entries",
                len(cache) >= 10,
                warning_msg=f"Only {len(cache)} entries (recommend 50+)"
            )

            # Check first entry structure
            first = cache[0]
            has_media = "media" in first
            has_url = "url" in first

            self.test(
                "Entries have image URL",
                has_media or has_url,
                "Entries missing 'media' or 'url' field"
            )

            # Check URL validity
            url = first.get("media") or first.get("url")
            if url:
                self.test(
                    "URL is from Pinterest",
                    "pinimg.com" in url or "pinterest.com" in url,
                    warning_msg=f"URL not from Pinterest: {url}"
                )

                self.test(
                    "URL is not blob",
                    "blob:" not in url,
                    "Cache contains blob URLs (won't work)"
                )

                self.test(
                    "URL is original quality",
                    "/originals/" in url,
                    warning_msg="URLs are thumbnails - run quick_fix.py"
                )

        except json.JSONDecodeError as e:
            self.test(
                "Valid JSON in cache",
                False,
                f"Invalid JSON in cache: {e}"
            )

    def test_extension_files(self):
        """Test extension files exist"""
        required_files = [
            "extension/background.js",
            "extension/newtab.html",
            "extension/newtab.js",
            "extension/popup.html",
            "extension/popup.js",
            "extension/styles.css",
        ]

        for filepath in required_files:
            self.test_file_exists(filepath, required=True)

    def test_icons(self):
        """Test icon files"""
        icon_files = [
            "extension/icons/icon16.png",
            "extension/icons/icon48.png",
            "extension/icons/icon128.png",
        ]

        for filepath in icon_files:
            self.test_file_exists(filepath, required=False)

    def test_python_tools(self):
        """Test Python tools exist"""
        tools = [
            "pinterest_scraper.py",
            "validate_images.py",
            "quick_fix.py",
            "dev_tools.py",
            "requirements.txt",
        ]

        for filepath in tools:
            self.test_file_exists(filepath, required=False)

    def run_all_tests(self):
        """Run all tests"""
        print("="*60)
        print("Extension Test Suite")
        print("="*60)

        self.test_manifest()
        self.test_extension_files()
        self.test_cache()
        self.test_icons()
        self.test_python_tools()

        # Print summary
        print("\n" + "="*60)
        print("Test Summary")
        print("="*60)

        print(f"\nTests passed: {self.tests_passed}/{self.tests_total}")

        if self.errors:
            print(f"\n❌ Errors ({len(self.errors)}):")
            for i, error in enumerate(self.errors, 1):
                print(f"  {i}. {error}")

        if self.warnings:
            print(f"\n⚠️  Warnings ({len(self.warnings)}):")
            for i, warning in enumerate(self.warnings, 1):
                print(f"  {i}. {warning}")

        if not self.errors:
            print("\n✓ Extension is ready to load!")
            print("\nNext steps:")
            print("  1. Open Chrome → chrome://extensions/")
            print("  2. Enable 'Developer mode'")
            print("  3. Click 'Load unpacked'")
            print("  4. Select the 'extension' folder")
            print("  5. Open a new tab to test!")
        else:
            print("\n✗ Fix errors before loading extension")
            sys.exit(1)


def main():
    """Run tests"""
    tester = ExtensionTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()
