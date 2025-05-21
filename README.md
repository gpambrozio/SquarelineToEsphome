# SquarelineToEsphome

SquarelineToEsphome is a tool that converts UI projects created with [SquareLine Studio](https://squareline.io/) into configuration files compatible with [ESPHome](https://esphome.io/). This enables you to design user interfaces visually and deploy them to ESP32/ESP8266 devices using ESPHome.

## Features

- Parses SquareLine Studio project files.
- Generates ESPHome YAML configuration for UI elements.
- Supports common widgets (buttons, labels, sliders, etc.).
- Simplifies integration of custom GUIs with ESPHome projects.

## Usage

1. Export your project from SquareLine Studio.
2. Run the converter tool:
    ```sh
    python squareline_to_esphome.py path/to/project.sqproj
    ```
3. Use the generated YAML in your ESPHome configuration.

## Requirements

- Python 3.7+

Install dependencies:
```sh
pip install -r requirements.txt
```

## License

MIT License

## Disclaimer

This project is not affiliated with SquareLine Studio or ESPHome.
