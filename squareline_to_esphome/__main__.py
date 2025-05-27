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
import time
import threading
import termios
import tty
from pathlib import Path

import pyperclip
import yaml  # pip install pyyaml
from PIL import Image

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
    "SLIDER": "slider",
    "SWITCH": "switch",
    "SPINBOX": "spinbox",
    # Visualizer widgets
    "BAR": "bar",
    "ARC": "arc",
    "SPINNER": "spinner",
}

EVENT_MAP = {
    "VALUE_CHANGED": "change",
    "CHECKED": "value",
    "PRESSED": "press",
    "LONG_PRESSED": "long_press",
    "LONG_PRESSED_REPEAT": "long_press_repeat",
    "SHORT_CLICKED": "short_click",
    "CLICKED": "click",
    "RELEASED": "release",
    "FOCUSED": "focus",
    "DEFOCUSED": "defocus",
    "GESTURE_LEFT": "swipe_left",
    "GESTURE_RIGHT": "swipe_right",
    "GESTURE_DOWN": "swipe_down",
    "GESTURE_UP": "swipe_up",
}

object_map = {}


def event_parser(node: dict, yaml_root_key: str) -> dict:
    global object_map

    event = node["strval"]
    if event not in EVENT_MAP:
        return {}
    event = EVENT_MAP[event]

    handlers = []
    for child in node["childs"]:
        if child["strtype"] == "_event/action":
            if child["strval"] == "CALL FUNCTION":
                for grandchild in child["childs"]:
                    if grandchild["strtype"] == "CALL FUNCTION/Function_name":
                        script = grandchild["strval"]
                        parameter = "tab" if yaml_root_key == "tabview" else "x"
                        handlers.append(
                            {
                                "lambda": f"id({script})->execute({parameter});",
                            }
                        )
                        break

            elif child["strval"] == "LABEL_PROPERTY":
                id = None
                property = None
                value = None
                for grandchild in child["childs"]:
                    if grandchild["strtype"] == "LABEL_PROPERTY/Target":
                        id = grandchild["strval"]
                    elif grandchild["strtype"] == "LABEL_PROPERTY/Property":
                        property = grandchild["strval"]
                    elif grandchild["strtype"] == "LABEL_PROPERTY/Value":
                        value = grandchild["strval"]
                if id and property and value:
                    handlers.append(
                        {
                            "lvgl.label.update": {
                                "id": object_map[id],
                                property.lower(): value,
                            }
                        }
                    )

    if handlers:
        return {
            f"on_{event}": {
                "then": handlers,
            }
        }
    return {}


def size_parser(node: dict, yaml_root_key: str) -> dict:
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
    if flags & 0x30 == 0x30:
        width = f"{size[0]}%"
    elif flags & 0x20 == 0x20:
        width = "SIZE_CONTENT"
    else:
        width = size[0]

    # Height
    if flags & 0x03 == 0x03:
        height = f"{size[1]}%"
    elif flags & 0x02 == 0x02:
        height = "SIZE_CONTENT"
    else:
        height = size[1]

    return {
        "width": width,
        "height": height,
    }


def layout_parser(node: dict, yaml_root_key: str) -> dict:
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
    if len(int_array) != 4:
        return "0x000000"
    r, g, b, _ = int_array
    return f"0x{r:02x}{g:02x}{b:02x}"


def style_parser(node: dict, yaml_root_key: str) -> dict:
    children = node.get("childs", [])
    result = {
        "pad_left": 0,
        "pad_right": 0,
        "pad_top": 0,
        "pad_bottom": 0,
    }
    for child in children:
        if child["strtype"] == "_style/StyleState":
            grandchildren = child.get("childs", [])
            for grandchild in grandchildren:
                if grandchild["strtype"] == "_style/Padding":
                    paddings = zip(
                        ("pad_left", "pad_right", "pad_top", "pad_bottom"),
                        grandchild["intarray"],
                    )
                    result = deep_update(result, {k: v for k, v in paddings})

                elif grandchild["strtype"] == "_style/Bg_Radius":
                    result["radius"] = grandchild["integer"]

                elif grandchild["strtype"] == "_style/Bg_Color":
                    result["bg_color"] = hex_color(grandchild["intarray"])

                elif grandchild["strtype"] == "_style/Border width":
                    result["border_width"] = grandchild.get("integer", 0)

                elif grandchild["strtype"] == "_style/Border_Color":
                    result["border_color"] = hex_color(grandchild["intarray"])

            break

    return result


# Individual SquareLine property → YAML key + optional post-processing lambda
PROP_MAP = {
    # Common object properties
    "OBJECT/Name": ("id", lambda v, _: slugify(v["strval"])),
    "OBJECT/Align": ("align", lambda v, _: v["strval"]),
    "OBJECT/Position": (("x", "y"), lambda v, _: v["intarray"]),
    "OBJECT/Disabled": (
        None,
        lambda v, _: {"state": {"disabled": v["strval"].lower() == "true"}},
    ),
    "OBJECT/Checked": (
        "checked",
        lambda v, _: {"state": {"checked": v["strval"].lower() == "true"}},
    ),
    "OBJECT/Focused": ("focused", lambda v, _: v["strval"].lower() == "true"),
    "OBJECT/Pressed": ("pressed", lambda v, _: v["strval"].lower() == "true"),
    "OBJECT/Edited": ("edited", lambda v, _: v["strval"].lower() == "true"),
    "OBJECT/Scrollable": ("scrollable", lambda v, _: v["strval"].lower() == "true"),
    "OBJECT/Size": (None, size_parser),
    "OBJECT/Layout_type": (None, layout_parser),
    "CONTAINER/Style_main": (None, style_parser),
    # Label properties
    "LABEL/Text": ("text", lambda v, _: v["strval"]),
    "LABEL/Long_mode": ("long_mode", lambda v, _: v["strval"].lower()),
    "LABEL/Recolor": ("recolor", lambda v, _: v["strval"].lower() == "true"),
    # Button properties
    "BUTTON/Checkable": ("checkable", lambda v, _: v["strval"].lower() == "true"),
    # Dropdown properties
    "DROPDOWN/Options": ("options", lambda v, _: v["strval"].split("\\n")),
    # Arc properties
    "ARC/Range": (("min_value", "max_value"), lambda v, _: v["intarray"]),
    "ARC/Value": ("value", lambda v, _: int(v["integer"])),
    "ARC/Mode": ("mode", lambda v, _: v["strval"].upper()),
    "ARC/Rotation": (
        "rotation",
        lambda v, _: int(v["integer"]) if "integer" in v else 0,
    ),
    # Bar properties
    "BAR/Range": (("min_value", "max_value"), lambda v, _: v["intarray"]),
    "BAR/Value": ("value", lambda v, _: int(v["integer"])),
    "BAR/Mode": ("mode", lambda v, _: v["strval"].upper()),
    # Slider properties
    "SLIDER/Range": (("min_value", "max_value"), lambda v, _: v["intarray"]),
    "SLIDER/Value": ("value", lambda v, _: int(v["integer"]) if "integer" in v else 0),
    "SLIDER/Mode": ("mode", lambda v, _: v["strval"].upper()),
    # Roller properties
    "ROLLER/Options": ("options", lambda v, _: v["strval"].split("\\n")),
    "ROLLER/Selected": ("selected", lambda v, _: int(v["integer"])),
    "ROLLER/Mode": ("mode", lambda v, _: v["strval"].upper()),
    # Spinbox properties
    "SPINBOX/Value": ("value", lambda v, _: int(v["integer"])),
    "SPINBOX/Range": (("min_value", "max_value"), lambda v, _: v["intarray"]),
    # Switch properties
    "SWITCH/Anim_time": ("anim_time", lambda v, _: v["strval"] + "ms"),
    # Textarea properties
    "TEXTAREA/One_line": ("one_line", lambda v, _: v["strval"].lower() == "true"),
    "TEXTAREA/Password": ("password", lambda v, _: v["strval"].lower() == "true"),
    "TEXTAREA/Text": ("text", lambda v, _: v["strval"]),
    "TEXTAREA/Placeholder": ("placeholder", lambda v, _: v["strval"]),
    # Image properties
    "IMAGE/Asset": ("src", lambda v, _: v["strval"]),
    "IMAGE/Pivot_x": ("pivot_x", lambda v, _: int(v["integer"])),
    "IMAGE/Pivot_y": ("pivot_y", lambda v, _: int(v["integer"])),
    "IMAGE/Rotation": (
        "angle",
        lambda v, _: float(v["integer"]) if "integer" in v else 0,
    ),
    "IMAGE/Scale": ("zoom", lambda v, _: float(v["integer"])),
    "TABVIEW/Tab_position": ("position", lambda v, _: v["strval"].upper()),
    "TABVIEW/Tab_size": ("size", lambda v, _: int(v["integer"])),
    "TABPAGE/Name": ("id", lambda v, _: v["strval"]),
    "TABPAGE/Title": ("name", lambda v, _: v["strval"]),
    "_event/EventHandler": (None, event_parser),
}


def slugify(name: str) -> str:
    """make a YAML-friendly id: letters, digits, underscores only, lowercase"""
    return re.sub(r"[^0-9A-Za-z_]", "_", name).lower()


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


def convert_widget(node: dict, images: dict) -> dict | None:
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

        processed = func(prop, yaml_root_key)

        if sl_key == "IMAGE/Asset":
            id = processed.split("/")[-1].replace(".", "_").replace(" ", "_")
            if id not in images:
                images[id] = processed
            cfg[yaml_key] = id
        elif isinstance(processed, dict):
            cfg = deep_update(cfg, processed)
        elif isinstance(yaml_key, tuple):
            for k, v in zip(yaml_key, processed):
                cfg[k] = v
        elif processed is not None:
            cfg[yaml_key] = processed

    # Recursively process child widgets
    children_yaml = []
    for child in node.get("children", []):
        child_widget = convert_widget(child, images)
        if child_widget:
            children_yaml.append(child_widget)

    if children_yaml:
        if yaml_root_key == "tabview":
            cfg["tabs"] = [p["tab"] for p in children_yaml]
        else:
            cfg["widgets"] = children_yaml

    return {yaml_root_key: cfg}


def convert_page(screen_node: dict, images: dict) -> dict:
    """Convert a SCREEN object into an lvgl page entry"""
    name_prop = get_prop(screen_node, "OBJECT/Name")
    page_id = slugify(name_prop["strval"]) if name_prop else "page"

    page_dict = {"id": page_id}

    # Process widgets inside the page
    widgets = []
    for child in screen_node.get("children", []):
        w = convert_widget(child, images)
        if w:
            widgets.append(w)
    if widgets:
        page_dict["widgets"] = widgets

    return page_dict


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
        src = os.path.join(folder, v)
        dst = convert_to_rgb565(src)
        converted[k] = dst
    return converted


def create_object_map(data: dict) -> dict:
    """
    Create a map of all objects with their Object/Name as key and their guid as value.
    This allows for easier referencing of objects by name instead of GUID.
    """
    global object_map
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


def monitor_input_file(path, process_func):
    """
    Monitor the input file for changes and re-run process_func when it changes.
    Exits when the user presses 'q'.
    """
    print("Monitoring for changes. Press 'q' to quit.")
    last_mtime = None
    stop_event = threading.Event()

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
        folder = os.path.dirname(path)

        # Create a map of object names to GUIDs
        create_object_map(data)

        # Walk root → pages (SCREEN objects)
        pages = []
        images = {}

        def recurse(node):
            if isinstance(node, dict):
                if node.get("saved_objtypeKey") == "SCREEN":
                    pages.append(convert_page(node, images))
                for child in node.get("children", []):
                    recurse(child)

        recurse(data["root"])

        img_dict = convert_all_images(folder, images)

        images_list = [
            {
                "id": key,
                "file": os.path.join(folder, value),
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
