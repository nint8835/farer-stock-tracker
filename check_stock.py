import pathlib
from typing import Generator, cast

import requests
from bs4 import BeautifulSoup, ResultSet, Tag

FARER_URL = "https://usd.farer.com"
PRODUCTS_LIST_URL = FARER_URL + "/products.json"
PRODUCT_URL_BASE = FARER_URL + "/products/"

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


def get_product_stock(link: str) -> list[str]:
    product_resp = requests.get(link)
    product_soup = BeautifulSoup(product_resp.text, "html.parser")

    uniq_num_select = cast(Tag | None, product_soup.find("select", id="uniq-num"))
    if uniq_num_select is None:
        print("No uniq-num select found for product")
        return []

    options = cast(ResultSet[Tag], uniq_num_select.find_all("option"))
    return [cast(str, option.get("value")) for option in options if option.get("value")]


print("Cleaning existing stock files")
for file in STOCK_PATH.iterdir():
    file.unlink()

total_stock = 0

for watch_name, watch_slug in get_watches():
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
