"""Test YAML validation and structure."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from squareline_to_esphome.__main__ import main

from .utils import discover_test_projects, validate_yaml_syntax


class TestYAMLValidation:
    """Test YAML output validation."""

    @pytest.mark.parametrize("project_name,project_path",
                           discover_test_projects(Path(__file__).parent / "projects"))
    def test_generated_yaml_is_valid(self, project_name: str, project_path: Path):
        """Test that generated YAML has valid syntax."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as temp_file:
            temp_output = temp_file.name

        try:
            # Generate YAML output
            test_args = ['squareline-to-esphome', str(project_path), '-o', temp_output]
            with patch('sys.argv', test_args):
                with patch('pyperclip.copy'):  # Disable clipboard
                    main()

            # Read and validate the generated YAML
            output_content = Path(temp_output).read_text()
            assert validate_yaml_syntax(output_content), f"Generated YAML is invalid for {project_name}"

        finally:
            if Path(temp_output).exists():
                Path(temp_output).unlink()

    @pytest.mark.parametrize("project_name,project_path",
                           discover_test_projects(Path(__file__).parent / "projects"))
    def test_yaml_contains_expected_structure(self, project_name: str, project_path: Path):
        """Test that generated YAML contains expected ESPHome LVGL structure."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as temp_file:
            temp_output = temp_file.name

        try:
            # Generate YAML output
            test_args = ['squareline-to-esphome', str(project_path), '-o', temp_output]
            with patch('sys.argv', test_args):
                with patch('pyperclip.copy'):  # Disable clipboard
                    main()

            # Parse and validate structure
            output_content = Path(temp_output).read_text()
            yaml_data = yaml.safe_load(output_content)

            # Should be a dictionary
            assert isinstance(yaml_data, dict), f"YAML root should be a dictionary for {project_name}"

            # Should have either 'lvgl' key (if it's a full config) or 'pages'/'widgets' (if it's partial)
            has_lvgl_structure = (
                'lvgl' in yaml_data or
                any(key in yaml_data for key in ['pages', 'widgets', 'image'])
            )
            assert has_lvgl_structure, f"YAML should contain LVGL structure for {project_name}"

        finally:
            if Path(temp_output).exists():
                Path(temp_output).unlink()

    def test_yaml_validation_utility_function(self):
        """Test the YAML validation utility function."""
        # Valid YAML
        valid_yaml = """
        key: value
        list:
          - item1
          - item2
        nested:
          subkey: subvalue
        """
        assert validate_yaml_syntax(valid_yaml)

        # Invalid YAML
        invalid_yaml = """
        key: value
        invalid: [unclosed bracket
        """
        assert not validate_yaml_syntax(invalid_yaml)

        # Empty YAML (should be valid)
        assert validate_yaml_syntax("")

        # YAML with special characters that might cause issues
        special_yaml = """
text_with_quotes: "This has 'single' and double quotes"
multiline: |
  This is a
  multiline string
        """
        assert validate_yaml_syntax(special_yaml)

    def test_yaml_handles_unicode_content(self, sample_project_path: Path):
        """Test that YAML generation handles unicode content properly."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as temp_file:
            temp_output = temp_file.name

        try:
            test_args = ['squareline-to-esphome', str(sample_project_path), '-o', temp_output]
            with patch('sys.argv', test_args):
                with patch('pyperclip.copy'):
                    main()

            # Read the file with UTF-8 encoding
            output_content = Path(temp_output).read_text(encoding='utf-8')

            # Should be valid YAML
            assert validate_yaml_syntax(output_content)

            # Should be parseable with PyYAML
            yaml_data = yaml.safe_load(output_content)
            assert yaml_data is not None

        finally:
            if Path(temp_output).exists():
                Path(temp_output).unlink()
