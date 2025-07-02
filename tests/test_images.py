"""Test image conversion functionality."""

from pathlib import Path

import pytest
from PIL import Image

from squareline_to_esphome.__main__ import convert_all_images, convert_to_rgb565

from .utils import discover_test_projects, get_project_assets_dir, has_images


class TestImageConversion:
    """Test image processing and conversion."""

    def test_rgb565_conversion_basic(self, temp_output_dir: Path):
        """Test basic RGB565 conversion functionality."""
        # Create a simple test image
        test_image_path = temp_output_dir / "test.png"

        # Create a small RGB image
        img = Image.new('RGB', (10, 10), color='red')
        img.save(test_image_path)

        # Convert to RGB565
        converted_path = convert_to_rgb565(str(test_image_path))

        # Verify the converted file exists
        assert Path(converted_path).exists(), "RGB565 converted file should exist"

        # Verify the naming convention
        expected_name = temp_output_dir / "test_RGB565.png"
        assert Path(converted_path) == expected_name, "RGB565 file should have correct naming"

    def test_rgb565_conversion_with_alpha(self, temp_output_dir: Path):
        """Test RGB565 conversion with alpha channel."""
        # Create a test image with alpha
        test_image_path = temp_output_dir / "test_alpha.png"

        # Create an RGBA image
        img = Image.new('RGBA', (10, 10), color=(255, 0, 0, 128))  # Semi-transparent red
        img.save(test_image_path)

        # Convert to RGB565
        converted_path = convert_to_rgb565(str(test_image_path))

        # Should create RGB565 file
        assert Path(converted_path).exists(), "RGB565 converted file should exist"

        # Verify the converted image can be opened and has correct mode
        with Image.open(converted_path) as converted_img:
            assert converted_img.mode == 'RGBA', "Converted image should be RGBA"

    def test_convert_all_images_function(self, temp_output_dir: Path):
        """Test the convert_all_images function."""
        # Create test images
        img1_path = temp_output_dir / "image1.png"
        img2_path = temp_output_dir / "image2.png"

        Image.new('RGB', (5, 5), color='blue').save(img1_path)
        Image.new('RGB', (5, 5), color='green').save(img2_path)

        # Create images dictionary like the main code would
        images = {
            "img1": "image1.png",
            "img2": "image2.png",
        }

        # Convert all images
        converted = convert_all_images(str(temp_output_dir), images)

        # Verify conversions
        assert len(converted) == 2, "Should convert all images"
        assert "img1" in converted, "Should contain first image"
        assert "img2" in converted, "Should contain second image"

        # Verify converted files exist
        for converted_path in converted.values():
            assert Path(converted_path).exists(), f"Converted file should exist: {converted_path}"

    def test_convert_all_images_with_empty_entries(self, temp_output_dir: Path):
        """Test convert_all_images handles empty image entries."""
        # Create one valid image
        img_path = temp_output_dir / "valid.png"
        Image.new('RGB', (5, 5), color='red').save(img_path)

        images = {
            "valid": "valid.png",
            "empty": "",  # Empty entry should be skipped
        }

        # Should not crash and should skip empty entries
        converted = convert_all_images(str(temp_output_dir), images)

        assert len(converted) == 1, "Should only convert non-empty images"
        assert "valid" in converted, "Should contain valid image"
        assert "empty" not in converted, "Should skip empty entries"

    @pytest.mark.parametrize("project_name,project_path",
                           [p for p in discover_test_projects(Path(__file__).parent / "projects")
                            if has_images(p[1])])
    def test_real_project_image_conversion(self, project_name: str, project_path: Path):
        """Test image conversion on real project images."""
        assets_dir = get_project_assets_dir(project_path)

        # Find PNG images in the assets directory
        png_files = list(assets_dir.glob("*.png"))

        if not png_files:
            pytest.skip(f"No PNG files found in {project_name} assets")

        # Test conversion of the first PNG file
        test_image = png_files[0]

        try:
            converted_path = convert_to_rgb565(str(test_image))

            # Verify conversion succeeded
            assert Path(converted_path).exists(), f"Conversion failed for {test_image.name}"

            # Verify it's a valid image
            with Image.open(converted_path):
                pass  # Just verify it can be opened

        except Exception as e:
            pytest.fail(f"Image conversion failed for {test_image.name}: {e}")

    def test_image_conversion_error_handling(self, temp_output_dir: Path):
        """Test error handling in image conversion."""
        # Test with non-existent file
        non_existent = temp_output_dir / "does_not_exist.png"

        # The function prints error but doesn't raise exception
        result = convert_to_rgb565(str(non_existent))
        assert result is None, "Should return None for non-existent file"

        # Test with invalid image file
        invalid_image = temp_output_dir / "invalid.png"
        invalid_image.write_text("not an image")

        # The function prints error but doesn't raise exception
        result = convert_to_rgb565(str(invalid_image))
        assert result is None, "Should return None for invalid image"

    def test_image_formats_support(self, temp_output_dir: Path):
        """Test support for different image formats."""
        formats_to_test = [
            ('RGB', 'test.png'),
            ('RGBA', 'test_alpha.png'),
            ('L', 'test_grayscale.png'),  # Grayscale
        ]

        for mode, filename in formats_to_test:
            image_path = temp_output_dir / filename
            img = Image.new(mode, (8, 8), color='white' if mode == 'L' else (255, 255, 255))
            img.save(image_path)

            # Should not raise an exception
            converted_path = convert_to_rgb565(str(image_path))
            assert Path(converted_path).exists(), f"Conversion failed for {mode} format"
