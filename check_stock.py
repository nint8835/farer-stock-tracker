import pathlib
from typing import Generator, cast

import requests
from bs4 import BeautifulSoup, ResultSet, Tag

FARER_URL = "https://usd.farer.com"
ALL_WATCHES_URL = FARER_URL + "/collections/all-watches"

STOCK_PATH = pathlib.Path("stock")


def get_product_links() -> Generator[str, None, None]:
    watches_resp = requests.get(ALL_WATCHES_URL)
    watches_soup = BeautifulSoup(watches_resp.text, "html.parser")

    products = cast(ResultSet[Tag], watches_soup.find_all("div", class_="product"))
    for product in products:
        product_link_tag = cast(Tag | None, product.find("a"))
        if product_link_tag is None:
            print("No product link found for product")
            continue

        product_link = product_link_tag.get("href")
        if product_link is None or isinstance(product_link, list):
            print("Incorrect number of hrefs found for product")
            continue

        product_link = FARER_URL + product_link
        yield product_link


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
