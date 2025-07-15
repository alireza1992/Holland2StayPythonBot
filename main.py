import http.client
import json
import urllib.parse
from datetime import datetime
import dateutil.tz
import ssl
import certifi
import time
import requests
import subprocess

ssl_context = ssl.create_default_context(cafile=certifi.where())

TELEGRAM_TOKEN = ''
CHAT_IDS = ['', '']
BASIC_RENT = 1700
# Mapping of city codes to names
city_map = {
    "26": "Delft",
    "90": "Den Haag",
    "24": "Amsterdam",
    "25": "Rotterdam",
    "27": "Utrecht",
    # Add more cities if needed
}

# LINE Notify token (replace with your actual token)

# API headers
headers = {
    "Accept": "*/*",
    "User-Agent": "Python Script",
    "Content-Type": "application/json"
}



# Send message via Telegram
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    for chat_id in CHAT_IDS:
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        try:
            res = requests.post(url, data=payload)
            if res.status_code != 200:
                print(f"[Telegram error] {res.text}")
        except Exception as e:
            print(f"[Telegram exception] {e}")

def fetch_city_data(city_code):
    """Fetch listings data for a specific city."""
    conn = http.client.HTTPSConnection("api.holland2stay.com",context=ssl_context)

    payload = json.dumps({
        "operationName": "GetCategories",
        "variables": {
            "currentPage": 1,
            "id": "Nw==",
            "filters": {
                "available_to_book": {"eq": "179"},
                "city": {"eq": city_code},
                "category_uid": {"eq": "Nw=="}
            },
            "pageSize": 50,
            "sort": {"available_startdate": "ASC"}
        },
        "query": """query GetCategories($id: String!, $pageSize: Int!, $currentPage: Int!, $filters: ProductAttributeFilterInput!, $sort: ProductAttributeSortInput) {
            categories(filters: {category_uid: {in: [$id]}}) {
                items {
                    uid
                    ...CategoryFragment
                    __typename
                }
                __typename
            }
            products(
                pageSize: $pageSize,
                currentPage: $currentPage,
                filter: $filters,
                sort: $sort
            ) {
                ...ProductsFragment
                __typename
            }
        }

        fragment CategoryFragment on CategoryTree {
            uid
            meta_title
            meta_keywords
            meta_description
            __typename
        }

        fragment ProductsFragment on Products {
            items {
                name
                city
                offer_text
                offer_text_two
                basic_rent
                url_key
                __typename
            }
            __typename
        }"""
    })

    conn.request("POST", "/graphql/", payload, headers)
    response = conn.getresponse()
    data = response.read().decode("utf-8")
    return json.loads(data)


import re

def slugify(name):
    slug = re.sub(r'[^a-zA-Z0-9 ]', '', name)
    slug = slug.lower().replace(' ', '-')
    return slug

def main():
    all_product_details = []

    for city_code, city_name in city_map.items():
        try:
            data = fetch_city_data(city_code)
            products = data['data']['products']['items']

            for item in products:

                name = item.get('name', '')
                offer_1 = str(item.get('offer_text') or "")
                offer_2 = str(item.get('offer_text_two') or "")
                price = item.get('basic_rent', None)
                url_key = item.get('url_key', '')

                if price is None:
                    price_text = "N/A"
                else:
                    price_text = f"€{price}"

                if price is None or not isinstance(price, (int, float)) or price > 1800:
                    continue  # Skip listings above €2000 or missing price

                if (
                        "Housing permit required" in offer_2
                        or "Short-stay" in offer_1
                        or "Short-stay" in offer_2
                ):
                    continue

                link = f"https://holland2stay.com/residence/{url_key}.html"

                message = (
                    f"🏙️ *{city_name}* - {name}\n"
                    f"💰 Price: {price_text}\n"
                    f"📝 Notes: {offer_1}, {offer_2}\n"
                    f"[View Listing]({link})"

                )

                all_product_details.append(message)

        except Exception as e:
            print(f"[Error] Failed to process city {city_name}: {e}")

    if all_product_details:
        message = "🏠 *Available residences:*\n\n" + "\n\n".join(all_product_details)
        send_telegram_message(message)
        print(message)

        # 🔔 macOS Notification
        subprocess.run([
            "osascript", "-e",
            f'display notification "Found {len(all_product_details)} listings" with title "🏠 Holland2Stay Alert" sound name "Glass"'
        ])

    else:
        now = datetime.now(dateutil.tz.gettz("Europe/Amsterdam"))
        if now.hour == 18 and now.minute == 0:
            print("⏰ BOT is alive. No listings available currently.")
        else:
            print("[Info] No listings found.")



if __name__ == "__main__":
    while True:
        main()
        time.sleep(20)  # Wait 20 Seconds because its Netherlands and otherwise you will miss the house
