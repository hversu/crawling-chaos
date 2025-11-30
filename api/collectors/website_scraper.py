"""
Website Scraper Collector
Fetches webpage content and extracts human-readable text and tables
"""
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional
import json


class WebsiteScraperCollector:
    """Scrapes website content and extracts readable text and tables"""

    def __init__(self, timeout: int = 30):
        """
        Initialize website scraper

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

    def collect(self, url: str, extract_tables: bool = True, extract_links: bool = False) -> Dict[str, Any]:
        """
        Scrape a website and extract readable content

        Args:
            url: URL to scrape
            extract_tables: Whether to extract and parse tables
            extract_links: Whether to extract hyperlinks

        Returns:
            Dictionary with status, text content, and optional tables/links
        """
        try:
            from bs4 import BeautifulSoup

            print(f"    Fetching URL: {url}")
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.content, 'lxml')

            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header", "aside"]):
                script.decompose()

            # Extract title
            title = ""
            if soup.title:
                title = soup.title.string.strip() if soup.title.string else ""

            # Extract main text content
            text_content = soup.get_text(separator='\n', strip=True)

            # Clean up whitespace
            lines = [line.strip() for line in text_content.splitlines()]
            lines = [line for line in lines if line]  # Remove empty lines
            cleaned_text = '\n'.join(lines)

            result = {
                'status': 'success',
                'url': url,
                'title': title,
                'text_content': cleaned_text,
                'text_length': len(cleaned_text),
                'collected_at': datetime.utcnow().isoformat()
            }

            # Extract tables if requested
            if extract_tables:
                tables = self._extract_tables(soup)
                result['tables'] = tables
                result['table_count'] = len(tables)
                print(f"    Extracted {len(tables)} table(s)")

            # Extract links if requested
            if extract_links:
                links = self._extract_links(soup, url)
                result['links'] = links
                result['link_count'] = len(links)
                print(f"    Extracted {len(links)} link(s)")

            print(f"    Extracted {len(cleaned_text)} characters of text")

            return result

        except ImportError:
            return {
                'status': 'error',
                'error': 'BeautifulSoup library not installed. Run: pip install beautifulsoup4 lxml',
                'url': url
            }
        except requests.exceptions.Timeout:
            return {
                'status': 'error',
                'error': f'Request timed out after {self.timeout} seconds',
                'url': url
            }
        except requests.exceptions.HTTPError as e:
            return {
                'status': 'error',
                'error': f'HTTP error: {e.response.status_code}',
                'url': url
            }
        except requests.exceptions.RequestException as e:
            return {
                'status': 'error',
                'error': f'Request failed: {str(e)}',
                'url': url
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'url': url
            }

    def _extract_tables(self, soup) -> List[Dict[str, Any]]:
        """Extract and parse HTML tables"""
        tables = []

        for idx, table in enumerate(soup.find_all('table')):
            table_data = {
                'table_id': idx,
                'headers': [],
                'rows': []
            }

            # Extract headers
            headers = table.find_all('th')
            if headers:
                table_data['headers'] = [th.get_text(strip=True) for th in headers]

            # Extract rows
            for row in table.find_all('tr'):
                cells = row.find_all(['td', 'th'])
                if cells:
                    row_data = [cell.get_text(strip=True) for cell in cells]
                    table_data['rows'].append(row_data)

            # Only add non-empty tables
            if table_data['rows']:
                tables.append(table_data)

        return tables

    def _extract_links(self, soup, base_url: str) -> List[Dict[str, str]]:
        """Extract hyperlinks from the page"""
        from urllib.parse import urljoin

        links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            text = link.get_text(strip=True)

            # Convert relative URLs to absolute
            absolute_url = urljoin(base_url, href)

            if text and absolute_url:
                links.append({
                    'text': text,
                    'url': absolute_url
                })

        return links


# Standalone function for easy importing
def scrape_website(url: str, extract_tables: bool = True, extract_links: bool = False, timeout: int = 30) -> Dict[str, Any]:
    """Convenience function to scrape a website"""
    scraper = WebsiteScraperCollector(timeout=timeout)
    return scraper.collect(url, extract_tables, extract_links)


if __name__ == '__main__':
    # Test the collector
    result = scrape_website('https://en.wikipedia.org/wiki/Artificial_intelligence', extract_tables=True)
    print(json.dumps({
        'status': result['status'],
        'title': result.get('title', ''),
        'text_length': result.get('text_length', 0),
        'table_count': result.get('table_count', 0)
    }, indent=2))
