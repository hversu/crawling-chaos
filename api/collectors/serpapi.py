"""
SerpAPI Collector
Fetches Google search results using SerpAPI
"""
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
import json


class SerpAPICollector:
    """Collects search results from Google via SerpAPI"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize SerpAPI collector

        Args:
            api_key: SerpAPI key. If not provided, reads from SERPAPI_API_KEY env var
        """
        self.api_key = api_key or os.getenv('SERPAPI_API_KEY')
        if not self.api_key:
            raise ValueError("SERPAPI_API_KEY not found in environment variables")

    def collect(self, query: str, max_results: int = 10, search_type: str = 'organic') -> Dict[str, Any]:
        """
        Collect search results for a given query

        Args:
            query: Search query string
            max_results: Maximum number of results to return
            search_type: Type of results ('organic', 'news', 'shopping', etc.)

        Returns:
            Dictionary with status and results list
        """
        try:
            from serpapi import GoogleSearch

            params = {
                "q": query,
                "api_key": self.api_key,
                "num": max_results,
                "engine": "google"
            }

            # Add news-specific parameters if requested
            if search_type == 'news':
                params["tbm"] = "nws"

            print(f"    Querying SerpAPI for: {query}")
            search = GoogleSearch(params)
            results = search.get_dict()

            # Check for errors
            if "error" in results:
                return {
                    'status': 'error',
                    'error': results["error"],
                    'results': []
                }

            # Extract results based on search type
            extracted_results = []

            if search_type == 'news' and 'news_results' in results:
                for item in results['news_results'][:max_results]:
                    extracted_results.append({
                        'title': item.get('title', ''),
                        'snippet': item.get('snippet', ''),
                        'url': item.get('link', ''),
                        'source': item.get('source', ''),
                        'date': item.get('date', ''),
                        'thumbnail': item.get('thumbnail', '')
                    })
            elif 'organic_results' in results:
                for item in results['organic_results'][:max_results]:
                    extracted_results.append({
                        'title': item.get('title', ''),
                        'snippet': item.get('snippet', ''),
                        'url': item.get('link', ''),
                        'position': item.get('position', 0),
                        'displayed_link': item.get('displayed_link', '')
                    })

            print(f"    Collected {len(extracted_results)} results from SerpAPI")

            return {
                'status': 'success',
                'query': query,
                'search_type': search_type,
                'count': len(extracted_results),
                'results': extracted_results,
                'collected_at': datetime.utcnow().isoformat(),
                'raw_results': results  # Include full response for debugging
            }

        except ImportError:
            return {
                'status': 'error',
                'error': 'SerpAPI library not installed. Run: pip install google-search-results',
                'results': []
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'results': []
            }


# Standalone function for easy importing
def collect_serpapi_results(query: str, max_results: int = 10, search_type: str = 'organic', api_key: Optional[str] = None) -> Dict[str, Any]:
    """Convenience function to collect SerpAPI results"""
    collector = SerpAPICollector(api_key=api_key)
    return collector.collect(query, max_results, search_type)


if __name__ == '__main__':
    # Test the collector
    result = collect_serpapi_results('artificial intelligence', max_results=5)
    print(json.dumps(result, indent=2))
