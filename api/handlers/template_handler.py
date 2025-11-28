"""
Template Handler
Manages execution templates that define workflows for jobs
"""
import os
import json
from typing import Dict, Any, Optional, List


class TemplateHandler:
    """Handles loading and parsing of execution templates"""

    def __init__(self, template_dir: str = None):
        """
        Initialize template handler

        Args:
            template_dir: Directory containing template JSON files
        """
        if template_dir is None:
            template_dir = os.path.join(os.path.dirname(__file__), '..', 'templates')

        self.template_dir = template_dir
        self._templates_cache = {}

    def load_template(self, template_name: str) -> Optional[Dict[str, Any]]:
        """
        Load a template by name

        Args:
            template_name: Name of the template (without .json extension)

        Returns:
            Template dictionary or None if not found
        """
        # Check cache first
        if template_name in self._templates_cache:
            return self._templates_cache[template_name]

        # Load from file
        template_path = os.path.join(self.template_dir, f'{template_name}.json')

        try:
            with open(template_path, 'r') as f:
                template = json.load(f)

            # Validate template structure
            if not self._validate_template(template):
                print(f"Invalid template structure: {template_name}")
                return None

            # Cache and return
            self._templates_cache[template_name] = template
            return template

        except FileNotFoundError:
            print(f"Template not found: {template_name}")
            return None
        except json.JSONDecodeError as e:
            print(f"Invalid JSON in template {template_name}: {e}")
            return None

    def list_templates(self) -> List[str]:
        """
        List all available templates

        Returns:
            List of template names (without .json extension)
        """
        try:
            files = os.listdir(self.template_dir)
            templates = [f.replace('.json', '') for f in files if f.endswith('.json')]
            return templates
        except Exception as e:
            print(f"Error listing templates: {e}")
            return []

    def get_collectors(self, template: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get collectors from template

        Args:
            template: Template dictionary

        Returns:
            List of collector configurations
        """
        return template.get('workflow', {}).get('collectors', [])

    def get_analyzers(self, template: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get analyzers from template

        Args:
            template: Template dictionary

        Returns:
            List of analyzer configurations
        """
        return template.get('workflow', {}).get('analyzers', [])

    def _validate_template(self, template: Dict[str, Any]) -> bool:
        """
        Validate template structure

        Args:
            template: Template dictionary to validate

        Returns:
            True if valid, False otherwise
        """
        # Required fields
        if 'name' not in template:
            return False

        if 'workflow' not in template:
            return False

        workflow = template['workflow']

        # Must have at least collectors or analyzers
        if not workflow.get('collectors') and not workflow.get('analyzers'):
            return False

        return True


if __name__ == '__main__':
    # Test template handler
    handler = TemplateHandler()
    templates = handler.list_templates()
    print(f"Available templates: {templates}")

    for template_name in templates:
        template = handler.load_template(template_name)
        if template:
            print(f"\nTemplate: {template_name}")
            print(f"  Collectors: {len(handler.get_collectors(template))}")
            print(f"  Analyzers: {len(handler.get_analyzers(template))}")
