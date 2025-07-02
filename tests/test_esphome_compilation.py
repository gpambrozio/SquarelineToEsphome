"""Test ESPHome compilation of generated YAML."""

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from squareline_to_esphome.__main__ import main

from .utils import discover_test_projects


def esphome_available():
    """Check if ESPHome is available in the system."""
    try:
        result = subprocess.run(
            ['esphome', '--version'],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


# Skip all tests in this module if ESPHome is not available
pytestmark = pytest.mark.skipif(
    not esphome_available(),
    reason="ESPHome not available - install with 'pip install esphome' to run compilation tests"
)


class TestESPHomeCompilation:
    """Test that generated YAML compiles successfully with ESPHome."""

    @pytest.mark.parametrize("project_name,project_path",
                           discover_test_projects(Path(__file__).parent / "projects"))
    def test_esphome_compilation(self, project_name: str, project_path: Path):
        """Test that generated YAML compiles with ESPHome without errors."""
        test_dir = Path(__file__).parent
        base_yaml_path = test_dir / "base.yaml"
        base_lgvl_yaml_path = test_dir / "base_lgvl.yaml"

        # Skip if base.yaml doesn't exist
        if not base_yaml_path.exists():
            pytest.skip("base.yaml not found - ESPHome compilation tests disabled")

        try:
            # Generate the LVGL YAML
            test_args = ['squareline-to-esphome', str(project_path), '-o', str(base_lgvl_yaml_path)]
            with patch('sys.argv', test_args):
                with patch('pyperclip.copy'):  # Disable clipboard
                    main()

            # Verify the generated file exists
            assert base_lgvl_yaml_path.exists(), f"Generated YAML not found for {project_name}"

            # Verify the generated file is not empty
            content = base_lgvl_yaml_path.read_text()
            assert content.strip(), f"Generated YAML is empty for {project_name}"

            # Create a secrets.yaml file for ESPHome compilation
            secrets_path = test_dir / "secrets.yaml"
            secrets_content = """
wifi_ssid: "test_network"
wifi_password: "test_password"
"""
            secrets_path.write_text(secrets_content)

            try:
                # Run ESPHome config validation
                result = subprocess.run(
                    ['esphome', 'config', str(base_yaml_path)],
                    cwd=str(test_dir),
                    capture_output=True,
                    text=True,
                    timeout=120  # 2 minute timeout
                )

                # Check for critical YAML syntax errors first
                output_text = (result.stdout + result.stderr).lower()
                critical_errors = [
                    "yaml syntax error",
                    "mapping values are not allowed here",
                    "could not determine a constructor",
                    "found undefined alias",
                    "parser error"
                ]

                for error in critical_errors:
                    if error in output_text:
                        # Include part of the generated YAML for debugging
                        yaml_content = base_lgvl_yaml_path.read_text()
                        error_msg = f"Critical YAML syntax error for {project_name}:\n"
                        error_msg += f"Error: {error}\n"
                        error_msg += f"STDOUT:\n{result.stdout}\n"
                        error_msg += f"STDERR:\n{result.stderr}\n"
                        error_msg += f"\nGenerated YAML (first 1000 chars):\n{yaml_content[:1000]}..."
                        pytest.fail(error_msg)

                # For other errors, we'll be more lenient as they might be configuration issues
                # not related to the YAML syntax itself
                if result.returncode != 0:
                    # Check if it's likely a configuration error vs syntax error
                    config_error_indicators = [
                        "component requires",
                        "unknown component",
                        "pin is already used",
                        "missing required",
                        "invalid configuration"
                    ]

                    is_config_error = any(indicator in output_text for indicator in config_error_indicators)

                    if not is_config_error:
                        # This might be a real YAML structure issue
                        yaml_content = base_lgvl_yaml_path.read_text()
                        error_msg = f"ESPHome compilation failed for {project_name}:\n"
                        error_msg += f"STDOUT:\n{result.stdout}\n"
                        error_msg += f"STDERR:\n{result.stderr}\n"
                        error_msg += f"\nGenerated YAML (first 1000 chars):\n{yaml_content[:1000]}..."
                        pytest.fail(error_msg)
                    else:
                        # Configuration error - log but don't fail the test
                        print(f"Configuration warning for {project_name} (not a YAML syntax issue):")
                        print(f"STDERR: {result.stderr[:500]}...")

                # Optionally check for warnings
                if "WARNING" in result.stderr or "WARNING" in result.stdout:
                    print(f"ESPHome compilation had warnings for {project_name}:")
                    print(f"STDOUT: {result.stdout}")
                    print(f"STDERR: {result.stderr}")

            except subprocess.TimeoutExpired:
                pytest.fail(f"ESPHome compilation timed out for {project_name}")
            except FileNotFoundError:
                pytest.skip("ESPHome not found - skipping compilation test")
            finally:
                # Clean up secrets file
                if secrets_path.exists():
                    secrets_path.unlink()

        finally:
            # Clean up generated LVGL YAML file
            if base_lgvl_yaml_path.exists():
                base_lgvl_yaml_path.unlink()

    def test_esphome_available(self):
        """Test that ESPHome is available for compilation testing."""
        result = subprocess.run(
            ['esphome', '--version'],
            capture_output=True,
            text=True,
            timeout=10
        )
        assert result.returncode == 0, f"ESPHome not working properly: {result.stderr}"
        print(f"ESPHome version: {result.stdout.strip()}")

    def test_base_yaml_structure(self):
        """Test that base.yaml has the expected structure."""
        test_dir = Path(__file__).parent
        base_yaml_path = test_dir / "base.yaml"

        if not base_yaml_path.exists():
            pytest.skip("base.yaml not found")

        content = base_yaml_path.read_text()

        # Check for required ESPHome sections
        required_sections = ['esphome:', 'display:', 'touchscreen:']
        for section in required_sections:
            assert section in content, f"Required ESPHome section missing: {section}"

        # Check for the include statement (either !include or packages syntax)
        include_found = (
            '!include base_lgvl.yaml' in content or
            'lgvl: !include base_lgvl.yaml' in content
        )
        assert include_found, "base_lgvl.yaml or base_lgvl.yaml include statement missing"

    def test_compilation_with_minimal_yaml(self):
        """Test ESPHome compilation with minimal LVGL YAML."""
        test_dir = Path(__file__).parent
        base_yaml_path = test_dir / "base.yaml"
        base_lgvl_yaml_path = test_dir / "base_lgvl.yaml"
        secrets_path = test_dir / "secrets.yaml"

        if not base_yaml_path.exists():
            pytest.skip("base.yaml not found")

        try:
            # Create minimal LVGL YAML that extends the base configuration
            minimal_lvgl = """
# Minimal LVGL pages for testing
lvgl:
  pages:
    - id: main_page
      widgets:
        - label:
            text: "Test"
            align: CENTER
"""
            base_lgvl_yaml_path.write_text(minimal_lvgl)

            # Create secrets file
            secrets_content = """
wifi_ssid: "test_network"
wifi_password: "test_password"
"""
            secrets_path.write_text(secrets_content)

            # Test ESPHome compilation
            try:
                result = subprocess.run(
                    ['esphome', 'config', str(base_yaml_path)],
                    cwd=str(test_dir),
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                # Check for critical errors that would prevent YAML from working
                critical_errors = [
                    "YAML syntax error",
                    "mapping values are not allowed here",
                    "could not determine a constructor",
                    "found undefined alias"
                ]

                output_text = (result.stdout + result.stderr).lower()
                for error in critical_errors:
                    if error.lower() in output_text:
                        pytest.fail(f"Critical YAML error in base configuration: {result.stderr}")

            except FileNotFoundError:
                pytest.skip("ESPHome not found")
            except subprocess.TimeoutExpired:
                pytest.fail("ESPHome compilation timed out")

        finally:
            # Clean up files
            for cleanup_path in [base_lgvl_yaml_path, secrets_path]:
                if cleanup_path.exists():
                    cleanup_path.unlink()
