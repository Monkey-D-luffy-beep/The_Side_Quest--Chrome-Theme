"""
Setup Script for Pinterest Aesthetic Extension
Handles initial setup and configuration
"""

import subprocess
import sys
from pathlib import Path


def check_python_version():
    """Ensure Python version is compatible"""
    if sys.version_info < (3, 8):
        print("ERROR: Python 3.8 or higher is required")
        sys.exit(1)
    print(f"✓ Python {sys.version_info.major}.{sys.version_info.minor} detected")


def install_dependencies():
    """Install required Python packages"""
    print("\n📦 Installing Python dependencies...")

    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ])
        print("✓ Dependencies installed successfully")
    except subprocess.CalledProcessError:
        print("✗ Failed to install dependencies")
        return False

    return True


def install_playwright_browsers():
    """Install Playwright browsers"""
    print("\n🌐 Installing Playwright browsers...")

    try:
        subprocess.check_call([
            sys.executable, "-m", "playwright", "install", "chromium"
        ])
        print("✓ Playwright browsers installed")
    except subprocess.CalledProcessError:
        print("✗ Failed to install Playwright browsers")
        return False

    return True


def check_extension_structure():
    """Verify extension files exist"""
    print("\n📁 Checking extension structure...")

    required_files = [
        "extension/manifest.json",
        "extension/background.js",
        "extension/newtab.html",
        "extension/newtab.js",
        "extension/popup.html",
        "extension/popup.js",
        "extension/styles.css",
    ]

    missing = []
    for file in required_files:
        if not Path(file).exists():
            missing.append(file)

    if missing:
        print("✗ Missing extension files:")
        for file in missing:
            print(f"  - {file}")
        return False

    print("✓ All extension files present")
    return True


def create_data_directory():
    """Ensure data directory exists"""
    data_dir = Path("extension/data")
    data_dir.mkdir(parents=True, exist_ok=True)
    print("✓ Data directory created")


def run_scraper():
    """Ask user if they want to run scraper now"""
    print("\n" + "="*60)
    print("Setup Complete!")
    print("="*60)

    response = input("\nWould you like to scrape Pinterest images now? (y/n): ")

    if response.lower() in ['y', 'yes']:
        print("\n🔍 Running Pinterest scraper...")
        print("This may take a few minutes...\n")

        try:
            subprocess.check_call([sys.executable, "pinterest_scraper.py"])
            print("\n✓ Scraping completed successfully!")

            # Ask about validation
            validate = input("\nValidate image URLs? (recommended) (y/n): ")
            if validate.lower() in ['y', 'yes']:
                print("\n✓ Validating URLs...")
                subprocess.check_call([sys.executable, "validate_images.py"])

        except subprocess.CalledProcessError:
            print("\n✗ Scraping failed. You can run it manually later:")
            print("  python pinterest_scraper.py")
    else:
        print("\n📝 You can run the scraper later with:")
        print("  python pinterest_scraper.py")


def print_next_steps():
    """Print instructions for loading extension"""
    print("\n" + "="*60)
    print("Next Steps - Load Extension in Chrome:")
    print("="*60)
    print("\n1. Open Chrome and go to: chrome://extensions/")
    print("2. Enable 'Developer mode' (toggle in top-right)")
    print("3. Click 'Load unpacked'")
    print(f"4. Select this folder: {Path('extension').absolute()}")
    print("5. Open a new tab to see your aesthetic background!")
    print("\n" + "="*60)


def main():
    """Main setup flow"""
    print("="*60)
    print("Pinterest Aesthetic Extension - Setup")
    print("="*60)

    # Run setup steps
    check_python_version()

    if not install_dependencies():
        print("\n✗ Setup failed at dependency installation")
        sys.exit(1)

    if not install_playwright_browsers():
        print("\n✗ Setup failed at Playwright installation")
        sys.exit(1)

    if not check_extension_structure():
        print("\n✗ Setup failed: Extension files missing")
        sys.exit(1)

    create_data_directory()

    # Optional scraping
    run_scraper()

    # Final instructions
    print_next_steps()


if __name__ == "__main__":
    main()
