"""Collectors package for data collection modules"""
from .google_news import GoogleNewsCollector, collect_google_news

__all__ = ['GoogleNewsCollector', 'collect_google_news']
