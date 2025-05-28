import requests
import time
import json
import os

WEBHOOK_URL      = 'YOUR_WEBHOOK_URL'
FORTNITE_API_URL = 'https://prm-dialogue-public-api-prod.edea.live.use1a.on.epicgames.com/api/v1/fortnite-br/channel/motd/target'
CLIENT_SECRET    = 'M2Y2OWU1NmM3NjQ5NDkyYzhjYzI5ZjFhZjA4YThhMTI6YjUxZWU5Y2IxMjIzNGY1MGE2OWVmYTY3ZWU1MzgxMmU='
OLD_NEWS_FILE    = 'old_news.json'

DEVICE_ID    = 'YOUR_DEVICE_ID'
SECRET       = 'YOUR_DEVICE_SECRET'
ACCOUNT_ID   = 'YOUR_ACCOUNT_ID'

# New: Role to ping for MOTD news (always ping once)
ROLE_ID_MOTD = YOUR_MOTD_ROLE_ID  # integer

def get_refresh_token():
    print("Debug: Attempting to get refresh token...")
    url = 'https://account-public-service-prod.ol.epicgames.com/account/api/oauth/token'
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': f'Basic {CLIENT_SECRET}',
    }
    body = {
        'grant_type': 'device_auth',
        'device_id': DEVICE_ID,
        'secret': SECRET,
        'account_id': ACCOUNT_ID
    }
    try:
        response = requests.post(url, headers=headers, data=body)
        response.raise_for_status()
        response_data = response.json()
        print(f"Debug: Refresh Token Response: {response_data}")
        return response_data.get('refresh_token')
    except Exception as e:
        print(f"Error: Failed to get refresh token. Exception: {e}")
        return None

def get_access_token(refresh_token):
    print(f"Debug: Attempting to get access token with refresh token: {refresh_token}...")
    url = 'https://account-public-service-prod.ol.epicgames.com/account/api/oauth/token'
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': f'Basic {CLIENT_SECRET}',
        'X-Epic-Device-ID': 'random_device_id',
    }
    body = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'token_type': 'eg1'
    }
    try:
        response = requests.post(url, headers=headers, data=body)
        response.raise_for_status()
        response_data = response.json()
        print(f"Debug: Access Token Response: {response_data}")
        return response_data.get('access_token')
    except Exception as e:
        print(f"Error: Failed to get access token. Exception: {e}")
        return None

def get_news(token):
    print(f"Debug: Attempting to fetch news using access token: {token}...")
    headers = {
        'Authorization': token,
        'Content-Type': 'application/json',
    }
    body = {
        "parameters": {
            "platform": "Windows",
            "language": "en",
            "serverRegion": "EU",
            "country": "DE",
        },
        "tags": ["Product.BR"]
    }
    try:
        response = requests.post(FORTNITE_API_URL, headers=headers, json=body)
        response.raise_for_status()
        response_data = response.json()
        print(f"Debug: News Response: {response_data}")
        return response_data
    except Exception as e:
        print(f"Error: Failed to fetch news. Exception: {e}")
        if '401' in str(e):
            raise Exception("Access token expired")
    return {}

def send_discord_message(title, body, image_url, thumbnail_url, content=None):
    print(f"Debug: Sending Discord message: {title}")
    data = {}
    if content:
        data["content"] = content
    data["embeds"] = [
        {
            "title": title,
            "description": body,
            "image": {"url": image_url},
            "thumbnail": {"url": thumbnail_url}
        }
    ]
    try:
        response = requests.post(WEBHOOK_URL, json=data)
        response.raise_for_status()
        print(f"Debug: Discord Response Status Code: {response.status_code}")
    except Exception as e:
        print(f"Error: Failed to send Discord message. Exception: {e}")

def save_news_data(news_data):
    print(f"Debug: Saving news data: {news_data}")
    try:
        with open(OLD_NEWS_FILE, 'w') as file:
            json.dump(news_data, file)
        print("Debug: News data successfully saved.")
    except Exception as e:
        print(f"Error: Failed to save news data. Exception: {e}")

def load_old_news_data():
    print("Debug: Loading old news data...")
    try:
        if os.path.exists(OLD_NEWS_FILE):
            with open(OLD_NEWS_FILE, 'r') as file:
                old_news = json.load(file)
                print(f"Debug: Old news data loaded: {old_news}")
                return old_news
        else:
            print("Debug: No old news data file found.")
    except Exception as e:
        print(f"Error: Failed to load old news data. Exception: {e}")
    return []

def main():
    old_news_data = load_old_news_data() or []
    refresh_token = get_refresh_token()
    if not refresh_token:
        print("Error: Failed to obtain refresh token.")
        return

    while True:
        access_token = get_access_token(refresh_token)
        if not access_token:
            print("Error: Failed to obtain access token.")
            refresh_token = get_refresh_token()
            continue
        try:
            news_data = get_news(access_token)
        except Exception as e:
            if str(e) == "Access token expired":
                refresh_token = get_refresh_token()
                continue

        if 'contentItems' in news_data and news_data['contentItems']:
            current_list = [item['contentFields'] for item in news_data['contentItems']]
            new_items = [item for item in current_list if item not in old_news_data]
            if new_items:
                # always ping once (even if only one)
                ping_once = True
                for idx, item in enumerate(new_items):
                    title         = item.get('FullScreenTitle', 'No Title')
                    body          = item.get('FullScreenBody',  'No Body')
                    image_url     = item.get('FullScreenBackground', {}).get('Image', [{}])[0].get('url','')
                    thumbnail_url = item.get('TileImage', {}).get('Image', [{}])[0].get('url','')
                    if idx == 0 and ping_once:
                        send_discord_message(
                            title, body, image_url, thumbnail_url,
                            content=f"<@&{ROLE_ID_MOTD}>"
                        )
                    else:
                        send_discord_message(title, body, image_url, thumbnail_url)
                save_news_data(current_list)
                old_news_data = current_list

        time.sleep(60)

if __name__ == "__main__":
    main()