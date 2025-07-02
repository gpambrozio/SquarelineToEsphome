# SquarelineToEsphome Tests

This directory contains comprehensive tests for the SquarelineToEsphome project.

## Running Tests

To run all tests:
```bash
uv run pytest
```

To run tests with verbose output:
```bash
uv run pytest -v
```

To run a specific test file:
```bash
uv run pytest tests/test_conversion.py -v
```

## Test Structure

- `test_conversion.py` - Main conversion functionality tests
- `test_yaml_validation.py` - YAML output validation tests
- `test_images.py` - Image processing and RGB565 conversion tests
- `test_esphome_compilation.py` - ESPHome compilation validation tests
- `conftest.py` - Shared test fixtures
- `utils.py` - Test utility functions
- `projects/` - Directory containing SquareLine test projects
- `base.yaml` - Base ESPHome configuration for compilation testing

## Adding New Test Projects

To add a new SquareLine project for testing:

1. **Create Project Directory**: Create a new directory under `tests/projects/` with your project name:
   ```bash
   mkdir tests/projects/my_new_project
   ```

2. **Add Project Files**: Copy your SquareLine project files into the directory:
   - `.spj` project file (required)
   - `assets/` directory with images (if any)
   - Any other project-related files

3. **Automatic Discovery**: The test suite will automatically discover and test your new project. No code changes are needed!

### Example Project Structure
```
tests/projects/my_new_project/
├── my_project.spj          # SquareLine project file
├── assets/                 # Image assets (optional)
│   ├── image1.png
│   └── image2.png
└── components/             # Other project files (optional)
```

## Test Types

### Conversion Tests (`test_conversion.py`)
- Tests that projects convert without errors
- Validates project file loading
- Tests different output modes (stdout, file, clipboard)
- Error handling for invalid/missing files

### YAML Validation Tests (`test_yaml_validation.py`)
- Ensures generated YAML has valid syntax
- Validates YAML structure contains expected ESPHome LVGL elements
- Tests unicode content handling
- Validates YAML parsing with PyYAML

### Image Tests (`test_images.py`)
- Tests RGB565 image conversion
- Validates support for different image formats (RGB, RGBA, grayscale)
- Tests batch image conversion
- Error handling for invalid images
- Tests on real project assets

### ESPHome Compilation Tests (`test_esphome_compilation.py`)
- Tests that generated YAML compiles successfully with ESPHome
- Validates YAML syntax compatibility with ESPHome parser
- Uses `base.yaml` configuration with proper display/touchscreen setup
- Generates `base_lgvl.yaml` and tests compilation with `esphome config`
- Automatically cleans up generated files after each test
- Distinguishes between YAML syntax errors and configuration errors
- **Requires ESPHome**: Install with `pip install esphome` to enable these tests
- Tests are automatically skipped if ESPHome is not available

## Test Utilities (`utils.py`)

### Key Functions
- `discover_test_projects()` - Automatically finds all test projects
- `validate_yaml_syntax()` - Validates YAML syntax
- `has_images()` - Checks if a project contains image assets
- `load_squareline_project()` - Loads and parses .spj files

## Test Fixtures (`conftest.py`)

### Available Fixtures
- `test_projects_dir` - Path to the test projects directory
- `temp_output_dir` - Temporary directory for test outputs
- `sample_project_path` - Path to the 3d_printer sample project

## Coverage

The test suite covers:
- ✅ Main conversion functionality
- ✅ YAML output validation and structure
- ✅ Image processing (RGB565 conversion)
- ✅ ESPHome compilation validation
- ✅ Error handling and edge cases
- ✅ Multiple output formats
- ✅ Unicode content handling
- ✅ Parametrized testing for multiple projects

## Continuous Integration

Tests are designed to work in CI environments:
- No clipboard dependencies (mocked when needed)
- Temporary file cleanup
- Cross-platform compatibility
- Deterministic test execution
- ESPHome compilation tests are optional (skipped if not available)

## Troubleshooting

### Common Issues

1. **Import Errors**: Make sure you're running tests from the project root:
   ```bash
   cd /path/to/SquarelineToEsphome
   uv run pytest
   ```

2. **Missing Test Projects**: Ensure your project has a `.spj` file in the project directory.

3. **Image Conversion Failures**: Check that your images are valid and supported formats (PNG, JPG, etc.).

4. **ESPHome Compilation Tests Skipped**: Install ESPHome with `pip install esphome` if you want to run the compilation validation tests. These tests are optional and will be skipped if ESPHome is not available.