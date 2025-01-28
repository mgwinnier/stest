import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import time
import random
import cv2
import numpy as np
from xvfbwrapper import Xvfb  # Simulates GUI on headless servers

# Directory to save screenshots
SCREENSHOT_DIR = "screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# Start a virtual display (for GitHub Actions)
vdisplay = Xvfb(width=1280, height=720)
vdisplay.start()

def jitter_mouse(driver, element, duration=8):
    """Simulate human-like mouse movements during a press-and-hold action."""
    action = ActionChains(driver)
    start_time = time.time()

    while time.time() - start_time < duration:
        offset_x = random.randint(-5, 5)
        offset_y = random.randint(-5, 5)
        action.move_to_element_with_offset(element, offset_x, offset_y).perform()
        time.sleep(random.uniform(0.1, 0.3))


def click_to_left_of_element(driver, element, offset=-180, wait_time=2):
    """Click slightly to the left of the given element and save a screenshot."""
    driver.execute_script("arguments[0].scrollIntoView();", element)
    location = element.location
    size = element.size

    click_x = location["x"] - offset
    click_y = location["y"] + (size["height"] // 2)

    print(f"Attempting to click at ({click_x}, {click_y}), slightly to the left of the element.")
    time.sleep(wait_time)

    screenshot = driver.get_screenshot_as_png()
    image = cv2.imdecode(np.frombuffer(screenshot, np.uint8), cv2.IMREAD_COLOR)
    cv2.circle(image, (int(click_x), int(click_y)), 10, (0, 0, 255), -1)
    screenshot_path = os.path.join(SCREENSHOT_DIR, f"click_attempt_{int(time.time())}.png")
    cv2.imwrite(screenshot_path, image)
    print(f"Saved click attempt visualization to {screenshot_path}")

    action = ActionChains(driver)
    action.move_by_offset(click_x - driver.execute_script("return window.scrollX;"),
                          click_y - driver.execute_script("return window.scrollY;")).click().perform()


def solve_captcha(driver):
    """Check for the accessibility button first, then solve CAPTCHA."""
    print("Checking for press-and-hold button...")

    try:
        captcha_element = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "px-captcha"))
        )
        print("Press-and-hold button detected. Attempting to click the accessibility button first...")

        # Click to the left of the CAPTCHA button
        click_to_left_of_element(driver, captcha_element, offset=-180, wait_time=2)
        print("Clicked accessibility button. Waiting for 'Press Again' button to appear...")

        time.sleep(3)
        try:
            press_again_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//button[contains(text(),'Press Again')]"))
            )
            print("Press Again button detected, clicking now...")
            press_again_button.click()
            time.sleep(3)
            print("Clicked Press Again button.")
            return True
        except:
            print("Press Again button not found after clicking accessibility button, trying default CAPTCHA resolution.")
    except:
        print("Press-and-hold button not detected, skipping accessibility button click.")

    print("Trying Press-and-Hold CAPTCHA...")
    try:
        captcha_element = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "px-captcha"))
        )
        print("Press-and-hold CAPTCHA detected, attempting to solve...")

        action = ActionChains(driver)
        action.click_and_hold(captcha_element).perform()
        jitter_mouse(driver, captcha_element, duration=random.uniform(6, 12))
        action.release(captcha_element).perform()
        time.sleep(3)

        if "Press & Hold to confirm" not in driver.page_source:
            print("CAPTCHA solved successfully.")
            return True
    except:
        print("Failed to solve CAPTCHA.")
    
    return False


def fetch_product_data(driver, url):
    """Fetch product data from the Total Wine website."""
    try:
        driver.get(url)

        try:
            product_name_element = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'h1[data-at="product-name-title"]'))
            )
            product_name = product_name_element.text.strip()
            print(f"Product detected: {product_name}, skipping CAPTCHA check.")
        except:
            product_name = None

        if not product_name:
            if not solve_captcha(driver):
                print("Failed to solve CAPTCHA, skipping this URL.")
                return None
            try:
                product_name_element = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'h1[data-at="product-name-title"]'))
                )
                product_name = product_name_element.text.strip()
            except:
                product_name = "Product name not found"

        stock_status = "Stock status not found"
        store_name = "Store name not found"
        try:
            stock_status = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-at="selected-inventorystatus-text"]'))
            ).text.strip()
        except:
            pass

        try:
            store_name = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'a[data-at="product-pickup-store-name"]'))
            ).text.strip()
        except:
            pass

        return {
            "product_name": product_name,
            "stock_status": stock_status,
            "store_name": store_name,
        }
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None


def main():
    options = uc.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--start-maximized")
    options.add_argument("--window-size=1280,720")

    driver = uc.Chrome(options=options)

    urls = [
        "https://www.totalwine.com/spirits/bourbon/small-batch-bourbon/stagg-bourbon/p/135217750?s=501&igrules=true",
        "https://www.totalwine.com/spirits/american-whiskey/rye-whiskey/colonel-eh-taylor-straight-rye/p/130861750?s=501&igrules=true",
    ]

    try:
        for url in urls:
            data = fetch_product_data(driver, url)
            if data:
                print(
                    f"**Product Name:** {data['product_name']}\n"
                    f"**Stock Status:** {data['stock_status']}\n"
                    f"**Store Name:** {data['store_name']}\n"
                    f"---------------------------------------"
                )
    finally:
        driver.quit()
        vdisplay.stop()


if __name__ == "__main__":
    main()
