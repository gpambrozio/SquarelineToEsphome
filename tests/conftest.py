"""Shared test fixtures and utilities for SquarelineToEsphome tests."""

import tempfile
from pathlib import Path
from typing import Generator

import pytest


@pytest.fixture
def test_projects_dir() -> Path:
    """Return the path to the test projects directory."""
    return Path(__file__).parent / "projects"


@pytest.fixture
def temp_output_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test outputs."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def sample_project_path(test_projects_dir: Path) -> Path:
    """Return the path to the 3d_printer test project."""
    project_path = test_projects_dir / "3d_printer" / "3d_printer.spj"
    if not project_path.exists():
        pytest.skip(f"Test project not found: {project_path}")
    return project_path
