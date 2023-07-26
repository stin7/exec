import os
import html2text
import requests
from serpapi import BingSearch


def get_organic_search_results(query):
    params = {
        "q": query,
        "cc": "US",
        "api_key": os.getenv("SERPAPI_API_KEY"),
    }
    search = BingSearch(params)
    return search.get_dict()["organic_results"]


def get_markdown_from_url(url):
    # Step 1 & 2: Download HTML from URL
    response = requests.get(url)
    html = response.text
    # Step 3 & 4: Convert HTML to Markdown
    text_maker = html2text.HTML2Text()
    text_maker.ignore_links = False
    markdown = text_maker.handle(html)
    return markdown


if __name__ == "__main__":
    result = get_organic_search_results("vegetarian resturants in san francisco")
    # usage
    url = "https://example.com"
    print(get_markdown_from_url(url))
