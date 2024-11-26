import json
import os
import pathlib

import dotenv
import requests

dotenv.load_dotenv()

notification_webhook = os.environ["NOTIFICATION_WEBHOOK_URL"]

FARER_URL = "https://usd.farer.com"
PRODUCTS_LIST_URL = FARER_URL + "/products.json"
PRODUCT_URL_BASE = FARER_URL + "/products/"
HANDLE_AVAILABILITY_URL = "https://zepto-numbering-app.com/api/codes"

STOCK_PATH = pathlib.Path("stock")
STOCK_PATH.mkdir(exist_ok=True)

README_CONTENT = """# farer-stock-tracker

This repo tracks the available serial numbers for each watch model from [Farer](https://farer.com).

## Usage

This repo updates the available serial numbers every hour. Serial numbers for each model are listed in the relevant file in the [stock](./stock) folder. A summary of available stock is listed below.

## Stock

| Model | Available | Serial Numbers |
| ----- | --------: | -------------: |
"""


def get_watches() -> list[tuple[str, str]]:
    watches = []

    page = 1
    while products := requests.get(
        PRODUCTS_LIST_URL, params={"limit": 250, "page": page}
    ).json()["products"]:
        for product in products:
            if product["product_type"] == "Watch":
                watches.append(
                    (
                        (
                            " ".join(
                                [
                                    word.strip()
                                    for word in product["title"]
                                    .replace("<br>", " - ")
                                    .replace("<b>", "")
                                    .replace("</b>", "")
                                    .split(" ")
                                    if word.strip()
                                ]
                            )
                        ),
                        product["handle"],
                    )
                )

        if len(products) < 250:
            break
        page += 1

    watches.sort(key=lambda x: x[0])

    return watches


def get_handle_availability(handle: str) -> list[str]:
    availability_resp = requests.post(HANDLE_AVAILABILITY_URL, json={"handle": handle})
    return [str(i) for i in availability_resp.json()["numbers"]]


def get_product_stock(link: str) -> list[str]:
    product_resp = requests.get(link + ".json")
    handle = product_resp.json()["product"]["handle"]
    return get_handle_availability(handle)


with open("seen.json") as f:
    seen_watches = set(json.load(f))


print("Cleaning existing stock files")
for file in STOCK_PATH.iterdir():
    file.unlink()

total_stock = 0

for watch_name, watch_slug in get_watches():
    if watch_slug not in seen_watches:
        print(f"New watch found: {watch_name}")
        seen_watches.add(watch_slug)

        requests.post(
            notification_webhook,
            json={
                "content": f"New watch found on Farer's site: [{watch_name}]({PRODUCT_URL_BASE + watch_slug})"
            },
        )

    print(f"Getting availability for {watch_name}")
    stock = get_product_stock(PRODUCT_URL_BASE + watch_slug)

    if not stock:
        print("No stock found")
        continue

    with open(STOCK_PATH / watch_slug, "w") as f:
        f.write("\n".join(stock) + "\n")

    README_CONTENT += f"| [{watch_name}]({PRODUCT_URL_BASE + watch_slug}) | {len(stock)} | [`{watch_slug}`](./stock/{watch_slug}) |\n"
    total_stock += len(stock)


README_CONTENT += f"| **Total** | **{total_stock}** | |\n"

with open("README.md", "w") as f:
    f.write(README_CONTENT)

with open("seen.json", "w") as f:
    json.dump(sorted(list(seen_watches)), f, indent=2)
