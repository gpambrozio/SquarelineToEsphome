"""Test the main conversion functionality."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from squareline_to_esphome.__main__ import main

from .utils import discover_test_projects, load_squareline_project


class TestConversion:
    """Test the main conversion process."""

    @pytest.mark.parametrize("project_name,project_path",
                           discover_test_projects(Path(__file__).parent / "projects"))
    def test_project_conversion_runs_without_error(self, project_name: str, project_path: Path):
        """Test that conversion runs without errors for all test projects."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as temp_file:
            temp_output = temp_file.name

        try:
            # Mock sys.argv to simulate command line arguments
            test_args = ['squareline-to-esphome', str(project_path), '-o', temp_output]
            with patch('sys.argv', test_args):
                # Should not raise any exceptions
                main()

            # Verify output file was created
            assert Path(temp_output).exists(), f"Output file was not created for {project_name}"

            # Verify output file is not empty
            output_content = Path(temp_output).read_text()
            assert output_content.strip(), f"Output file is empty for {project_name}"

        finally:
            # Clean up temporary file
            if Path(temp_output).exists():
                Path(temp_output).unlink()

    def test_sample_project_loads_correctly(self, sample_project_path: Path):
        """Test that the sample project can be loaded and parsed."""
        project_data = load_squareline_project(sample_project_path)

        # Basic structure validation
        assert isinstance(project_data, dict), "Project data should be a dictionary"
        assert "root" in project_data, "Project should have root"
        assert isinstance(project_data["root"], dict), "Root should be a dictionary"
        assert "children" in project_data["root"], "Root should have children"
        assert isinstance(project_data["root"]["children"], list), "Children should be a list"

    def test_conversion_with_stdout_output(self, sample_project_path: Path, capsys):
        """Test conversion with stdout output."""
        test_args = ['squareline-to-esphome', str(sample_project_path), '--stdout']
        with patch('sys.argv', test_args):
            main()

        captured = capsys.readouterr()
        assert captured.out.strip(), "Should produce output to stdout"

    def test_conversion_with_clipboard_disabled(self, sample_project_path: Path):
        """Test conversion without clipboard to avoid clipboard dependencies in CI."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as temp_file:
            temp_output = temp_file.name

        try:
            test_args = ['squareline-to-esphome', str(sample_project_path), '-o', temp_output]
            with patch('sys.argv', test_args):
                # Mock pyperclip to avoid clipboard operations
                with patch('pyperclip.copy'):
                    main()

            # Verify output was written to file
            assert Path(temp_output).exists()
            output_content = Path(temp_output).read_text()
            assert output_content.strip()

        finally:
            if Path(temp_output).exists():
                Path(temp_output).unlink()

    def test_invalid_project_file_handling(self, temp_output_dir: Path):
        """Test handling of invalid project files."""
        # Create an invalid project file
        invalid_project = temp_output_dir / "invalid.spj"
        invalid_project.write_text("invalid json content")

        test_args = ['squareline-to-esphome', str(invalid_project), '--stdout']
        with patch('sys.argv', test_args):
            # Should handle the error gracefully (may raise SystemExit or JSONDecodeError)
            with pytest.raises((SystemExit, json.JSONDecodeError)):
                main()

    def test_nonexistent_project_file_handling(self):
        """Test handling of nonexistent project files."""
        nonexistent_file = "/path/that/does/not/exist.spj"

        test_args = ['squareline-to-esphome', nonexistent_file, '--stdout']
        with patch('sys.argv', test_args):
            with pytest.raises((SystemExit, FileNotFoundError)):
                main()
