#!/usr/bin/env python3
"""
squareline-to-esphome.py  -  Convert SquareLine *.spj JSON to ESPHome-LVGL YAML.
"""

import argparse
import json
import os
import os.path
import re
import sys
import threading
import time
from pathlib import Path

import pyperclip
import yaml
from PIL import Image

from squareline_to_esphome.action_handlers import event_parser

# SquareLine object type → ESPHome YAML widget keyword
TYPE_MAP = {
    # Basic widgets
    "LABEL": "label",
    "BUTTON": "button",
    "IMAGE": "image",
    "PANEL": "obj",  # Panel maps to generic obj in ESPHome
    "CONTAINER": "obj",  # Container also maps to obj
    "TEXTAREA": "textarea",
    "TABVIEW": "tabview",
    "TABPAGE": "tab",
    # Controller widgets
    "CHECKBOX": "checkbox",
    "DROPDOWN": "dropdown",
    "KEYBOARD": "keyboard",
    "ROLLER": "roller",
    "SCREEN": "screen",
    "SLIDER": "slider",
    "SWITCH": "switch",
    "SPINBOX": "spinbox",
    # Visualizer widgets
    "BAR": "bar",
    "ARC": "arc",
    "SPINNER": "spinner",
}


# Style property mapping with lambdas for proper conversion
STYLE_PROPERTY_MAP = {
    # Background styles
    "_style/Bg_Color": lambda v: color_opa("bg_color", "bg_opa", v),
    "_style/Bg_gradiens_Color": lambda v: {"bg_grad_color": hex_color(v["intarray"])},
    "_style/Gradient direction": lambda v: {"bg_grad_dir": v["strval"].lower()},
    "_style/Bg_gradient_params": lambda v: {
        "bg_main_stop": v["intarray"][0],
        "bg_grad_stop": v["intarray"][1],
    },
    "_style/Bg_Image": lambda v: {"bg_image_src": v["strval"]},
    "_style/Bg_Image_Opa": lambda v: {"bg_image_opa": v["integer"]},
    "_style/Bg_Image_Recolor": lambda v: color_opa(
        "bg_image_recolor", "bg_image_recolor_opa", v
    ),
    "_style/Bg_Image_Tiled": lambda v: {
        "bg_image_tiled": v["strval"].lower() == "true"
    },
    # Border styles
    "_style/Border_Color": lambda v: color_opa("border_color", "border_opa", v),
    "_style/Border width": lambda v: {"border_width": v.get("integer", 0)},
    "_style/Border side": lambda v: {
        "border_side": ["TOP", "BOTTOM", "LEFT", "RIGHT"]
        if v["strval"] == "FULL"
        else v["strval"]
    },
    "_style/Border post": lambda v: {"border_post": v["strval"].lower() == "true"},
    # Image styles
    "_style/Image_reColor": lambda v: color_opa(
        "image_recolor", "image_recolor_opa", v
    ),
    # Text styles
    "_style/Text_Color": lambda v: color_opa("text_color", "text_opa", v),
    "_style/Text_Font": lambda v: {"text_font": v["strval"]},
    "_style/Text_Letter_Space": lambda v: {"text_letter_space": v["integer"]},
    "_style/Text_Line_Space": lambda v: {"text_line_space": v["integer"]},
    "_style/Text_Decor": lambda v: {"text_decor": v["strval"].lower()},
    "_style/Text_Align": lambda v: {"text_align": v["strval"].lower()},
    # Outline styles
    "_style/Outline_Width": lambda v: {"outline_width": v["integer"]},
    "_style/Outline_Color": lambda v: color_opa("outline_color", "outline_opa", v),
    "_style/Outline_Pad": lambda v: {"outline_pad": v["integer"]},
    # Shadow styles
    "_style/Shadow_Width": lambda v: {"shadow_width": v["integer"]},
    "_style/Shadow_Ofs_X": lambda v: {"shadow_ofs_x": v["integer"]},
    "_style/Shadow_Ofs_Y": lambda v: {"shadow_ofs_y": v["integer"]},
    "_style/Shadow_Spread": lambda v: {"shadow_spread": v["integer"]},
    "_style/Shadow_Color": lambda v: color_opa("shadow_color", "shadow_opa", v),
    # Padding styles
    "_style/Padding": lambda v: {
        "pad_left": v["intarray"][0],
        "pad_right": v["intarray"][1],
        "pad_top": v["intarray"][2],
        "pad_bottom": v["intarray"][3],
    },
    "_style/Pad_Left": lambda v: {"pad_left": v["integer"]},
    "_style/Pad_Right": lambda v: {"pad_right": v["integer"]},
    "_style/Pad_Top": lambda v: {"pad_top": v["integer"]},
    "_style/Pad_Bottom": lambda v: {"pad_bottom": v["integer"]},
    "_style/Padding_RowCol": lambda v: {
        "layout": {
            "pad_row": v["intarray"][0],
            "pad_column": v["intarray"][1],
        },
    },
    # Radius styles
    "_style/Bg_Radius": lambda v: {"radius": v["integer"]},
    # Line styles
    "_style/Line_Width": lambda v: {"line_width": v["integer"]},
    "_style/Line_Dash_Width": lambda v: {"line_dash_width": v["integer"]},
    "_style/Line_Dash_Gap": lambda v: {"line_dash_gap": v["integer"]},
    "_style/Line_Rounded": lambda v: {"line_rounded": v["strval"].lower() == "true"},
    "_style/Line_Color": lambda v: color_opa("line_color", "line_opa", v),
    # Arc styles
    "_style/Arc_Width": lambda v: {"arc_width": v["integer"]},
    "_style/Arc_Rounded": lambda v: {"arc_rounded": v["strval"].lower() == "true"},
    "_style/Arc_Color": lambda v: color_opa("arc_color", "arc_opa", v),
    # Blend styles
    "_style/Blend_Mode": lambda v: {"blend_mode": v["strval"].lower()},
    # Transform styles
    "_style/Transform_Width": lambda v: {"transform_width": v["integer"]},
    "_style/Transform_Height": lambda v: {"transform_height": v["integer"]},
    "_style/Transform_Zoom": lambda v: {
        "transform_zoom": round(float(v["integer"] / 256.0), 2)
    },
    "_style/Transform_Angle": lambda v: {"transform_angle": v["integer"]},
    "_style/Transform_Pivot_X": lambda v: {"transform_pivot_x": v["integer"]},
    "_style/Transform_Pivot_Y": lambda v: {"transform_pivot_y": v["integer"]},
}


def slugify(name: str) -> str:
    """make a YAML-friendly id: letters, digits, underscores only, lowercase"""
    return re.sub(r"[^0-9A-Za-z_]", "_", name)


def slugify_image(name: str) -> str:
    """make a YAML-friendly id: letters, digits, underscores only, lowercase"""
    return name.split("/")[-1].replace(".", "_").replace(" ", "_")


def size_parser(node: dict, yaml_root_key: str, images: dict) -> dict:
    """Convert size property to a dict with width and height"""
    # Bit 0x30: width is size_content
    # Bit 0x03: height is size_content
    # Bit 0x20: width is percent
    # Bit 0x02: height is percent
    # Bit 0x10: width is px
    # Bit 0x01: height is px

    flags = node["flags"]
    size = node.get("intarray", [0, 0])

    # Width
    if flags & 0x03 == 0x03:
        width = "SIZE_CONTENT"
    elif flags & 0x02 == 0x02:
        width = f"{size[0]}%"
    else:
        width = size[0]

    # Height
    if flags & 0x30 == 0x30:
        height = "SIZE_CONTENT"
    elif flags & 0x20 == 0x20:
        height = f"{size[1]}%"
    else:
        height = size[1]

    return {
        "width": width,
        "height": height,
    }


def layout_parser(node: dict, yaml_root_key: str, images: dict) -> dict:
    if node["LayoutType"] == 1:
        flow = "ROW" if node["Flow"] == 0 else "COLUMN"
        wrap = "_WRAP" if node["Wrap"] else ""
        reverse = "_REVERSE" if node["Reversed"] else ""
        alignments = [
            "START",
            "CENTER",
            "END",
            "SPACE_BETWEEN",
            "SPACE_AROUND",
            "SPACE_EVENLY",
        ]
        return {
            "layout": {
                "type": "flex",
                "flex_flow": f"{flow}{wrap}{reverse}",
                "flex_align_main": alignments[node["MainAlignment"]],
                "flex_align_cross": alignments[node["CrossAlignment"]],
                "flex_align_track": alignments[node["TrackAlignment"]],
            }
        }


def hex_color(int_array: list) -> str:
    """Convert a list of 4 integers to a hex color string"""
    if len(int_array) == 4:
        r, g, b, _ = int_array
        return f"0x{r:02x}{g:02x}{b:02x}"
    if len(int_array) == 3:
        r, g, b = int_array
        return f"0x{r:02x}{g:02x}{b:02x}"
    return "0x000000"


def color_opa(color_id: str, opa_id: str, node: dict) -> dict:
    """Convert a color and opacity node to a dictionary"""
    if "intarray" not in node:
        return {}

    components = node["intarray"]
    color = hex_color(components)
    if len(components) == 4:
        opa = components[3]
    else:
        opa = 255  # Default opacity

    return {color_id: color, opa_id: opa / 255.0}


def style_parser(node: dict, yaml_root_key: str, images: dict) -> dict:
    """Parse style properties from a node and return a dictionary of style properties"""
    return base_style_parser(node, None, yaml_root_key, images)


def cursor_style_parser(node: dict, yaml_root_key: str, images: dict) -> dict:
    """Parse cursor properties from a node and return a dictionary of cursor properties"""
    return base_style_parser(node, "cursor", yaml_root_key, images)


def base_style_parser(
    node: dict, style_key: str, yaml_root_key: str, images: dict
) -> dict:
    """Parse style properties from a node and return a dictionary of style properties"""
    children = node.get("childs", [])
    result = (
        {
            "pad_left": 0,
            "pad_right": 0,
            "pad_top": 0,
            "pad_bottom": 0,
        }
        if style_key is None
        else {}
    )

    for child in children:
        if child["strtype"] == "_style/StyleState":
            state = child["strval"].lower()  # Get state (DEFAULT, PRESSED, etc.)
            grandchildren = child.get("childs", [])

            state_styles = {}
            for grandchild in grandchildren:
                style_type = grandchild["strtype"]

                if style_type in STYLE_PROPERTY_MAP:
                    try:
                        style_props = STYLE_PROPERTY_MAP[style_type](grandchild)

                        # Handle image properties specially
                        for key, value in style_props.items():
                            if "image_src" in key and isinstance(value, str):
                                # Convert image source to slugified ID
                                id = slugify_image(value)
                                style_props[key] = id
                                images[id] = value

                        state_styles.update(style_props)

                    except Exception as e:
                        print(f"Error processing style {style_type}: {e}")

            # Only add state if we have styles for it
            if state_styles:
                if state == "default":
                    # Default state properties go directly in the result
                    result.update(state_styles)
                else:
                    # Other states go under their state name
                    result[state] = state_styles

    if style_key is None:
        return result

    if result:
        return {style_key: result}

    return None


# Individual SquareLine property → YAML key + optional post-processing lambda
PROP_MAP = {
    # Common object properties
    "OBJECT/Name": ("id", lambda v, *args: slugify(v["strval"])),
    "OBJECT/Align": ("align", lambda v, *args: v["strval"]),
    "OBJECT/Position": (("x", "y"), lambda v, *args: v["intarray"]),
    "OBJECT/Disabled": (
        None,
        lambda v, *args: {"state": {"disabled": v["strval"].lower() == "true"}},
    ),
    "OBJECT/Checked": (
        "checked",
        lambda v, *args: {"state": {"checked": v["strval"].lower() == "true"}},
    ),
    "OBJECT/Checkable": ("checkable", lambda v, *args: v["strval"].lower() == "true"),
    "OBJECT/Edited": (
        "edited",
        lambda v, *args: {"state": {"edited": v["strval"].lower() == "true"}},
    ),
    "OBJECT/Focused": (
        "focused",
        lambda v, *args: {"state": {"focused": v["strval"].lower() == "true"}},
    ),
    "OBJECT/Pressed": (
        "pressed",
        lambda v, *args: {"state": {"pressed": v["strval"].lower() == "true"}},
    ),
    "OBJECT/Scrollable": ("scrollable", lambda v, *args: v["strval"].lower() == "true"),
    "OBJECT/Size": (None, size_parser),
    "OBJECT/Layout_type": (None, layout_parser),
    "TABPAGE/Layout_type": (None, layout_parser),
    "TABPAGE/Scrollable": (
        "scrollable",
        lambda v, *args: v["strval"].lower() == "true",
    ),
    # Styles
    "ARC/Style_main": (None, style_parser),
    "BAR/Style_main": (None, style_parser),
    "BUTTON/Style_main": (None, style_parser),
    "CONTAINER/Style_main": (None, style_parser),
    "DROPDOWN/Style_main": (None, style_parser),
    "IMAGE/Style_main": (None, style_parser),
    "LABEL/Style_main": (None, style_parser),
    "PANEL/Style_main": (None, style_parser),
    "ROLLER/Style_main": (None, style_parser),
    "SCREEN/Style_main": (None, style_parser),
    "SLIDER/Style_main": (None, style_parser),
    "SPINBOX/Style_cursor": (None, cursor_style_parser),
    "SPINBOX/Style_main": (None, style_parser),
    "SWITCH/Style_main": (None, style_parser),
    "TABPAGE/Style_main": (None, style_parser),
    "TABVIEW/Style_main": (None, style_parser),
    "TEXTAREA/Style_cursor": (None, cursor_style_parser),
    "TEXTAREA/Style_main": (None, style_parser),
    # Label properties
    "LABEL/Text": ("text", lambda v, *args: v["strval"]),
    "LABEL/Long_mode": ("long_mode", lambda v, *args: v["strval"].lower()),
    "LABEL/Recolor": ("recolor", lambda v, *args: v["strval"].lower() == "true"),
    # Button properties
    "BUTTON/Checkable": ("checkable", lambda v, *args: v["strval"].lower() == "true"),
    # Dropdown properties
    "DROPDOWN/Options": ("options", lambda v, *args: v["strval"].split("\\n")),
    # Arc properties
    # A bit hacky as SqureLine does not have an `adjustable` property
    # but they are so setting this to True for all ARCs
    # is the only way to make them work in ESPHome.
    "ARC/Arc": ("adjustable", lambda v, *args: True),
    "ARC/Range": (("min_value", "max_value"), lambda v, *args: v["intarray"]),
    "ARC/Value": ("value", lambda v, *args: int(v["integer"])),
    "ARC/Mode": ("mode", lambda v, *args: v["strval"].upper()),
    "ARC/Rotation": (
        "rotation",
        lambda v, *args: int(v["integer"]) if "integer" in v else 0,
    ),
    "ARC/Bg_angles": (("start_angle", "end_angle"), lambda v, *args: v["intarray"]),
    # Bar properties
    "BAR/Range": (("min_value", "max_value"), lambda v, *args: v["intarray"]),
    "BAR/Value": ("value", lambda v, *args: int(v["integer"])),
    "BAR/Mode": ("mode", lambda v, *args: v["strval"].upper()),
    # Slider properties
    "SLIDER/Range": (("min_value", "max_value"), lambda v, *args: v["intarray"]),
    "SLIDER/Value": (
        "value",
        lambda v, *args: int(v["integer"]) if "integer" in v else 0,
    ),
    "SLIDER/Mode": ("mode", lambda v, *args: v["strval"].upper()),
    # Roller properties
    "ROLLER/Options": ("options", lambda v, *args: v["strval"].split("\\n")),
    "ROLLER/Selected": ("selected_index", lambda v, *args: int(v.get("integer", 0))),
    "ROLLER/Mode": ("mode", lambda v, *args: v["strval"].upper()),
    # Spinbox properties
    "SPINBOX/Value": ("value", lambda v, *args: int(v.get("integer", 0))),
    "SPINBOX/Range": (("range_from", "range_to"), lambda v, *args: v["intarray"]),
    "SPINBOX/Digit_format": (
        ("digits", "decimal_places"),
        lambda v, *args: [v["intarray"][0], v["intarray"][1]],
    ),
    # Switch properties
    "SWITCH/Anim_time": ("anim_time", lambda v, *args: v["strval"] + "ms"),
    # Textarea properties
    "TEXTAREA/One_line": ("one_line", lambda v, *args: v["strval"].lower() == "true"),
    "TEXTAREA/Password": ("password", lambda v, *args: v["strval"].lower() == "true"),
    "TEXTAREA/Text": ("text", lambda v, *args: v["strval"]),
    "TEXTAREA/Placeholder": ("placeholder_text", lambda v, *args: v["strval"]),
    # Image properties
    "IMAGE/Asset": ("src", lambda v, *args: v["strval"]),
    "IMAGE/Pivot_x": ("pivot_x", lambda v, *args: int(v["integer"])),
    "IMAGE/Pivot_y": ("pivot_y", lambda v, *args: int(v["integer"])),
    "IMAGE/Rotation": (
        "angle",
        lambda v, *args: float(v["integer"]) if "integer" in v else 0,
    ),
    "IMAGE/Scale": ("zoom", lambda v, *args: round(float(v["integer"] / 256.0), 2)),
    "TABVIEW/Tab_position": ("position", lambda v, *args: v["strval"].upper()),
    "TABVIEW/Tab_size": ("size", lambda v, *args: int(v["integer"])),
    "TABPAGE/Name": ("id", lambda v, *args: v["strval"]),
    "TABPAGE/Title": ("name", lambda v, *args: v["strval"]),
    "_event/EventHandler": (None, event_parser),
}


def get_prop(node: dict, key: str) -> dict | None:
    """Return full property dict whose strtype matches key, else None"""
    return next((p for p in node.get("properties", []) if p["strtype"] == key), None)


def deep_update(original, update_with):
    for key, value in update_with.items():
        if (
            key in original
            and isinstance(original[key], dict)
            and isinstance(value, dict)
        ):
            deep_update(original[key], value)
        else:
            original[key] = value
    return original


def convert_widget(node: dict, images: dict, object_map: dict) -> dict | None:
    """Return YAML snippet (dict) for a SquareLine widget node with coordinate conversion"""
    sl_type = node.get("saved_objtypeKey")
    yaml_root_key = TYPE_MAP.get(sl_type)
    if not yaml_root_key:
        return None

    cfg = {}

    # Process all properties
    for sl_key, (yaml_key, func) in PROP_MAP.items():
        prop = get_prop(node, sl_key)
        if prop is None:
            continue

        # Special case for event_parser which needs object_map parameter
        if func == event_parser:
            processed = func(prop, yaml_root_key, images, object_map)
        else:
            processed = func(prop, yaml_root_key, images)

        if sl_key == "IMAGE/Asset":
            id = slugify_image(processed)
            images[id] = processed
            cfg[yaml_key] = id
        elif isinstance(processed, dict):
            cfg = deep_update(cfg, processed)
        elif isinstance(yaml_key, tuple):
            for k, v in zip(yaml_key, processed):
                cfg[k] = v
        elif processed is not None:
            cfg[yaml_key] = processed

    if yaml_root_key == "textarea":
        # Special case for TEXTAREA: ensure text is always a string
        text = cfg.get("text", "")
        if text.startswith(">custom"):
            # If it starts with >custom, it's a custom widget
            # Parse every line after the first as a yaml line
            # Replace yaml_root_key with the root of th yamls and
            # then replace all properties of this node with the properties of the yaml
            lines = text.split("\\n")
            if len(lines) > 1:
                yaml_text = "\n".join(lines[1:])
                try:
                    custom_cfg = yaml.safe_load(yaml_text)
                    if isinstance(custom_cfg, dict) and len(custom_cfg.keys()) == 1:
                        # Replace the root key with the widget type
                        yaml_root_key = list(custom_cfg)[0]
                        # Merge properties into cfg
                        del cfg["text"]
                        if "placeholder" in cfg:
                            del cfg["placeholder"]
                        if "placeholder_text" in cfg:
                            del cfg["placeholder_text"]
                        cfg = deep_update(cfg, custom_cfg[yaml_root_key])
                except yaml.YAMLError as e:
                    print(f"Error parsing custom YAML in TEXTAREA: {e}")

    # Recursively process child widgets
    children_yaml = []
    for child in node.get("children", []):
        child_widget = convert_widget(child, images, object_map)
        if child_widget:
            children_yaml.append(child_widget)

    if children_yaml:
        if yaml_root_key == "tabview":
            cfg["tabs"] = [p["tab"] for p in children_yaml]
        else:
            cfg["widgets"] = children_yaml

    return {yaml_root_key: cfg}


def convert_page(screen_node: dict, images: dict, object_map: dict) -> dict:
    """Convert a SCREEN object into an lvgl page entry"""
    page_dict = convert_widget(screen_node, images, object_map)
    return page_dict["screen"]


def convert_to_rgb565(image_path: str) -> str:
    # Get the base name and directory
    directory = os.path.dirname(image_path)
    base_name = os.path.basename(image_path)
    name, ext = os.path.splitext(base_name)

    # Create output filename
    output_path = os.path.join(directory, f"{name}_RGB565{ext}")

    try:
        with Image.open(image_path) as img:
            # Check if image has alpha channel
            has_alpha = img.mode in ("RGBA", "LA")

            if has_alpha:
                # If image has alpha, split into color and alpha
                if img.mode == "RGBA":
                    img_rgba = img.convert("RGBA")
                else:  # LA mode (grayscale with alpha)
                    img_rgba = img.convert("RGBA")
                r, g, b, a = img_rgba.split()
            else:
                # Convert to RGB mode if not already
                img_rgb = img.convert("RGB")
                r, g, b = img_rgb.split()
                # Create an opaque alpha channel
                a = Image.new("L", img_rgb.size, 255)

            # Quantize RGB to RGB565 format
            r = r.point(lambda x: (x >> 3) << 3)  # 5 bits for red
            g = g.point(lambda x: (x >> 2) << 2)  # 6 bits for green
            b = b.point(lambda x: (x >> 3) << 3)  # 5 bits for blue

            # Always merge as RGBA
            rgb565_img = Image.merge("RGBA", (r, g, b, a))

            # Save the converted image with alpha
            rgb565_img.save(output_path)
            return output_path

    except Exception as e:
        print(f"Error processing {image_path}: {str(e)}")


def convert_all_images(folder: str, images: dict) -> dict:
    converted = {}
    for k, v in images.items():
        if v == "":
            print("Skipping empty image. Yaml will not compile")
            continue
        src = os.path.join(folder, v)
        dst = convert_to_rgb565(src)
        converted[k] = dst
    return converted


def create_object_map(data: dict) -> dict:
    """
    Create a map of all objects with their Object/Name as key and their guid as value.
    This allows for easier referencing of objects by name instead of GUID.
    """
    object_map = {}

    def process_node(node):
        if isinstance(node, dict):
            # Check if this is an object with a name and guid
            name_prop = get_prop(node, "OBJECT/Name")
            if name_prop and "guid" in node:
                object_name = name_prop["strval"]
                object_guid = node["guid"]
                object_map[object_guid] = slugify(object_name)

            # Also check for TABPAGE/Name which is used for tab pages
            tab_name_prop = get_prop(node, "TABPAGE/Name")
            if tab_name_prop and "guid" in node:
                tab_name = tab_name_prop["strval"]
                tab_guid = node["guid"]
                object_map[tab_guid] = slugify(tab_name)

            # Recursively process children
            for child in node.get("children", []):
                process_node(child)

    # Start processing from the root
    process_node(data["root"])
    return object_map


def monitor_input_file(path, process_func):
    """
    Monitor the input file for changes and re-run process_func when it changes.
    Exits when the user presses 'q'.
    """
    print("Monitoring for changes. Press 'q' to quit.")
    last_mtime = None
    stop_event = threading.Event()

    if sys.platform == "win32":
        import msvcrt

        def key_listener():
            while not stop_event.is_set():
                if msvcrt.kbhit() and msvcrt.getch() == b"q":
                    stop_event.set()
                time.sleep(0.1)
    else:
        import termios
        import tty

        def key_listener():
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setcbreak(fd)
                while not stop_event.is_set():
                    if sys.stdin.read(1) == "q":
                        stop_event.set()
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    listener_thread = threading.Thread(target=key_listener, daemon=True)
    listener_thread.start()

    while not stop_event.is_set():
        try:
            mtime = os.path.getmtime(path)
            if last_mtime is None or mtime != last_mtime:
                last_mtime = mtime
                print(f"File {path} changed. Reprocessing...")
                process_func()
        except Exception as e:
            print(f"Error monitoring file: {e}", file=sys.stderr)
        time.sleep(1)


def main():
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(
        description="Convert SquareLine *.spj JSON to ESPHome-LVGL YAML"
    )
    parser.add_argument("input_file", help="Input SquareLine project file (.spj)")
    parser.add_argument("-o", "--output", help="Output file path")
    parser.add_argument(
        "-c", "--clipboard", action="store_true", help="Copy output to clipboard"
    )
    parser.add_argument("-s", "--stdout", action="store_true", help="Output to stdout")
    parser.add_argument(
        "-m", "--monitor", action="store_true", help="Monitor input file for changes"
    )

    args = parser.parse_args()

    # If no output options specified, default to both stdout and clipboard (original behavior)
    if not (args.output or args.clipboard or args.stdout):
        args.stdout = True

    path = args.input_file

    def process():
        data = json.loads(Path(path).read_text())
        folder = os.path.abspath(os.path.dirname(path))

        # Create a map of object names to GUIDs
        object_map = create_object_map(data)

        # Walk root → pages (SCREEN objects)
        pages = []
        images = {}

        def recurse(node):
            if isinstance(node, dict):
                if node.get("saved_objtypeKey") == "SCREEN":
                    pages.append(convert_page(node, images, object_map))
                for child in node.get("children", []):
                    recurse(child)

        recurse(data["root"])

        img_dict = convert_all_images(folder, images)

        # Convert image paths to relative paths
        relative_to = None
        if args.output:
            relative_to = os.path.abspath(os.path.dirname(args.output))

        images_list = [
            {
                "id": key,
                "file": os.path.relpath(os.path.join(folder, value), relative_to)
                if relative_to
                else os.path.join(folder, value),
                "type": "RGB565",
                "transparency": "alpha_channel",
            }
            for key, value in img_dict.items()
        ]

        lvgl_yaml = {
            "lvgl": {"pages": pages},
        }

        if images_list:
            lvgl_yaml["image"] = images_list

        output = yaml.dump(
            lvgl_yaml,
            sort_keys=False,
            width=88,
            default_flow_style=False,
            allow_unicode=True,
        )

        # Handle output based on command line arguments
        if args.stdout:
            print(output)

        if args.clipboard:
            try:
                pyperclip.copy(output)
                if args.stdout:
                    print("Output copied to clipboard.", file=sys.stderr)
            except Exception as e:
                print(f"Failed to copy to clipboard: {str(e)}", file=sys.stderr)

        if args.output:
            try:
                with open(args.output, "w") as f:
                    f.write(output)
                if args.stdout:
                    print(f"Output written to {args.output}", file=sys.stderr)
            except Exception as e:
                print(
                    f"Failed to write to file {args.output}: {str(e)}", file=sys.stderr
                )

    if args.monitor:
        monitor_input_file(path, process)
    else:
        process()


if __name__ == "__main__":
    main()
