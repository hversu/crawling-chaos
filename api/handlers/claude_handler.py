"""
Claude Handler
Interfaces with Anthropic's Claude API for text analysis
"""
import os
from typing import Dict, Any
import json
from anthropic import Anthropic


class ClaudeHandler:
    """Handles Claude API interactions"""

    def __init__(self, api_key: str = None):
        """
        Initialize Claude handler

        Args:
            api_key: Anthropic API key (or uses ANTHROPIC_API_KEY env var)
        """
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("Anthropic API key not provided")

        self.client = Anthropic(api_key=self.api_key)
        self.default_model = "claude-3-5-sonnet-20241022"

    def analyze(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str = None,
        max_tokens: int = 4096
    ) -> Dict[str, Any]:
        """
        Send prompts to Claude and get analysis

        Args:
            system_prompt: System prompt for Claude
            user_prompt: User prompt/content to analyze
            model: Claude model to use (default: claude-3-5-sonnet-20241022)
            max_tokens: Maximum tokens in response

        Returns:
            Dictionary with status and response
        """
        try:
            message = self.client.messages.create(
                model=model or self.default_model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )

            # Extract text content from response
            response_text = ""
            if message.content:
                for block in message.content:
                    if hasattr(block, 'text'):
                        response_text += block.text

            return {
                'status': 'success',
                'analysis': response_text,
                'model': message.model,
                'usage': {
                    'input_tokens': message.usage.input_tokens,
                    'output_tokens': message.usage.output_tokens
                },
                'raw_response': {
                    'id': message.id,
                    'type': message.type,
                    'role': message.role
                }
            }

        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'analysis': None
            }

    def analyze_batch(
        self,
        system_prompt: str,
        articles: list,
        user_prompt_template: str,
        model: str = None,
        max_tokens: int = 8192
    ) -> Dict[str, Any]:
        """
        Analyze multiple articles together in a single prompt

        Args:
            system_prompt: System prompt for Claude
            articles: List of article dictionaries
            user_prompt_template: Template for formatting the batch prompt
            model: Claude model to use (default: claude-3-5-sonnet-20241022)
            max_tokens: Maximum tokens in response

        Returns:
            Dictionary with status and response
        """
        try:
            # Format all articles into a single prompt
            articles_text = ""
            for idx, article in enumerate(articles, 1):
                articles_text += f"\n--- Article {idx} ---\n"
                articles_text += f"Title: {article.get('title', 'N/A')}\n"
                articles_text += f"Source: {article.get('source', 'Unknown')}\n"
                articles_text += f"Published: {article.get('publish_date', 'N/A')}\n"
                articles_text += f"URL: {article.get('url', 'N/A')}\n"
                articles_text += f"Summary: {article.get('summary', 'N/A')}\n"

            # Use template or default format
            user_prompt = user_prompt_template.format(
                article_count=len(articles),
                articles=articles_text
            )

            message = self.client.messages.create(
                model=model or self.default_model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )

            # Extract text content from response
            response_text = ""
            if message.content:
                for block in message.content:
                    if hasattr(block, 'text'):
                        response_text += block.text

            return {
                'status': 'success',
                'analysis': response_text,
                'model': message.model,
                'article_count': len(articles),
                'usage': {
                    'input_tokens': message.usage.input_tokens,
                    'output_tokens': message.usage.output_tokens
                },
                'raw_response': {
                    'id': message.id,
                    'type': message.type,
                    'role': message.role
                }
            }

        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'analysis': None
            }


def analyze_with_claude(
    system_prompt: str,
    user_prompt: str,
    api_key: str = None
) -> Dict[str, Any]:
    """
    Convenience function to analyze with Claude

    Args:
        system_prompt: System prompt
        user_prompt: User prompt
        api_key: Optional API key

    Returns:
        Analysis result dictionary
    """
    handler = ClaudeHandler(api_key=api_key)
    return handler.analyze(system_prompt, user_prompt)


if __name__ == '__main__':
    # Test the handler
    result = analyze_with_claude(
        system_prompt="You are a helpful news analyst.",
        user_prompt="Summarize this: AI technology is advancing rapidly."
    )
    print(json.dumps(result, indent=2))
