import os
import re
import json
import time
import smtplib
from email.mime.text import MIMEText

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

from bs4 import BeautifulSoup
from plyer import notification

##############################################################################
# CONFIGURATION
##############################################################################

FLIPKART_URL = input("Enter Flipkart Product URL: ").strip()

CHECK_INTERVAL = 3600  # 1 hour

EMAIL_ALERTS = True

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "your_email@gmail.com"
SENDER_PASSWORD = "your_app_password"
RECEIVER_EMAIL = "receiver@gmail.com"

PRICE_FILE = "price_data.json"

##############################################################################
# UTILITIES
##############################################################################

def send_email(subject, body):
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = SENDER_EMAIL
        msg["To"] = RECEIVER_EMAIL

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()

        print("Email sent")

    except Exception as e:
        print("Email error:", e)


def desktop_notification(title, message):
    try:
        notification.notify(
            title=title,
            message=message,
            timeout=15
        )
    except Exception as e:
        print("Notification error:", e)


def load_previous_price():
    if not os.path.exists(PRICE_FILE):
        return None

    try:
        with open(PRICE_FILE, "r") as f:
            return json.load(f)
    except:
        return None


def save_price(data):
    with open(PRICE_FILE, "w") as f:
        json.dump(data, f, indent=2)


##############################################################################
# SCRAPER
##############################################################################

def get_driver():
    options = Options()

    options.add_argument("--headless=new")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    return driver


def parse_price(text):
    digits = re.sub(r"[^\d]", "", text)

    if digits:
        return int(digits)

    return None


def fetch_product_details(url):

    driver = get_driver()

    try:
        driver.get(url)

        time.sleep(5)

        soup = BeautifulSoup(driver.page_source, "html.parser")

        title = None
        price = None

        # Product Title
        title_tag = soup.find("span", {"class": "VU-ZEz"})

        if not title_tag:
            title_tag = soup.find("h1")

        if title_tag:
            title = title_tag.get_text(strip=True)

        # Price
        price_selectors = [
            "div.Nx9bqj.CxhGGd",
            "div._30jeq3",
            "div[class*='Nx9bqj']"
        ]

        for selector in price_selectors:
            element = soup.select_one(selector)

            if element:
                price = parse_price(element.get_text())
                break

        return {
            "title": title,
            "price": price
        }

    finally:
        driver.quit()


##############################################################################
# MONITOR
##############################################################################

def monitor():

    print("=" * 60)
    print("Flipkart Price Tracker Started")
    print("=" * 60)

    while True:

        try:

            data = fetch_product_details(FLIPKART_URL)

            current_price = data["price"]
            title = data["title"]

            if not current_price:
                print("Could not fetch price")
                time.sleep(CHECK_INTERVAL)
                continue

            print(
                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] "
                f"{title[:50]}..."
            )
            print(f"Current Price: ₹{current_price}")

            previous = load_previous_price()

            if previous is None:

                save_price({
                    "title": title,
                    "price": current_price
                })

                print("Initial price stored")

            else:

                old_price = previous["price"]

                if current_price < old_price:

                    drop = old_price - current_price

                    msg = (
                        f"Price Dropped!\n\n"
                        f"{title}\n\n"
                        f"Old Price: ₹{old_price}\n"
                        f"New Price: ₹{current_price}\n"
                        f"You Save: ₹{drop}\n\n"
                        f"{FLIPKART_URL}"
                    )

                    print(msg)

                    desktop_notification(
                        "Flipkart Price Drop!",
                        f"₹{old_price} → ₹{current_price}"
                    )

                    if EMAIL_ALERTS:
                        send_email(
                            "Flipkart Price Drop Alert",
                            msg
                        )

                elif current_price > old_price:

                    print(
                        f"Price Increased "
                        f"₹{old_price} → ₹{current_price}"
                    )

                else:
                    print("No price change")

                save_price({
                    "title": title,
                    "price": current_price
                })

        except Exception as e:
            print("Error:", e)

        print(f"Sleeping {CHECK_INTERVAL//3600} hour(s)...")
        time.sleep(CHECK_INTERVAL)


##############################################################################
# MAIN
##############################################################################

if __name__ == "__main__":
    monitor()