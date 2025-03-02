import os
import json
import time
import datetime
import requests
import tempfile
import shutil
from enum import Enum
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import jwt

class Config(Enum):
    TOKEN_FILE = 'token_cache.json'
    LOGIN_URL = 'https://www.naukri.com/'
    PROFILE_UPDATE_URL = 'https://www.naukri.com/cloudgateway-mynaukri/resman-aggregator-services/v1/users/self/fullprofiles'
    USERNAME = 'anubhav.tomar.at@gmail.com'
    PASSWORD = '12345@zxcvB'
    # Replace with your actual profile id
    PROFILE_ID = '82149711e52eb452740ca2b333163638c0b88703c4c3bdf85c4f31944917d4da'
    TOKEN_LOCAL_STORAGE_KEY = 'access_token'
    TOP_RIGHT_LOGIN_BUTTON_ID = "login_Layer"
    EMAIL_INPUT_FIELD = '//input[@placeholder="Enter your active Email ID / Username"]'
    PASSWORD_INPUT_FIELD = '//input[@placeholder="Enter your password"]'
    FINAL_LOGIN_BUTTON = '//button[contains(@class, "loginButton") and contains(text(),"Login")]'

def is_token_expired(token, threshold_minutes=5):
    try:
        # Decode without verifying the signature.
        payload = jwt.decode(token, options={"verify_signature": False})
        exp_timestamp = payload.get('exp')
        if exp_timestamp:
            exp_datetime = datetime.datetime.fromtimestamp(exp_timestamp)
            return datetime.datetime.now() >= (exp_datetime - datetime.timedelta(minutes=threshold_minutes))
        return True
    except Exception as e:
        print("Error checking token expiration:", e)
        return True

def load_token():
    if os.path.exists(Config.TOKEN_FILE.value):
        with open(Config.TOKEN_FILE.value, 'r') as f:
            data = json.load(f)
            token = data.get('token')
            if token and not is_token_expired(token):
                return token
    return None

def save_token(token):
    with open(Config.TOKEN_FILE.value, 'w') as f:
        json.dump({'token': token}, f)

def login_and_get_token():
    chrome_options = Options()
    # Uncomment the following line for headless mode in production:
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    
    # Create a unique temporary directory for user data
    temp_dir = tempfile.mkdtemp()
    print("Using temporary user data directory:", temp_dir)
    chrome_options.add_argument(f"--user-data-dir={temp_dir}")
    
    # Set Chrome binary location if needed.
    chrome_options.binary_location = os.getenv("CHROME_BIN", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        driver.get(Config.LOGIN_URL.value)
        driver.maximize_window()
        wait = WebDriverWait(driver, 30)
        
        # Click the top right login button.
        top_login = wait.until(EC.element_to_be_clickable((By.ID, Config.TOP_RIGHT_LOGIN_BUTTON_ID.value)))
        driver.execute_script("arguments[0].scrollIntoView(true);", top_login)
        top_login.click()
        
        time.sleep(3)  # Wait for the login modal to appear.
        
        email_field = wait.until(EC.element_to_be_clickable((By.XPATH, Config.EMAIL_INPUT_FIELD.value)))
        password_field = wait.until(EC.element_to_be_clickable((By.XPATH, Config.PASSWORD_INPUT_FIELD.value)))
        
        email_field.send_keys(Config.USERNAME.value)
        password_field.send_keys(Config.PASSWORD.value)
        
        final_login = wait.until(EC.element_to_be_clickable((By.XPATH, Config.FINAL_LOGIN_BUTTON.value)))
        final_login.click()
        
        time.sleep(10)  # Wait for the login process to complete.
        
        # Try extracting the token from localStorage.
        token = driver.execute_script(
            f"return window.localStorage.getItem('{Config.TOKEN_LOCAL_STORAGE_KEY.value}');"
        )
        if token:
            print("Token retrieved from localStorage.")
            save_token(token)
            return token
        
        # Fallback: extract token from cookies.
        cookies = driver.get_cookies()
        for cookie in cookies:
            if cookie.get('name') == 'nauk_at':
                token = cookie.get('value')
                print("Token retrieved from cookie 'nauk_at'.")
                break
        
        if token:
            save_token(token)
        else:
            print("Token not found. Check extraction logic.")
        return token
    finally:
        driver.quit()
        # Clean up the temporary user data directory
        shutil.rmtree(temp_dir)
        print("Temporary user data directory removed.")

def get_token():
    token = load_token()
    if not token:
        token = login_and_get_token()
    return token

def update_resume_headline(token):
    base_bio = (
        "Experienced Software Development Engineer with over 5 years of experience "
        "With a robust foundation in Java, Python, Spring Boot, MySQL, MongoDB, Redis, "
        "Kafka, SNS and extensive use of AWS Cloud....z"
    )
    day = datetime.datetime.now().day
    if day % 2 == 1:
        updated_bio = base_bio if base_bio.endswith('.') else base_bio + '.'
    else:
        updated_bio = base_bio.rstrip('.') if base_bio.endswith('.') else base_bio

    headers = {
        'accept': 'application/json',
        'accept-language': 'en-US,en-GB;q=0.9,en;q=0.8,hi;q=0.7',
        'appid': '105',
        'authorization': f'Bearer {token}',
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
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
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
    token = get_token()
    if not token:
        print("Failed to obtain a valid token.")
        return
    
    response = update_resume_headline(token)
    if response.status_code == 401:
        print("Token invalid or expired. Re-logging in.")
        token = login_and_get_token()
        if token:
            response = update_resume_headline(token)
        else:
            print("Re-login failed.")
            return

    print("API Response Code:", response.status_code)
    print("API Response Body:", response.text)

if __name__ == "__main__":
    main()
