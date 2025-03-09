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

# ---------------------------
# GLOBAL CONFIGURATION
# ---------------------------
GLOBAL_CONFIG = {
    "LOGIN_URL": "https://www.naukri.com/",
    "PROFILE_UPDATE_URL": "https://www.naukri.com/cloudgateway-mynaukri/resman-aggregator-services/v1/users/self/fullprofiles"
}

# ---------------------------
# USER SPECIFIC CONFIGURATION
# ---------------------------
# You can add multiple users here, code will iterate and process this one by one
# Each user will have their unique profile_id which you can get by inpecting element 
# and using network tab in your local while updating bio

USER_CONFIGS = [
    {
        "username": "anubhav.tomar.at@gmail.com",
        "password": "12345@zxcvB",
        "profile_id": "82149711e52eb452740ca2b333163638c0b88703c4c3bdf85c4f31944917d4da",
        "base_bio": ("Experienced Software Development Engineer with over 5 years of experience "
                     "With a robust foundation in Java, Python, Spring Boot, MySQL, MongoDB, Redis, "
                     "Kafka, SNS and extensive use of AWS Cloud......z")
    },
    {
        "username": "anubhav.tomar.at@gmail.com",
        "password": "12345@zxcvB",
        "profile_id": "82149711e52eb452740ca2b333163638c0b88703c4c3bdf85c4f31944917d4da",
        "base_bio": ("Experienced Software Development Engineer with over 5 years of experience "
                     "With a robust foundation in Java, Python, Spring Boot, MySQL, MongoDB, Redis, "
                     "Kafka, SNS and extensive use of AWS Cloud......z")
    }
]

# ---------------------------
# UI ELEMENT CONFIGURATION
# ---------------------------
class ButtonConfig(Enum):
    TOP_RIGHT_LOGIN_BUTTON_ID = "login_Layer"
    EMAIL_INPUT_FIELD = '//input[@placeholder="Enter your active Email ID / Username"]'
    PASSWORD_INPUT_FIELD = '//input[@placeholder="Enter your password"]'
    FINAL_LOGIN_BUTTON = '//button[contains(@class, "loginButton") and contains(text(),"Login")]'

# ---------------------------
# FUNCTIONS
# ---------------------------
def login_and_capture_logs(username, password):
    chrome_options = Options()
    # Enable headless mode.
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36")
    # Additional flags to reduce automation detection.
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--remote-debugging-port=9222")
    
    # Use a unique temporary user-data directory.
    user_data_dir = f"/tmp/chrome-user-data-{int(time.time())}"
    chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
    
    # Set logging preferences via options.
    chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    
    # Specify binary location if needed.
    chrome_options.binary_location = os.getenv("CHROME_BIN", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        print("Navigating to login URL...", flush=True)
        driver.get(GLOBAL_CONFIG["LOGIN_URL"])
        wait = WebDriverWait(driver, 60)
        
        try:
            top_login = wait.until(EC.presence_of_element_located((By.ID, ButtonConfig.TOP_RIGHT_LOGIN_BUTTON_ID.value)))
            driver.execute_script("arguments[0].scrollIntoView(true);", top_login)
            driver.execute_script("arguments[0].click();", top_login)
            print("Clicked the top-right login button.", flush=True)
        except TimeoutException as te:
            print("Top-right login button not found; checking if already logged in...", flush=True)
            try:
                wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'nI-gNb-log-reg')]")))
                print("User appears already logged in; skipping login button click.", flush=True)
            except TimeoutException:
                print("Top-right login button not found and user is not logged in. Aborting.", flush=True)
                raise te
        
        email_field = wait.until(EC.visibility_of_element_located((By.XPATH, ButtonConfig.EMAIL_INPUT_FIELD.value)))
        password_field = wait.until(EC.visibility_of_element_located((By.XPATH, ButtonConfig.PASSWORD_INPUT_FIELD.value)))
        print("Filling in email and password...", flush=True)
        email_field.send_keys(username)
        password_field.send_keys(password)
        
        try:
            final_login = wait.until(EC.presence_of_element_located((By.XPATH, ButtonConfig.FINAL_LOGIN_BUTTON.value)))
            driver.execute_script("arguments[0].click();", final_login)
            print("Clicked the final login button.", flush=True)
        except TimeoutException as te:
            print("Final login button not found; aborting.", flush=True)
            raise te
        
        wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'nI-gNb-log-reg')]")))
        print("Login confirmed.", flush=True)
        
        time.sleep(5)
        logs = driver.get_log("performance")
        print(f"Captured {len(logs)} performance log entries.", flush=True)
        return logs, driver
    finally:
        # Do not quit the driver here if fallback extraction is needed.
        pass

def extract_token_from_local_storage(driver):
    print("Attempting to extract token from local storage...", flush=True)
    keys = driver.execute_script("return Object.keys(window.localStorage);")
    print("Local storage keys found:", keys, flush=True)
    for key in keys:
        value = driver.execute_script(f"return window.localStorage.getItem('{key}');")
        if value and value.count('.') == 2 and len(value) > 100:
            print(f"Found possible JWT token in local storage under key '{key}': {value[:30]}...", flush=True)
            return value
    print("No token found in local storage.", flush=True)
    return None

def find_bearer_tokens(logs):
    print("Scanning performance logs for Bearer tokens...", flush=True)
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
                            print(f"Found Bearer token in header '{key}': {value[:30]}...", flush=True)
                            tokens.append(value)
        except Exception as e:
            logging.error("Error processing log entry: %s", e)
    print(f"Total Bearer tokens found: {len(tokens)}", flush=True)
    return tokens

def update_resume_headline(token, profile_id, base_bio):
    print("Preparing to update resume headline...", flush=True)
    day = datetime.datetime.now().day
    if day % 2 == 1:
        updated_bio = base_bio if base_bio.endswith('.') else base_bio + '.'
    else:
        updated_bio = base_bio.rstrip('.') if base_bio.endswith('.') else base_bio
    
    auth_token = token if token.startswith("Bearer ") else f"Bearer {token}"
    
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
        "profileId": profile_id
    }
    
    print("Sending API request with headers:", flush=True)
    print(json.dumps(headers, indent=4), flush=True)
    print("Payload:", flush=True)
    print(json.dumps(data, indent=4), flush=True)
    
    response = requests.post(GLOBAL_CONFIG["PROFILE_UPDATE_URL"], headers=headers, json=data)
    return response

def update_resume_headline_using_cookies(cookies, profile_id, base_bio):
    print("Updating resume headline using session cookies...", flush=True)
    day = datetime.datetime.now().day
    if day % 2 == 1:
        updated_bio = base_bio if base_bio.endswith('.') else base_bio + '.'
    else:
        updated_bio = base_bio.rstrip('.') if base_bio.endswith('.') else base_bio
    
    headers = {
        'accept': 'application/json',
        'accept-language': 'en-US,en-GB;q=0.9,en;q=0.8,hi;q=0.7',
        'appid': '105',
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
        "profileId": profile_id
    }
    
    cookies_dict = {cookie['name']: cookie['value'] for cookie in cookies}
    
    print("Sending API request with headers (using cookies):", flush=True)
    print(json.dumps(headers, indent=4), flush=True)
    print("Payload:", flush=True)
    print(json.dumps(data, indent=4), flush=True)
    
    response = requests.post(GLOBAL_CONFIG["PROFILE_UPDATE_URL"], headers=headers, json=data, cookies=cookies_dict)
    return response

def main():
    for user in USER_CONFIGS:
        print(f"\nProcessing user: {user['username']}", flush=True)
        logs, driver = login_and_capture_logs(user['username'], user['password'])
        tokens = find_bearer_tokens(logs)
        print(f"Tokens found in logs: {tokens}", flush=True)
        
        if tokens:
            token = tokens[0]
            print("Using Bearer token from logs:", flush=True)
            print(token, flush=True)
            response = update_resume_headline(token, user['profile_id'], user['base_bio'])
        else:
            print("No Bearer token found in logs; checking local storage...", flush=True)
            token = extract_token_from_local_storage(driver)
            if token:
                print("Using token from local storage:", flush=True)
                print(token, flush=True)
                response = update_resume_headline(token, user['profile_id'], user['base_bio'])
            else:
                print("No token found in logs or local storage; using session cookies...", flush=True)
                cookies = driver.get_cookies()
                print("Cookies retrieved:", cookies, flush=True)
                response = update_resume_headline_using_cookies(cookies, user['profile_id'], user['base_bio'])
        
        driver.quit()
        
        print("API Response Code:", response.status_code, flush=True)
        print("API Response Body:", response.text, flush=True)

if __name__ == "__main__":
    main()
