import requests
from urllib.parse import quote
import feedparser
from newspaper import Article
from bs4 import BeautifulSoup


def search_from_wikipedia_action_api(query: str, lang="en"):

    url = f"https://{lang}.wikipedia.org/w/api.php"

    
    params = {
        "action": "query",
        "prop": "extracts",
        "exintro": True,
        "explaintext": True,
        "titles": query,
        "format": "json"
    }
    response = requests.get(url, params=params)
    data = response.json()

    pages = data.get("query", {}).get("pages", {})

    for page_id, page_data in pages.items():
        # Check if page exists and is not missing
        if page_data and "missing" not in page_data:
            return {
                "title": page_data.get("title", ""),
                "extract": page_data.get("extract", ""),
                "source": f"https://{lang}.wikipedia.org/wiki/{quote(query)}"
            }
    
    return {
        "title": "No information found",
        "extract": "Sorry, no information could be found for your request.",
        "source": ""
    }


def search_google_news_with_content(query, lang="en"):
    url = f"https://news.google.com/rss/search?q={quote(query)}" #RSS = rich site summary (provided me as title, link, summary, published_at)
    feed = feedparser.parse(url)
    articles = []

    for entry in feed.entries[:2]: #lasted 10 news provided me
        article_url = entry.link
        try:
            # Extract full article using newspaper3k
            article = Article(article_url)
            article.download()
            # Manually set user-agent if blocked
            # article.set_user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36")

            article.parse()

            articles.append({
                "title": article.title,
                "link": article_url,
                "published": entry.published,
                "summary": entry.summary,
                "full_text": article.text
            })

        except Exception as e:
            articles.append({
                "title": entry.title,
                "link": article_url,
                "published": entry.published,
                "summary": entry.summary,
                "full_text": "Could not fetch full content."
            })

    return articles



def search_linkedin_duckduckgo(name, lang="en"):
    url = f"https://html.duckduckgo.com/html/?q={name.replace(' ', '+')}+site:linkedin.com/in"
    headers = {
         "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    }
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")

    results = []
    for result in soup.find_all("a", class_="result__a", limit=3):
        results.append({
            "title": result.text,
            "url": result.get("href")
        })

    return results

