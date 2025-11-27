"""
Google News Collector
Fetches news articles based on query string using Google News RSS feed
"""
import feedparser
import requests
from datetime import datetime
from typing import Dict, List, Any
import json


class GoogleNewsCollector:
    """Collects news from Google News RSS feed"""

    BASE_URL = "https://news.google.com/rss/search"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def collect(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        """
        Collect news articles for a given query

        Args:
            query: Search query string
            max_results: Maximum number of results to return

        Returns:
            Dictionary with status and articles list
        """
        try:
            # Build the RSS URL
            params = {
                'q': query,
                'hl': 'en-US',
                'gl': 'US',
                'ceid': 'US:en'
            }

            # Construct URL with parameters
            url = f"{self.BASE_URL}?q={requests.utils.quote(query)}&hl=en-US&gl=US&ceid=US:en"

            # Fetch and parse RSS feed
            feed = feedparser.parse(url)

            if feed.bozo:
                return {
                    'status': 'error',
                    'error': 'Failed to parse RSS feed',
                    'articles': []
                }

            articles = []
            for entry in feed.entries[:max_results]:
                article = {
                    'title': entry.get('title', ''),
                    'summary': entry.get('summary', ''),
                    'url': entry.get('link', ''),
                    'publish_date': self._parse_date(entry.get('published', '')),
                    'source': entry.get('source', {}).get('title', 'Unknown')
                }
                articles.append(article)

            return {
                'status': 'success',
                'query': query,
                'count': len(articles),
                'articles': articles,
                'collected_at': datetime.utcnow().isoformat()
            }

        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'articles': []
            }

    def _parse_date(self, date_str: str) -> str:
        """Parse date string to ISO format"""
        try:
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(date_str)
            return dt.isoformat()
        except:
            return datetime.utcnow().isoformat()


# Standalone function for easy importing
def collect_google_news(query: str, max_results: int = 10) -> Dict[str, Any]:
    """Convenience function to collect Google News"""
    collector = GoogleNewsCollector()
    return collector.collect(query, max_results)


if __name__ == '__main__':
    # Test the collector
    result = collect_google_news('artificial intelligence', max_results=5)
    print(json.dumps(result, indent=2))
