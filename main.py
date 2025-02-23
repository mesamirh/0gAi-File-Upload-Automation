import os
import random
import requests
import time
import shutil
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import urlparse
import socket

class StorageScanAutomation:
    def __init__(self):
        """Initialize automation with project-specific browser profile"""
        self.website_url = "https://storagescan-newton.0g.ai/tool"
        self.project_dir = os.getcwd()
        self.download_dir = os.path.join(self.project_dir, "temp_images")
        self.browser_dir = os.path.join(self.project_dir, "browser_profiles")
        self.profile_dir = os.path.join(self.browser_dir, "automation_profile")
        self.transaction_delay = 60  # Default delay
        
        print("\n=== Storage Scan Automation Setup ===")
        if os.path.exists(self.profile_dir):
            print("✓ Existing profile detected - Your MetaMask setup will be restored")
        
        self.setup_directories()
        self.setup_browser()

    def initial_setup(self):
        """Handle first-time MetaMask setup"""
        try:
            print("\n=== Installing MetaMask Extension ===")
            self.driver.get("https://chromewebstore.google.com/detail/metamask/nkbihfbeogaeaoehlefnkodbefgpgknn")
            print("\nPlease complete these steps:")
            print("1. Install MetaMask extension")
            print("2. Set up your wallet (create new or import existing)")
            print("3. Once setup is complete, we'll proceed to the main website")
            input("\nPress Enter ONLY after MetaMask is fully set up...")
            
        except Exception as e:
            print(f"❌ Error during initial setup: {str(e)}")
            raise

    def setup_directories(self):
        """Create necessary directories if they don't exist"""
        if os.path.exists(self.download_dir):
            shutil.rmtree(self.download_dir)
        os.makedirs(self.download_dir)
        
        if not os.path.exists(self.browser_dir):
            os.makedirs(self.browser_dir)
        if not os.path.exists(self.profile_dir):
            os.makedirs(self.profile_dir)

    def cleanup_images(self):
        """Remove downloaded images"""
        if os.path.exists(self.download_dir):
            shutil.rmtree(self.download_dir)

    def setup_browser(self):
        """Setup Chrome browser with project-specific profile"""
        try:
            print("\nSetting up Chrome browser...")
            chrome_options = Options()
            
            print(f"Using profile directory: {self.profile_dir}")
            chrome_options.add_argument(f"user-data-dir={self.profile_dir}")
            
            # Basic Chrome options
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--start-maximized")
            chrome_options.add_argument("--disable-dev-shm-usage")
            
            # Remove automation flags
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Initialize WebDriver
            print("Initializing Chrome WebDriver...")
            self.driver = webdriver.Chrome(options=chrome_options)
            print("✓ Chrome browser launched successfully")
            
        except Exception as e:
            print(f"❌ Error setting up browser: {str(e)}")
            raise

    def download_random_images(self, num_images):
        """Download random images with preliminary checks"""
        if not self.is_internet_connected():
            raise Exception("❌ No internet connection available")
        
        if not self.verify_download_directory():
            raise Exception("❌ Cannot write to download directory")
        
        print(f"\nDownloading {num_images} random images...")
        images = []
        retry_count = 3  # Number of retries per image
        
        for i in range(num_images):
            success = False
            for attempt in range(retry_count):
                try:
                    print(f"Downloading image {i+1}/{num_images}...")
                    # Using Picsum Photos API to get random images
                    image_url = f"https://picsum.photos/800/600?random={i}"
                    response = requests.get(
                        image_url, 
                        timeout=10,
                        headers={'User-Agent': 'Mozilla/5.0'}
                    )
                    
                    if response.status_code == 200:
                        file_path = os.path.join(self.download_dir, f"image_{i}.jpg")
                        with open(file_path, "wb") as f:
                            f.write(response.content)
                        images.append(file_path)
                        print(f"✓ Image {i+1} downloaded successfully")
                        success = True
                        break
                    else:
                        print(f"⚠️  Attempt {attempt + 1}: Failed to download image {i+1}")
                        
                except requests.exceptions.RequestException as e:
                    print(f"⚠️  Attempt {attempt + 1}: Error downloading image {i+1}: {str(e)}")
                    time.sleep(1)
                    
                except Exception as e:
                    print(f"❌ Unexpected error downloading image {i+1}: {str(e)}")
                    break
            
            if not success:
                print(f"❌ Failed to download image {i+1} after {retry_count} attempts")
                choice = input("Enter 'r' to retry this image, or any other key to continue: ")
                if choice.lower() == 'r':
                    i -= 1
                    continue
        
        total_downloaded = len(images)
        if total_downloaded < num_images:
            print(f"\n⚠️  Warning: Only {total_downloaded} out of {num_images} images were downloaded")
            if total_downloaded == 0:
                raise Exception("No images were downloaded successfully")
        else:
            print(f"\n✓ Successfully downloaded all {num_images} images")
        
        return images

    def upload_images(self, image_paths):
        """Upload images with configurable delay"""
        print("\n🚀 Starting Upload Process\n")
        
        for idx, image_path in enumerate(image_paths, 1):
            try:
                print(f"📌 Processing Image {idx}/{len(image_paths)}")
                
                # Upload file
                print("  ⏳ Preparing file upload...")
                file_input = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
                )
                file_input.send_keys(image_path)
                print("  ✅ File ready")

                print("  ⏳ Initiating upload...")
                upload_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Upload')]"))
                )
                upload_button.click()
                print("  ✅ Upload started")

                # Handle MetaMask confirmation
                print("  ⏳ Waiting for MetaMask...")
                time.sleep(3)
                
                # Get current window handle
                original_window = self.driver.current_window_handle
                
                # Wait and switch to MetaMask popup
                WebDriverWait(self.driver, 20).until(lambda d: len(d.window_handles) > 1)
                metamask_window = [handle for handle in self.driver.window_handles 
                                  if handle != original_window][0]
                
                self.driver.switch_to.window(metamask_window)
                print("  👉 MetaMask popup detected")

                # Handle MetaMask confirmation with retry logic
                max_retries = 3
                for attempt in range(max_retries):
                    if self.click_metamask_confirm(original_window):
                        # Switch back to main window
                        self.driver.switch_to.window(original_window)
                        print("  ⏳ Processing upload...")
                        
                        try:
                            # Wait specifically for the success image with configured timeout
                            print(f"  ⏳ Waiting {self.transaction_delay} seconds for transaction completion...")
                            time.sleep(self.transaction_delay)
                            
                            success_element = WebDriverWait(self.driver, 30).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, 
                                    'img[src*="check-upload.3f48c9e8.svg"]'))
                            )
                        
                            if success_element.is_displayed():
                                print("  🎉 Upload completed successfully!")
                                
                                if idx < len(image_paths):
                                    print("\n  🔄 Refreshing page for next upload...")
                                    self.driver.refresh()
                                    time.sleep(3)
                                    print("  ✅ Page refreshed\n")
                                break
                            else:
                                raise Exception("Success image found but not visible")
                                
                        except Exception as e:
                            if attempt < max_retries - 1:
                                print(f"  ⚠️  Upload completion not detected: {str(e)}")
                                print("  🔄 Retrying...")
                                continue
                            raise Exception("Upload completion not detected after maximum retries")
                    else:
                        if attempt < max_retries - 1:
                            print("  ⚠️  Confirmation failed, retrying...")
                            time.sleep(2)
                            continue
                        raise Exception("Failed to confirm transaction after maximum retries")

            except Exception as e:
                print(f"\n  ❌ Error: {str(e)}")
                retry = input("  🔄 Retry this upload? (y/n): ")
                if retry.lower() == 'y':
                    idx -= 1
                    print("  ⏳ Refreshing page...")
                    self.driver.refresh()
                    time.sleep(3)
                    continue
                else:
                    break

        print("\n✨ Upload Process Complete!")
        print(f"📊 Successfully processed {len(image_paths)} images")

    def click_metamask_confirm(self, original_window):
        """Handle MetaMask confirmation with improved retry logic"""
        print("  ⏳ Looking for confirm button...")
        max_attempts = 3
        
        for attempt in range(max_attempts):
            try:
                time.sleep(5 + (attempt * 2))
                
                print(f"  🔍 Attempt {attempt + 1}/{max_attempts} to find confirm button...")
                result = self.driver.execute_script("""
                    const buttons = document.querySelectorAll('button');
                    for (const button of buttons) {
                        if (button.textContent.includes('Confirm') && 
                            button.className.includes('mm-button-primary')) {
                            console.log('Found confirm button:', button);
                            button.click();
                            return true;
                        }
                    }
                    console.log('No confirm button found');
                    return false;
                """)
                
                if result:
                    print(f"  ✓ Successfully clicked button with JavaScript (Attempt {attempt + 1})")
                    time.sleep(3)
                    return True
                else:
                    print(f"  ⚠️  Button not found on attempt {attempt + 1}")
                    if attempt < max_attempts - 1:
                        print("  🔄 Retrying...")
                        continue
                    
            except Exception as e:
                print(f"  ⚠️  Error on attempt {attempt + 1}: {str(e)}")
                if attempt < max_attempts - 1:
                    print("  🔄 Retrying...")
                    continue
        
        print("\n  ❌ Automatic confirmation failed after all attempts")
        print("  💡 Manual intervention required:")
        print("  1. Please check the MetaMask popup")
        print("  2. Click the confirm button manually")
        user_input = input("  Did you click confirm manually? (y/n): ")
        if user_input.lower() == 'y':
            time.sleep(2)
            return True
        
        return False

    def connect_wallet(self):
        """Wait for MetaMask connection button and click it"""
        print("\nAttempting to connect MetaMask wallet...")
        try:
            print("Looking for 'Connect Wallet' button...")
            connect_button = None
            possible_xpaths = [
                "//*[contains(text(), 'Connect Wallet')]",
                "//*[contains(text(), 'Connect wallet')]",
                "//*[contains(text(), 'connect wallet')]",
                "//button[contains(text(), 'Connect')]",
                "//div[contains(text(), 'Connect')]"
            ]
            
            for xpath in possible_xpaths:
                try:
                    connect_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, xpath))
                    )
                    if connect_button:
                        break
                except:
                    continue
            
            if not connect_button:
                print("❌ Connect wallet button not found!")
                return False
                
            print("✓ Found wallet connection button")
            print("Clicking connect button...")
            connect_button.click()
            time.sleep(2)
            
            print("\n=== IMPORTANT: MetaMask Connection Steps ===")
            print("1. Look for the MetaMask popup window")
            print("2. Click 'Connect' in the MetaMask popup")
            print("3. If prompted, select your accounts")
            print("4. Click 'Connect' to confirm")
            print("\nNote: You may need to switch to the MetaMask popup if it's not visible")
            
            return True
            
        except Exception as e:
            print(f"❌ Error during wallet connection: {str(e)}")
            print("\nTroubleshooting tips:")
            print("1. Make sure MetaMask is installed and set up")
            print("2. Check if the website is loaded completely")
            print("3. Try refreshing the page if the button doesn't appear")
            return False

    def is_internet_connected(self):
        """Check if internet connection is available"""
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            return True
        except OSError:
            return False

    def verify_download_directory(self):
        """Verify download directory exists and is writable"""
        try:
            if not os.path.exists(self.download_dir):
                os.makedirs(self.download_dir)
            test_file = os.path.join(self.download_dir, "test.txt")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            return True
        except Exception as e:
            print(f"❌ Error with download directory: {str(e)}")
            return False

    def run(self, num_images):
        """Main execution method with improved debugging output"""
        try:
            print("\n" + "="*50)
            print("🚀 STORAGE SCAN AUTOMATION STARTING")
            print("="*50)
            
            # Configure transaction delay
            print("\n📋 CONFIGURATION")
            print("----------------")
            while True:
                try:
                    delay = input("→ Enter transaction wait time in seconds [default: 60]: ").strip()
                    if not delay:
                        delay = 60
                    else:
                        delay = int(delay)
                    if delay > 0:
                        break
                    print("⚠️  Please enter a positive number")
                except ValueError:
                    print("⚠️  Please enter a valid number")
            
            print(f"✓ Transaction wait time: {delay} seconds")
            self.transaction_delay = delay
            
            # Navigation
            print("\n🌐 WEBSITE NAVIGATION")
            print("-------------------")
            print(f"→ URL: {self.website_url}")
            print("→ Loading page...")
            self.driver.get(self.website_url)
            time.sleep(5)
            print("✓ Page loaded")

            # Wallet Connection
            print("\n🦊 METAMASK CONNECTION")
            print("--------------------")
            print("Steps:")
            print("1. Open MetaMask extension")
            print("2. Connect your wallet to the website")
            print("3. Approve the connection")
            input("\n→ Press Enter once wallet is connected...")
            
            # Image Processing
            print("\n📸 IMAGE PROCESSING")
            print("----------------")
            print(f"→ Downloading {num_images} images...")
            images = self.download_random_images(num_images)
            
            # Upload Process
            print("\n📤 UPLOAD PROCESS")
            print("--------------")
            self.upload_images(images)

            # Completion
            print("\n" + "="*50)
            print("✨ AUTOMATION COMPLETED SUCCESSFULLY")
            print("="*50)
            input("\nPress Enter to close the browser...")

        except Exception as e:
            print("\n" + "="*50)
            print("❌ ERROR OCCURRED")
            print("="*50)
            print(f"Details: {str(e)}")
            raise
        
        finally:
            print("\n🧹 CLEANUP")
            print("--------")
            print("→ Removing temporary files...")
            self.cleanup_images()
            print("✓ Temporary images removed")
            print("→ Closing browser...")
            self.driver.quit()
            print("✓ Browser closed")

def main():
    print("\n=== Storage Scan Automation Tool ===")
    while True:
        try:
            num_images = int(input("\nHow many images would you like to upload? "))
            if num_images > 0:
                break
            print("Please enter a positive number.")
        except ValueError:
            print("Please enter a valid number.")

    automation = StorageScanAutomation()
    automation.run(num_images)

if __name__ == "__main__":
    main()