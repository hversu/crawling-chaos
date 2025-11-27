"""
GPT Handler
Interfaces with OpenAI's GPT API for text analysis
"""
import os
from typing import Dict, Any
import json
from openai import OpenAI


class GPTHandler:
    """Handles OpenAI GPT API interactions"""

    def __init__(self, api_key: str = None):
        """
        Initialize GPT handler

        Args:
            api_key: OpenAI API key (or uses OPENAI_API_KEY env var)
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key not provided")

        self.client = OpenAI(api_key=self.api_key)
        self.default_model = "gpt-4-turbo-preview"

    def analyze(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str = None,
        max_tokens: int = 4096,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Send prompts to GPT and get analysis

        Args:
            system_prompt: System prompt for GPT
            user_prompt: User prompt/content to analyze
            model: GPT model to use (default: gpt-4-turbo-preview)
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature

        Returns:
            Dictionary with status and response
        """
        try:
            response = self.client.chat.completions.create(
                model=model or self.default_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )

            # Extract response text
            response_text = response.choices[0].message.content

            return {
                'status': 'success',
                'analysis': response_text,
                'model': response.model,
                'usage': {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                },
                'raw_response': {
                    'id': response.id,
                    'finish_reason': response.choices[0].finish_reason
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
        max_tokens: int = 8192,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Analyze multiple articles together in a single prompt

        Args:
            system_prompt: System prompt for GPT
            articles: List of article dictionaries
            user_prompt_template: Template for formatting the batch prompt
            model: GPT model to use (default: gpt-4-turbo-preview)
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature

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

            response = self.client.chat.completions.create(
                model=model or self.default_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )

            # Extract response text
            response_text = response.choices[0].message.content

            return {
                'status': 'success',
                'analysis': response_text,
                'model': response.model,
                'article_count': len(articles),
                'usage': {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                },
                'raw_response': {
                    'id': response.id,
                    'finish_reason': response.choices[0].finish_reason
                }
            }

        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'analysis': None
            }


def analyze_with_gpt(
    system_prompt: str,
    user_prompt: str,
    api_key: str = None
) -> Dict[str, Any]:
    """
    Convenience function to analyze with GPT

    Args:
        system_prompt: System prompt
        user_prompt: User prompt
        api_key: Optional API key

    Returns:
        Analysis result dictionary
    """
    handler = GPTHandler(api_key=api_key)
    return handler.analyze(system_prompt, user_prompt)


if __name__ == '__main__':
    # Test the handler
    result = analyze_with_gpt(
        system_prompt="You are a helpful news analyst.",
        user_prompt="Summarize this: AI technology is advancing rapidly."
    )
    print(json.dumps(result, indent=2))
