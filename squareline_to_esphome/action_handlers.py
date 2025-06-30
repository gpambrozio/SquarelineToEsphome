"""
Action handlers for SquareLine event processing.
Converts SquareLine event actions to ESPHome YAML format.
"""

from .yaml_utils import ESPHomeLambda

# Global reference to object_map - will be set by main module
object_map = {}

# Event mapping from SquareLine to ESPHome
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


def event_parser(node: dict, yaml_root_key: str, images: dict) -> dict:
    """Parse SquareLine event handlers and convert to ESPHome format."""
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
                        parameter = "x"
                        if yaml_root_key == "tabview":
                            parameter = "tab"
                        if yaml_root_key == "label":
                            parameter = "text"
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

            elif child["strval"] == "CHANGE SCREEN":
                screen_id = None
                fade_mode = None
                speed = None
                for grandchild in child["childs"]:
                    if grandchild["strtype"] == "CHANGE SCREEN/Screen_to":
                        screen_id = grandchild["strval"]
                    elif grandchild["strtype"] == "CHANGE SCREEN/Fade_mode":
                        fade_mode = grandchild["strval"]
                    elif grandchild["strtype"] == "CHANGE SCREEN/Speed":
                        speed = grandchild.get("integer", 500)

                if screen_id and screen_id in object_map:
                    page_action = {"lvgl.page.show": {"id": object_map[screen_id]}}
                    if fade_mode or speed:
                        page_action["lvgl.page.show"]["animation"] = {}
                        if fade_mode:
                            page_action["lvgl.page.show"]["animation"] = (
                                fade_mode.lower()
                            )
                        if speed:
                            page_action["lvgl.page.show"]["time"] = f"{speed}ms"
                    handlers.append(page_action)

            elif child["strval"] == "INCREMENT ARC":
                target_id = None
                value = None
                for grandchild in child["childs"]:
                    if grandchild["strtype"] == "INCREMENT ARC/Target":
                        target_id = grandchild["strval"]
                    elif grandchild["strtype"] == "INCREMENT ARC/Value":
                        value = grandchild.get("integer", 0)

                if target_id and target_id in object_map and value is not None:
                    handlers.append(
                        {
                            "lvgl.arc.update": {
                                "id": object_map[target_id],
                                "value": ESPHomeLambda(
                                    f"return float({value} + lv_arc_get_value(id({object_map[target_id]})));"
                                ),
                            }
                        }
                    )

            elif child["strval"] == "INCREMENT BAR":
                target_id = None
                value = None
                animate = None
                for grandchild in child["childs"]:
                    if grandchild["strtype"] == "INCREMENT BAR/Target":
                        target_id = grandchild["strval"]
                    elif grandchild["strtype"] == "INCREMENT BAR/Value":
                        value = grandchild.get("integer", 0)
                    elif grandchild["strtype"] == "INCREMENT BAR/Animate":
                        animate = grandchild["strval"]

                if target_id and target_id in object_map and value is not None:
                    handlers.append(
                        {
                            "lvgl.bar.update": {
                                "id": object_map[target_id],
                                "animated": animate == "ON",
                                "value": ESPHomeLambda(
                                    f"return float({value} + lv_bar_get_value(id({object_map[target_id]})));"
                                ),
                            }
                        }
                    )

            elif child["strval"] == "INCREMENT SLIDER":
                target_id = None
                value = None
                animate = None
                for grandchild in child["childs"]:
                    if grandchild["strtype"] == "INCREMENT SLIDER/Target":
                        target_id = grandchild["strval"]
                    elif grandchild["strtype"] == "INCREMENT SLIDER/Value":
                        value = grandchild.get("integer", 0)
                    elif grandchild["strtype"] == "INCREMENT SLIDER/Animate":
                        animate = grandchild["strval"]

                if target_id and target_id in object_map and value is not None:
                    handlers.append(
                        {
                            "lvgl.slider.update": {
                                "id": object_map[target_id],
                                "animated": animate == "ON",
                                "value": ESPHomeLambda(
                                    f"return float({value} + lv_slider_get_value(id({object_map[target_id]})));"
                                ),
                            }
                        }
                    )

            elif child["strval"] == "BASIC_PROPERTY":
                target_id = None
                property = None
                value = None
                for grandchild in child["childs"]:
                    if grandchild["strtype"] == "BASIC_PROPERTY/Target":
                        target_id = grandchild["strval"]
                    elif grandchild["strtype"] == "BASIC_PROPERTY/Property":
                        property = grandchild["strval"]
                    elif grandchild["strtype"] == "BASIC_PROPERTY/Value":
                        value = grandchild.get("integer") or grandchild.get("strval")

                if (
                    target_id
                    and target_id in object_map
                    and property
                    and value is not None
                ):
                    esp_property = property.lower().replace(" ", "_")
                    if property == "Position_X":
                        esp_property = "x"
                    elif property == "Position_Y":
                        esp_property = "y"

                    handlers.append(
                        {
                            "lvgl.widget.update": {
                                "id": object_map[target_id],
                                esp_property: value,
                            }
                        }
                    )

            elif child["strval"] == "SET OPACITY":
                target_id = None
                value = None
                for grandchild in child["childs"]:
                    if grandchild["strtype"] == "SET OPACITY/Target":
                        target_id = grandchild["strval"]
                    elif grandchild["strtype"] == "SET OPACITY/Value":
                        value = grandchild.get("integer", 255)

                if target_id and target_id in object_map and value is not None:
                    handlers.append(
                        {
                            "lvgl.widget.update": {
                                "id": object_map[target_id],
                                "opa": float(value) / 255.0,
                            }
                        }
                    )

            elif child["strval"] == "SLIDER_PROPERTY":
                target_id = None
                property = None
                value = None
                for grandchild in child["childs"]:
                    if grandchild["strtype"] == "SLIDER_PROPERTY/Target":
                        target_id = grandchild["strval"]
                    elif grandchild["strtype"] == "SLIDER_PROPERTY/Property":
                        property = grandchild["strval"]
                    elif grandchild["strtype"] == "SLIDER_PROPERTY/Value":
                        value = grandchild.get("integer") or grandchild.get("strval")

                if (
                    target_id
                    and target_id in object_map
                    and property
                    and value is not None
                ):
                    handlers.append(
                        {
                            "lvgl.slider.update": {
                                "id": object_map[target_id],
                                "animated": property == "Value_with_anim",
                                "value": int(value),
                            }
                        }
                    )

            elif child["strval"] == "BAR_PROPERTY":
                target_id = None
                property = None
                value = None
                for grandchild in child["childs"]:
                    if grandchild["strtype"] == "BAR_PROPERTY/Target":
                        target_id = grandchild["strval"]
                    elif grandchild["strtype"] == "BAR_PROPERTY/Property":
                        property = grandchild["strval"]
                    elif grandchild["strtype"] == "BAR_PROPERTY/Value":
                        value = grandchild.get("integer") or grandchild.get("strval")

                if (
                    target_id
                    and target_id in object_map
                    and property
                    and value is not None
                ):
                    handlers.append(
                        {
                            "lvgl.bar.update": {
                                "id": object_map[target_id],
                                "animated": property == "Value_with_anim",
                                "value": int(value),
                            }
                        }
                    )

            elif child["strval"] == "ROLLER_PROPERTY":
                target_id = None
                property = None
                value = None
                for grandchild in child["childs"]:
                    if grandchild["strtype"] == "ROLLER_PROPERTY/Target":
                        target_id = grandchild["strval"]
                    elif grandchild["strtype"] == "ROLLER_PROPERTY/Property":
                        property = grandchild["strval"]
                    elif grandchild["strtype"] == "ROLLER_PROPERTY/Value":
                        value = grandchild.get("integer") or grandchild.get("strval")

                if (
                    target_id
                    and target_id in object_map
                    and property
                    and value is not None
                ):
                    handlers.append(
                        {
                            "lvgl.roller.update": {
                                "id": object_map[target_id],
                                "animated": property == "Value_with_anim",
                                "selected_text": value,
                            }
                        }
                    )

            elif child["strval"] == "STEP SPINBOX":
                target_id = None
                direction = None
                for grandchild in child["childs"]:
                    if grandchild["strtype"] == "STEP SPINBOX/Target":
                        target_id = grandchild["strval"]
                    elif grandchild["strtype"] == "STEP SPINBOX/Direction":
                        direction = grandchild["strval"]

                if target_id and target_id in object_map and direction is not None:
                    if direction == "1":
                        handlers.append(
                            {"lvgl.spinbox.increment": {"id": object_map[target_id]}}
                        )
                    elif direction == "-1":
                        handlers.append(
                            {"lvgl.spinbox.decrement": {"id": object_map[target_id]}}
                        )

            elif child["strval"] == "MODIFY FLAG":
                target_id = None
                flag = None
                action = None
                for grandchild in child["childs"]:
                    if grandchild["strtype"] == "MODIFY FLAG/Object":
                        target_id = grandchild["strval"]
                    elif grandchild["strtype"] == "MODIFY FLAG/Flag":
                        flag = grandchild["strval"]
                    elif grandchild["strtype"] == "MODIFY FLAG/Action":
                        action = grandchild["strval"]

                if target_id and target_id in object_map and flag and action:
                    state = True
                    if action == "REMOVE":
                        state = False
                    elif action == "TOGGLE":
                        state = ESPHomeLambda(
                            f"return !lv_obj_has_flag(id({object_map[target_id]}), LV_OBJ_FLAG_{flag});"
                        )

                    handlers.append(
                        {
                            "lvgl.widget.update": {
                                "id": object_map[target_id],
                                flag.lower(): state,
                            }
                        }
                    )

            elif child["strval"] == "MODIFY STATE":
                target_id = None
                state = None
                action = None
                for grandchild in child["childs"]:
                    if grandchild["strtype"] == "MODIFY STATE/Object":
                        target_id = grandchild["strval"]
                    elif grandchild["strtype"] == "MODIFY STATE/State":
                        state = grandchild["strval"]
                    elif grandchild["strtype"] == "MODIFY STATE/Action":
                        action = grandchild["strval"]

                if target_id and target_id in object_map and state and action:
                    set_state = True
                    if action == "REMOVE":
                        set_state = False
                    elif action == "TOGGLE":
                        set_state = ESPHomeLambda(
                            f"return !lv_obj_has_flag(id({object_map[target_id]}), LV_OBJ_FLAG_{flag});"
                        )

                    handlers.append(
                        {
                            "lvgl.widget.update": {
                                "id": object_map[target_id],
                                "state": {
                                    state.lower(): set_state,
                                },
                            }
                        }
                    )

            elif child["strval"] == "KEYBOARD SET TARGET":
                keyboard_id = None
                textarea_id = None
                for grandchild in child["childs"]:
                    if grandchild["strtype"] == "KEYBOARD SET TARGET/Keyboard":
                        keyboard_id = grandchild["strval"]
                    elif grandchild["strtype"] == "KEYBOARD SET TARGET/TextArea":
                        textarea_id = grandchild["strval"]

                if (
                    keyboard_id
                    and textarea_id
                    and keyboard_id in object_map
                    and textarea_id in object_map
                ):
                    handlers.append(
                        {
                            "lvgl.keyboard.update": {
                                "id": object_map[keyboard_id],
                                "textarea": object_map[textarea_id],
                            }
                        }
                    )

            elif child["strval"] == "SET TEXT VALUE FROM ARC":
                target_id = None
                prefix = None
                postfix = None
                for grandchild in child["childs"]:
                    if grandchild["strtype"] == "SET TEXT VALUE FROM ARC/Target":
                        target_id = grandchild["strval"]
                    elif grandchild["strtype"] == "SET TEXT VALUE FROM ARC/Prefix":
                        prefix = grandchild["strval"]
                    elif grandchild["strtype"] == "SET TEXT VALUE FROM ARC/Postfix":
                        postfix = grandchild["strval"]

                if target_id and target_id in object_map:
                    prefix = prefix or ""
                    postfix = postfix or ""
                    handlers.append(
                        {
                            "lvgl.label.update": {
                                "id": object_map[target_id],
                                "text": {
                                    "format": "%s%d%s",
                                    "args": [f'"{prefix}"', "x", f'"{postfix}"'],
                                },
                            }
                        }
                    )

            elif child["strval"] == "SET TEXT VALUE FROM SLIDER":
                target_id = None
                prefix = None
                postfix = None
                for grandchild in child["childs"]:
                    if grandchild["strtype"] == "SET TEXT VALUE FROM SLIDER/Target":
                        target_id = grandchild["strval"]
                    elif grandchild["strtype"] == "SET TEXT VALUE FROM SLIDER/Prefix":
                        prefix = grandchild["strval"]
                    elif grandchild["strtype"] == "SET TEXT VALUE FROM SLIDER/Postfix":
                        postfix = grandchild["strval"]

                if target_id and target_id in object_map:
                    prefix = prefix or ""
                    postfix = postfix or ""
                    handlers.append(
                        {
                            "lvgl.label.update": {
                                "id": object_map[target_id],
                                "text": {
                                    "format": "%s%d%s",
                                    "args": [f'"{prefix}"', "x", f'"{postfix}"'],
                                },
                            }
                        }
                    )

            elif child["strval"] == "SET TEXT VALUE WHEN CHECKED":
                target_id = None
                on_text = None
                off_text = None
                for grandchild in child["childs"]:
                    if grandchild["strtype"] == "SET TEXT VALUE WHEN CHECKED/Target":
                        target_id = grandchild["strval"]
                    elif grandchild["strtype"] == "SET TEXT VALUE WHEN CHECKED/On_text":
                        on_text = grandchild["strval"]
                    elif (
                        grandchild["strtype"] == "SET TEXT VALUE WHEN CHECKED/Off_text"
                    ):
                        off_text = grandchild["strval"]

                if target_id and target_id in object_map and on_text and off_text:
                    handlers.append(
                        {
                            "lvgl.label.update": {
                                "id": object_map[target_id],
                                "text": {
                                    "format": "%s",
                                    "args": [f'x ? ""{on_text}"" : ""{off_text}""'],
                                },
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
