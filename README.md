# SquarelineToEsphome

SquarelineToEsphome is a tool that converts UI projects created with [SquareLine Studio](https://squareline.io/) into configuration files compatible with [ESPHome](https://esphome.io/). This enables you to design user interfaces visually and deploy them to ESP32/ESP8266 devices using ESPHome.

## Features

- Parses SquareLine Studio project files.
- Generates ESPHome YAML configuration for UI elements.
- Supports common widgets (buttons, labels, sliders, etc.).
- Simplifies integration of custom GUIs with ESPHome projects.

## Usage

1. Save your project in SquareLine Studio.
2. Run the converter tool:
    ```sh
    python squareline_to_esphome.py path/to/project.sqproj
    ```
   Or, if you are using [uv](https://github.com/astral-sh/uv) for dependency management:
    ```sh
    uv run squareline-to-esphome path/to/project.sqproj
    ```
3. Use the generated YAML in your ESPHome configuration.

### Command Line Options

You can control the output and behavior of the tool with these options:

- `-o, --output <file>`: Write the generated YAML to the specified file.
- `-c, --clipboard`: Copy the generated YAML to the clipboard.
- `-s, --stdout`: Print the generated YAML to standard output (default if no output option is specified).
- `-m, --monitor`: Monitor the input file for changes and re-run the conversion automatically. Press `q` to quit monitoring.

Example:
```sh
uv run squareline-to-esphome path/to/project.sqproj --output ui.yaml --monitor
```

## Requirements

- Python 3.7+

Install dependencies:
```sh
pip install -r requirements.txt
```
Or with uv:
```sh
uv sync
```

## License

MIT License

## Disclaimer

This project is not affiliated with SquareLine Studio or ESPHome.
