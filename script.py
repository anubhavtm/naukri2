import os
import time
import json
import logging
import datetime
import requests
from enum import Enum
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException

# Enum for general configuration variables (non-UI parameters)
class Config(Enum):
    LOGIN_URL = 'https://www.naukri.com/'
    USERNAME = 'anubhav.tomar.at@gmail.com'
    PASSWORD = '12345@zxcvB'
    PROFILE_UPDATE_URL = 'https://www.naukri.com/cloudgateway-mynaukri/resman-aggregator-services/v1/users/self/fullprofiles'
    PROFILE_ID = '82149711e52eb452740ca2b333163638c0b88703c4c3bdf85c4f31944917d4da'
    BASE_BIO = ("Experienced Software Development Engineer with over 5 years of experience "
                "With a robust foundation in Java, Python, Spring Boot, MySQL, MongoDB, Redis, "
                "Kafka, SNS and extensive use of AWS Cloud......z")

# Enum for UI elements (input fields and buttons)
class ButtonConfig(Enum):
    TOP_RIGHT_LOGIN_BUTTON_ID = "login_Layer"
    EMAIL_INPUT_FIELD = '//input[@placeholder="Enter your active Email ID / Username"]'
    PASSWORD_INPUT_FIELD = '//input[@placeholder="Enter your password"]'
    FINAL_LOGIN_BUTTON = '//button[contains(@class, "loginButton") and contains(text(),"Login")]'

def login_and_capture_logs():
    chrome_options = Options()
    # Enable headless mode.
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # Set a fixed window size.
    chrome_options.add_argument("--window-size=1920,1080")
    # Set a standard user-agent to mimic a normal desktop browser.
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36")
    
    # Use a unique temporary user-data directory to avoid conflicts.
    user_data_dir = f"/tmp/chrome-user-data-{int(time.time())}"
    chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
    
    # Set logging preferences via options (Selenium 4+)
    chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    
    # Specify binary location if needed.
    chrome_options.binary_location = os.getenv("CHROME_BIN", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        driver.get(Config.LOGIN_URL.value)
        wait = WebDriverWait(driver, 60)
        
        # Try to locate and click the top-right login button.
        try:
            top_login = wait.until(EC.presence_of_element_located((By.ID, ButtonConfig.TOP_RIGHT_LOGIN_BUTTON_ID.value)))
            driver.execute_script("arguments[0].scrollIntoView(true);", top_login)
            driver.execute_script("arguments[0].click();", top_login)
            print("Clicked the login button.")
        except TimeoutException as te:
            print("Login button not found. Checking if already logged in...")
            # If the login button is not found, try verifying if user is already logged in.
            try:
                wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'nI-gNb-log-reg')]")))
                print("User appears already logged in; skipping login click.")
            except TimeoutException:
                print("Login button not found and user is not logged in. Exiting.")
                raise te
        
        # Fill in the login form.
        email_field = wait.until(EC.visibility_of_element_located((By.XPATH, ButtonConfig.EMAIL_INPUT_FIELD.value)))
        password_field = wait.until(EC.visibility_of_element_located((By.XPATH, ButtonConfig.PASSWORD_INPUT_FIELD.value)))
        email_field.send_keys(Config.USERNAME.value)
        password_field.send_keys(Config.PASSWORD.value)
        
        # Click the final login button.
        try:
            final_login = wait.until(EC.presence_of_element_located((By.XPATH, ButtonConfig.FINAL_LOGIN_BUTTON.value)))
            driver.execute_script("arguments[0].click();", final_login)
            print("Clicked the final login button.")
        except TimeoutException as te:
            print("Final login button not found. Exiting.")
            raise te
        
        # Wait for login confirmation element.
        wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'nI-gNb-log-reg')]")))
        print("Login confirmed.")
        
        # Allow extra time for network activity to be logged.
        time.sleep(5)
        
        # Retrieve performance logs.
        logs = driver.get_log("performance")
        return logs
    finally:
        driver.quit()

def find_bearer_tokens(logs):
    tokens = []
    for entry in logs:
        try:
            message = json.loads(entry["message"])["message"]
            if message.get("method") in ["Network.requestWillBeSent", "Network.responseReceived"]:
                headers = None
                if message["method"] == "Network.requestWillBeSent":
                    headers = message.get("params", {}).get("request", {}).get("headers", {})
                elif message["method"] == "Network.responseReceived":
                    headers = message.get("params", {}).get("response", {}).get("headers", {})
                if headers:
                    for key, value in headers.items():
                        if isinstance(value, str) and value.startswith("Bearer"):
                            tokens.append(value)
        except Exception as e:
            logging.error("Error processing log entry: %s", e)
    return tokens

def update_resume_headline(token):
    base_bio = Config.BASE_BIO.value
    day = datetime.datetime.now().day
    if day % 2 == 1:
        updated_bio = base_bio if base_bio.endswith('.') else base_bio + '.'
    else:
        updated_bio = base_bio.rstrip('.') if base_bio.endswith('.') else base_bio
    
    # Ensure 'Bearer' appears only once.
    if token.startswith("Bearer "):
        auth_token = token
    else:
        auth_token = f"Bearer {token}"
    
    headers = {
        'accept': 'application/json',
        'accept-language': 'en-US,en-GB;q=0.9,en;q=0.8,hi;q=0.7',
        'appid': '105',
        'authorization': auth_token,
        'clientid': 'd3skt0p',
        'content-type': 'application/json',
        'dnt': '1',
        'origin': 'https://www.naukri.com',
        'priority': 'u=1, i',
        'referer': 'https://www.naukri.com/mnjuser/profile?id=&altresid&action=modalOpen',
        'sec-ch-ua': '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'systemid': 'Naukri',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
        'x-http-method-override': 'PUT',
        'x-requested-with': 'XMLHttpRequest'
    }
    
    data = {
        "profile": {"resumeHeadline": updated_bio},
        "profileId": Config.PROFILE_ID.value
    }
    
    print("Sending API request with headers:")
    print(json.dumps(headers, indent=4))
    print("Payload:")
    print(json.dumps(data, indent=4))
    
    response = requests.post(Config.PROFILE_UPDATE_URL.value, headers=headers, json=data)
    return response

def main():
    logs = login_and_capture_logs()
    tokens = find_bearer_tokens(logs)
    if tokens:
        token = tokens[0]
        print("Found Bearer token:")
        print(token)
        response = update_resume_headline(token)
        print("API Response Code:", response.status_code)
        print("API Response Body:", response.text)
    else:
        print("No Bearer tokens found.")

if __name__ == "__main__":
    main()
