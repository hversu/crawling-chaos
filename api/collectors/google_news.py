"""
Google News Collector
Fetches news articles based on query string using Google News RSS feed
"""
import feedparser
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json


class GoogleNewsCollector:
    """Collects news from Google News RSS feed"""

    BASE_URL = "https://news.google.com/rss/search"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def collect(self, query: str, max_results: int = 10, days_to_lookback: Optional[int] = None) -> Dict[str, Any]:
        """
        Collect news articles for a given query

        Args:
            query: Search query string
            max_results: Maximum number of results to return
            days_to_lookback: Optional number of days to look back for articles (filters out older articles)

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

            # Calculate cutoff date if days_to_lookback is specified
            cutoff_date = None
            cutoff_date_aware = None
            if days_to_lookback is not None and days_to_lookback > 0:
                cutoff_date = datetime.utcnow() - timedelta(days=days_to_lookback)

            print(f"    Feed returned {len(feed.entries)} total entries")
            if cutoff_date:
                print(f"    Cutoff date: {cutoff_date.isoformat()}")

            articles = []
            filtered_count = 0
            date_parse_failures = 0

            for entry in feed.entries:
                # Parse the article date
                publish_date_str = self._parse_date(entry.get('published', ''))

                # Filter by date if cutoff is specified
                if cutoff_date:
                    try:
                        publish_date = datetime.fromisoformat(publish_date_str.replace('Z', '+00:00'))

                        # Make cutoff_date timezone-aware once
                        if cutoff_date_aware is None and publish_date.tzinfo is not None:
                            from datetime import timezone
                            cutoff_date_aware = cutoff_date.replace(tzinfo=timezone.utc)

                        # Use timezone-aware cutoff if available
                        compare_cutoff = cutoff_date_aware if cutoff_date_aware else cutoff_date

                        # Debug: print first few article dates
                        if filtered_count + len(articles) < 3:
                            print(f"    Article date: {publish_date.isoformat()}, Cutoff: {compare_cutoff.isoformat()}, Pass: {publish_date >= compare_cutoff}")

                        # Skip articles older than cutoff
                        if publish_date < compare_cutoff:
                            filtered_count += 1
                            continue
                    except Exception as e:
                        # If date parsing fails, include the article
                        date_parse_failures += 1
                        if date_parse_failures <= 2:
                            print(f"    Date parse error: {e} for date: {publish_date_str}")
                        pass

                article = {
                    'title': entry.get('title', ''),
                    'summary': entry.get('summary', ''),
                    'url': entry.get('link', ''),
                    'publish_date': publish_date_str,
                    'source': entry.get('source', {}).get('title', 'Unknown')
                }
                articles.append(article)

                # Stop if we've reached max_results
                if len(articles) >= max_results:
                    break

            if days_to_lookback and filtered_count > 0:
                print(f"    Filtered out {filtered_count} articles older than {days_to_lookback} days")
            print(f"    Collected {len(articles)} articles")

            return {
                'status': 'success',
                'query': query,
                'count': len(articles),
                'articles': articles,
                'collected_at': datetime.utcnow().isoformat(),
                'days_to_lookback': days_to_lookback
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
def collect_google_news(query: str, max_results: int = 10, days_to_lookback: Optional[int] = None) -> Dict[str, Any]:
    """Convenience function to collect Google News"""
    collector = GoogleNewsCollector()
    return collector.collect(query, max_results, days_to_lookback)


if __name__ == '__main__':
    # Test the collector
    result = collect_google_news('artificial intelligence', max_results=5)
    print(json.dumps(result, indent=2))
