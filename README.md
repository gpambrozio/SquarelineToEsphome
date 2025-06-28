# SquarelineToEsphome

SquarelineToEsphome is a tool that converts UI projects created with [SquareLine Studio](https://squareline.io/) into configuration files compatible with [ESPHome](https://esphome.io/). This enables you to design user interfaces visually and deploy them to ESP32/ESP8266 devices using ESPHome.

## Features

- Parses SquareLine Studio project files.
- Generates ESPHome YAML configuration for UI elements.
- Supports common widgets (buttons, labels, sliders, etc.).
- **Converts SquareLine Studio events and actions into ESPHome-compatible handlers.**
- **Supports custom widgets through special textarea syntax.**
- Simplifies integration of custom GUIs with ESPHome projects.

## Usage

1. Save your project in SquareLine Studio.
2. Make sure to have `uv` installed. Follow instructions [here](https://github.com/astral-sh/uv?tab=readme-ov-file#installation)
3. Run the converter tool:
    ```sh
    uv run squareline-to-esphome path/to/project.sqproj
    ```
4. Use the generated YAML in your ESPHome configuration.

> **Tip**: Take advantage of event actions and custom widgets to create more interactive and feature-rich UIs. See the [Advanced Features](#advanced-features) section below for details.

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

## Advanced Features

### Event Actions

SquarelineToEsphome automatically converts SquareLine Studio event handlers into ESPHome-compatible actions. When you add event handlers to widgets in SquareLine Studio, they'll be converted to the appropriate ESPHome syntax.

#### Supported Events

The tool supports these SquareLine Studio events:
- `PRESSED` → `on_press`
- `CLICKED` → `on_click` 
- `SHORT_CLICKED` → `on_short_click`
- `LONG_PRESSED` → `on_long_press`
- `RELEASED` → `on_release`
- `VALUE_CHANGED` → `on_change`
- `CHECKED` → `on_value`
- Gesture events: `GESTURE_LEFT/RIGHT/UP/DOWN` → `on_swipe_left/right/up/down`
- Focus events: `FOCUSED/DEFOCUSED` → `on_focus/defocus`

#### Action Types

**1. CALL FUNCTION Actions**
When you add a "CALL FUNCTION" action in SquareLine Studio, it generates ESPHome lambda expressions:

```yaml
button:
  - id: my_button
    on_click:
      then:
        - lambda: id(my_script)->execute(x);
```

**2. LABEL_PROPERTY Actions** 
Label property changes become ESPHome service calls:

```yaml
button:
  - id: trigger_button
    on_click:
      then:
        - lvgl.label.update:
            id: target_label
            text: "New Text"
```

### Custom Widgets

You can define custom ESPHome LVGL widgets that aren't directly supported by SquareLine Studio using a special textarea syntax.

#### How to Use Custom Widgets

1. **In SquareLine Studio**: Create a TEXTAREA widget
2. **Set the text content** to start with `>custom` on the first line
3. **Add YAML configuration** on subsequent lines defining your custom widget

#### Example: Custom QR Code

In SquareLine Studio, create a textarea with this content:
```
>custom
qrcode:
  text: !secret api_url
  size: 150
  light_color: 0xFFFFFF
  dark_color: 0x000000
```

This will be converted to a proper ESPHome QR code widget instead of a textarea. Note that you can use `!secret` and `!include` directives in the YAML configuration.

#### Custom Widget Requirements

- Text must start with `>custom` on the first line
- Following lines must contain valid YAML
- YAML must have exactly one root key (the widget type)
- The widget type must be supported by ESPHome's LVGL component

This feature allows you to use the full power of ESPHome's LVGL widgets while maintaining the visual design workflow of SquareLine Studio.

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
