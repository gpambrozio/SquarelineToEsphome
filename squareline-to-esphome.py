#!/usr/bin/env python3
"""
squareline-to-esphome.py  -  Convert SquareLine *.spj JSON to ESPHome-LVGL YAML.
"""

import json
import yaml            # pip install pyyaml
from PIL import Image
import os
import os.path
import re
import sys
from pathlib import Path
from typing import Dict, Tuple, Optional
import pyperclip


# SquareLine object type → ESPHome YAML widget keyword
TYPE_MAP = {
    # Basic widgets
    "LABEL":     "label",
    "BUTTON":    "button",
    "IMAGE":     "image",
    "PANEL":     "obj",          # Panel maps to generic obj in ESPHome
    "CONTAINER": "obj",          # Container also maps to obj
    "TEXTAREA":  "textarea",
    "TABVIEW":   "tabview",

    # Controller widgets
    "CHECKBOX":  "checkbox",
    "DROPDOWN":  "dropdown",
    "KEYBOARD":  "keyboard",
    "ROLLER":    "roller",
    "SLIDER":    "slider",
    "SWITCH":    "switch",
    "SPINBOX":   "spinbox",

    # Visualizer widgets
    "BAR":       "bar",
    "ARC":       "arc",
    "SPINNER":   "spinner",
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

def event_handler(node: dict) -> dict:
    event = node["strval"]
    if event not in EVENT_MAP:
        return {}
    event = EVENT_MAP[event]

    script = None
    for child in node["childs"]:
        if child["strtype"] == "_event/action" and child["strval"] == "CALL FUNCTION":
            for grandchild in child["childs"]:
                if grandchild["strtype"] == "CALL FUNCTION/Function_name":
                    script = grandchild["strval"]

    if script is None:
        return {}

    return {
        f"on_{event}": {"script.execute": script}
    }

def size_parser(node: dict) -> dict:
    """Convert size property to a dict with width and height"""
    if node["flags"] ==  17:
        size = node["intarray"]
        return {
            "width": size[0],
            "height": size[1],
        }

    if node["flags"] ==  51:
        return {
            "width": "SIZE_CONTENT",
            "height": "SIZE_CONTENT",
        }

def layout_parser(node: dict) -> dict:
    if node["LayoutType"] ==  1:
        flow = "ROW" if node["Flow"] == 0 else "COLUMN"
        wrap = "_WRAP" if node["Wrap"] else ""
        reverse = "_REVERSE" if node["Reversed"] else ""
        alignments = [
            "START", "CENTER", "END", "SPACE_BETWEEN", "SPACE_AROUND", "SPACE_EVENLY",
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


# Individual SquareLine property → YAML key + optional post-processing lambda
PROP_MAP = {
    # Common object properties
    "OBJECT/Name":         ("id",          lambda v: slugify(v["strval"])),
    "OBJECT/Align":        ("align",       lambda v: v["strval"]),
    "OBJECT/Position":     (("x", "y"),    lambda v: v["intarray"]),
    "OBJECT/Size":         (None,          size_parser),
    "OBJECT/Scrollable":   ("scrollable",  lambda v: v["strval"].lower() == "true"),
    "OBJECT/Layout_type":  (None,          layout_parser),

    # Label properties
    "LABEL/Text":          ("text",        lambda v: v["strval"]),
    "LABEL/Long_mode":     ("long_mode",   lambda v: v["strval"].lower()),
    "LABEL/Recolor":       ("recolor",     lambda v: v["strval"].lower() == "true"),

    # Button properties
    "BUTTON/Checkable":    ("checkable",   lambda v: v["strval"].lower() == "true"),

    # Dropdown properties
    "DROPDOWN/Options":    ("options",     lambda v: v["strval"].split("\\n")),

    # Arc properties
    "ARC/Range":          (("min_value", "max_value"), lambda v: v["intarray"]),
    "ARC/Value":          ("value",       lambda v: int(v["integer"])),
    "ARC/Mode":           ("mode",        lambda v: v["strval"].upper()),
    "ARC/Rotation":       ("rotation",    lambda v: int(v["integer"]) if "integer" in v else 0),

    # Bar properties
    "BAR/Range":          (("min_value", "max_value"), lambda v: v["intarray"]),
    "BAR/Value":          ("value",       lambda v: int(v["integer"])),
    "BAR/Mode":           ("mode",        lambda v: v["strval"].upper()),

    # Slider properties
    "SLIDER/Range":       (("min_value", "max_value"), lambda v: v["intarray"]),
    "SLIDER/Value":       ("value",       lambda v: int(v["integer"]) if "integer" in v else 0),
    "SLIDER/Mode":        ("mode",        lambda v: v["strval"].upper()),

    # Roller properties
    "ROLLER/Options":     ("options",     lambda v: v["strval"].split("\\n")),
    "ROLLER/Selected":    ("selected",    lambda v: int(v["integer"])),
    "ROLLER/Mode":        ("mode",        lambda v: v["strval"].upper()),

    # Spinbox properties
    "SPINBOX/Value":      ("value",       lambda v: int(v["integer"])),
    "SPINBOX/Range":      (("min_value", "max_value"), lambda v: v["intarray"]),

    # Switch properties
    "SWITCH/Anim_time":   ("anim_time",   lambda v: v["strval"] + "ms"),

    # Textarea properties
    "TEXTAREA/One_line":  ("one_line",    lambda v: v["strval"].lower() == "true"),
    "TEXTAREA/Password":   ("password",    lambda v: v["strval"].lower() == "true"),
    "TEXTAREA/Text":      ("text",        lambda v: v["strval"]),
    "TEXTAREA/Placeholder": ("placeholder", lambda v: v["strval"]),

    # Image properties
    "IMAGE/Asset":        ("src",         lambda v: v["strval"]),
    "IMAGE/Pivot_x":      ("pivot_x",     lambda v: int(v["integer"])),
    "IMAGE/Pivot_y":      ("pivot_y",     lambda v: int(v["integer"])),
    "IMAGE/Rotation":     ("angle",       lambda v: float(v["integer"]) if "integer" in v else 0),
    "IMAGE/Scale":        ("zoom",        lambda v: float(v["integer"])),
    
    "_event/EventHandler": (None,         event_handler),
}

def slugify(name: str) -> str:
    """make a YAML-friendly id: letters, digits, underscores only, lowercase"""
    return re.sub(r"[^0-9A-Za-z_]", "_", name).lower()

def get_prop(node: Dict, key: str) -> Optional[Dict]:
    """Return full property dict whose strtype matches key, else None"""
    return next((p for p in node.get("properties", []) if p["strtype"] == key), None)

def extract_dimensions(node: Dict) -> Tuple[Optional[int], Optional[int]]:
    """Extract width and height from a widget node if available"""
    size_prop = get_prop(node, "OBJECT/Size")
    if size_prop and "intarray" in size_prop:
        return size_prop["intarray"][0], size_prop["intarray"][1]
    return None, None

def convert_widget(node: Dict, images: Dict) -> Optional[Dict]:
    """Return YAML snippet (dict) for a SquareLine widget node with coordinate conversion"""
    sl_type = node.get("saved_objtypeKey")
    yaml_root_key = TYPE_MAP.get(sl_type)
    if not yaml_root_key:
        return None

    cfg = {}

    # Get this widget's dimensions first
    widget_width, widget_height = extract_dimensions(node)

    # Process all properties
    for sl_key, (yaml_key, func) in PROP_MAP.items():
        prop = get_prop(node, sl_key)
        if prop is None:
            continue

        processed = func(prop)

        if sl_key == "IMAGE/Asset":
            id = processed.split("/")[-1].replace(".", "_").replace(" ", "_")
            if id not in images:
                images[id] = processed
            cfg[yaml_key] = id
        elif isinstance(processed, dict):
            cfg.update(processed)
        elif isinstance(yaml_key, tuple):
            for k, v in zip(yaml_key, processed):
                cfg[k] = v
        elif processed is not None:
            cfg[yaml_key] = processed


    # Recursively process child widgets
    if node.get("children"):
        children_yaml = []
        for child in node["children"]:
            child_widget = convert_widget(child, images)
            if child_widget:
                children_yaml.append(child_widget)
        if children_yaml:
            cfg["widgets"] = children_yaml

    return {yaml_root_key: cfg}

def convert_page(screen_node: Dict, images: Dict) -> Dict:
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
            has_alpha = img.mode in ('RGBA', 'LA')
            
            if has_alpha:
                # If image has alpha, split into color and alpha
                if img.mode == 'RGBA':
                    img_rgba = img.convert('RGBA')
                else:  # LA mode (grayscale with alpha)
                    img_rgba = img.convert('RGBA')
                r, g, b, a = img_rgba.split()
            else:
                # Convert to RGB mode if not already
                img_rgb = img.convert('RGB')
                r, g, b = img_rgb.split()
                # Create an opaque alpha channel
                a = Image.new('L', img_rgb.size, 255)
                
            # Quantize RGB to RGB565 format
            r = r.point(lambda x: (x >> 3) << 3)  # 5 bits for red
            g = g.point(lambda x: (x >> 2) << 2)  # 6 bits for green
            b = b.point(lambda x: (x >> 3) << 3)  # 5 bits for blue
            
            # Always merge as RGBA
            rgb565_img = Image.merge('RGBA', (r, g, b, a))
            
            # Save the converted image with alpha
            rgb565_img.save(output_path)
            return output_path
            
    except Exception as e:
        print(f"Error processing {image_path}: {str(e)}")
        
def convert_all_images(folder: str, images: Dict) -> Dict:
    converted = {}
    for k, v in images.items():
        src = os.path.join(folder, v)
        dst = convert_to_rgb565(src)
        converted[k] = dst
    return converted


def main(path: str):
    data = json.loads(Path(path).read_text())
    folder = os.path.dirname(path)

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

    images = convert_all_images(folder, images)

    images = [
        {
            "id": key,
            "file": os.path.join(folder, value),
            "type": "RGB565",
            "transparency": "alpha_channel"
        }
        for key, value in images.items()
    ]

    lvgl_yaml = {
        "lvgl": {
            "pages": pages
        },
    }
    
    if images:
        lvgl_yaml["image"] = images

    output = yaml.dump(
            lvgl_yaml,
            sort_keys=False,
            width=88,
            default_flow_style=False,
            allow_unicode=True,
        )
    print(output)

    # Copy output to clipboard
    pyperclip.copy(output)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"usage: {sys.argv[0]} <project.spj>", file=sys.stderr)
        sys.exit(1)
    main(sys.argv[1])
