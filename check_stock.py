import pathlib
from typing import Generator, cast

import requests
from bs4 import BeautifulSoup, ResultSet, Tag

FARER_URL = "https://usd.farer.com"
PRODUCTS_LIST_URL = FARER_URL + "/products.json"
PRODUCT_URL_BASE = FARER_URL + "/products/"

STOCK_PATH = pathlib.Path("stock")


def get_product_links() -> Generator[str, None, None]:
    page = 1
    while products := requests.get(
        PRODUCTS_LIST_URL, params={"limit": 250, "page": page}
    ).json()["products"]:
        for product in products:
            if product["product_type"] == "Watch":
                yield PRODUCT_URL_BASE + product["handle"]

        if len(products) < 250:
            break
        page += 1


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

for product_link in get_product_links():
    print(f"Getting availability for {product_link}")
    stock = get_product_stock(product_link)

    if not stock:
        print("No stock found")
        continue

    product_slug = product_link.split("/")[-1]
    with open(STOCK_PATH / product_slug, "w") as f:
        f.write("\n".join(stock))
