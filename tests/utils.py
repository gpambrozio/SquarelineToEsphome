"""Test utilities for SquarelineToEsphome tests."""

import json
from pathlib import Path
from typing import Dict, List, Tuple

import yaml


def discover_test_projects(projects_dir: Path) -> List[Tuple[str, Path]]:
    """
    Discover all test projects in the projects directory.

    Returns a list of (project_name, project_file_path) tuples.
    """
    projects = []
    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir():
            continue

        # Look for .spj files in the project directory
        spj_files = list(project_dir.glob("*.spj"))
        if spj_files:
            # Use the first .spj file found
            projects.append((project_dir.name, spj_files[0]))

    return projects


def load_squareline_project(project_path: Path) -> Dict:
    """Load and parse a SquareLine project file."""
    with open(project_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def validate_yaml_syntax(yaml_content: str) -> bool:
    """
    Validate that the YAML content has valid syntax.

    Returns True if valid, False otherwise.
    """
    try:
        yaml.safe_load(yaml_content)
        return True
    except yaml.YAMLError:
        return False


def get_project_assets_dir(project_path: Path) -> Path:
    """Get the assets directory for a project."""
    return project_path.parent / "assets"


def has_images(project_path: Path) -> bool:
    """Check if a project has image assets."""
    assets_dir = get_project_assets_dir(project_path)
    if not assets_dir.exists():
        return False

    image_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.gif'}
    for file_path in assets_dir.rglob('*'):
        if file_path.suffix.lower() in image_extensions:
            return True

    return False
