"""
Action handlers for SquareLine event processing.
Converts SquareLine event actions to ESPHome YAML format.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from .yaml_utils import ESPHomeLambda

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


class ActionHandler(ABC):
    """Abstract base class for SquareLine action handlers."""

    @abstractmethod
    def handle(
        self, child: Dict[str, Any], yaml_root_key: str, object_map: Dict[str, str]
    ) -> Optional[Dict[str, Any]]:
        """
        Handle a SquareLine action and return ESPHome YAML configuration.

        Args:
            child: The SquareLine action node
            yaml_root_key: The YAML root key for context (e.g., "tabview", "label")
            object_map: Mapping of SquareLine GUIDs to slugified names

        Returns:
            ESPHome YAML configuration dict or None if action cannot be handled
        """
        pass


def extract_child_values(
    child: Dict[str, Any], field_mappings: Dict[str, str]
) -> Dict[str, Any]:
    """
    Extract values from child nodes based on field mappings.

    Args:
        child: The parent node containing children
        field_mappings: Dict mapping result keys to SquareLine field names

    Returns:
        Dictionary with extracted values
    """
    result = {}
    for grandchild in child.get("childs", []):
        for result_key, field_name in field_mappings.items():
            if grandchild.get("strtype") == field_name:
                if "integer" in grandchild:
                    result[result_key] = grandchild["integer"]
                elif "strval" in grandchild:
                    result[result_key] = grandchild["strval"]
                break
    return result


def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> bool:
    """Check if all required fields are present and not None."""
    return all(data.get(field) is not None for field in required_fields)


class CallFunctionHandler(ActionHandler):
    """Handler for CALL FUNCTION actions."""

    def handle(
        self, child: Dict[str, Any], yaml_root_key: str, object_map: Dict[str, str]
    ) -> Optional[Dict[str, Any]]:
        data = extract_child_values(
            child, {"function_name": "CALL FUNCTION/Function_name"}
        )

        if not data.get("function_name"):
            return None

        script = data["function_name"]
        parameter = "x"
        if yaml_root_key == "tabview":
            parameter = "tab"
        elif yaml_root_key == "label":
            parameter = "text"

        return {"lambda": f"id({script})->execute({parameter});"}


class LabelPropertyHandler(ActionHandler):
    """Handler for LABEL_PROPERTY actions."""

    def handle(
        self, child: Dict[str, Any], yaml_root_key: str, object_map: Dict[str, str]
    ) -> Optional[Dict[str, Any]]:
        data = extract_child_values(
            child,
            {
                "target_id": "LABEL_PROPERTY/Target",
                "property": "LABEL_PROPERTY/Property",
                "value": "LABEL_PROPERTY/Value",
            },
        )

        if not validate_required_fields(data, ["target_id", "property", "value"]):
            return None

        if data["target_id"] not in object_map:
            return None

        return {
            "lvgl.label.update": {
                "id": object_map[data["target_id"]],
                data["property"].lower(): data["value"],
            }
        }


class ChangeScreenHandler(ActionHandler):
    """Handler for CHANGE SCREEN actions."""

    def handle(
        self, child: Dict[str, Any], yaml_root_key: str, object_map: Dict[str, str]
    ) -> Optional[Dict[str, Any]]:
        data = extract_child_values(
            child,
            {
                "screen_id": "CHANGE SCREEN/Screen_to",
                "fade_mode": "CHANGE SCREEN/Fade_mode",
                "speed": "CHANGE SCREEN/Speed",
            },
        )

        if not data.get("screen_id") or data["screen_id"] not in object_map:
            return None

        page_action = {"lvgl.page.show": {"id": object_map[data["screen_id"]]}}

        if data.get("fade_mode") or data.get("speed"):
            page_action["lvgl.page.show"]["animation"] = {}
            if data.get("fade_mode"):
                page_action["lvgl.page.show"]["animation"] = data["fade_mode"].lower()
            if data.get("speed"):
                page_action["lvgl.page.show"]["time"] = f"{data['speed']}ms"

        return page_action


class IncrementArcHandler(ActionHandler):
    """Handler for INCREMENT ARC actions."""

    def handle(
        self, child: Dict[str, Any], yaml_root_key: str, object_map: Dict[str, str]
    ) -> Optional[Dict[str, Any]]:
        data = extract_child_values(
            child, {"target_id": "INCREMENT ARC/Target", "value": "INCREMENT ARC/Value"}
        )

        if not data.get("target_id") or data["target_id"] not in object_map:
            return None
        if data.get("value") is None:
            return None

        return {
            "lvgl.arc.update": {
                "id": object_map[data["target_id"]],
                "value": ESPHomeLambda(
                    f"return float({data['value']} + lv_arc_get_value(id({object_map[data['target_id']]})));"
                ),
            }
        }


class IncrementBarHandler(ActionHandler):
    """Handler for INCREMENT BAR actions."""

    def handle(
        self, child: Dict[str, Any], yaml_root_key: str, object_map: Dict[str, str]
    ) -> Optional[Dict[str, Any]]:
        data = extract_child_values(
            child,
            {
                "target_id": "INCREMENT BAR/Target",
                "value": "INCREMENT BAR/Value",
                "animate": "INCREMENT BAR/Animate",
            },
        )

        if not data.get("target_id") or data["target_id"] not in object_map:
            return None
        if data.get("value") is None:
            return None

        return {
            "lvgl.bar.update": {
                "id": object_map[data["target_id"]],
                "animated": data.get("animate") == "ON",
                "value": ESPHomeLambda(
                    f"return float({data['value']} + lv_bar_get_value(id({object_map[data['target_id']]})));"
                ),
            }
        }


class IncrementSliderHandler(ActionHandler):
    """Handler for INCREMENT SLIDER actions."""

    def handle(
        self, child: Dict[str, Any], yaml_root_key: str, object_map: Dict[str, str]
    ) -> Optional[Dict[str, Any]]:
        data = extract_child_values(
            child,
            {
                "target_id": "INCREMENT SLIDER/Target",
                "value": "INCREMENT SLIDER/Value",
                "animate": "INCREMENT SLIDER/Animate",
            },
        )

        if not data.get("target_id") or data["target_id"] not in object_map:
            return None
        if data.get("value") is None:
            return None

        return {
            "lvgl.slider.update": {
                "id": object_map[data["target_id"]],
                "animated": data.get("animate") == "ON",
                "value": ESPHomeLambda(
                    f"return float({data['value']} + lv_slider_get_value(id({object_map[data['target_id']]})));"
                ),
            }
        }


class BasicPropertyHandler(ActionHandler):
    """Handler for BASIC_PROPERTY actions."""

    def handle(
        self, child: Dict[str, Any], yaml_root_key: str, object_map: Dict[str, str]
    ) -> Optional[Dict[str, Any]]:
        data = extract_child_values(
            child,
            {
                "target_id": "BASIC_PROPERTY/Target",
                "property": "BASIC_PROPERTY/Property",
                "value": "BASIC_PROPERTY/Value",
            },
        )

        if not validate_required_fields(data, ["target_id", "property"]):
            return None
        if data["target_id"] not in object_map or data.get("value") is None:
            return None

        esp_property = data["property"].lower().replace(" ", "_")
        if data["property"] == "Position_X":
            esp_property = "x"
        elif data["property"] == "Position_Y":
            esp_property = "y"

        return {
            "lvgl.widget.update": {
                "id": object_map[data["target_id"]],
                esp_property: data["value"],
            }
        }


class SetOpacityHandler(ActionHandler):
    """Handler for SET OPACITY actions."""

    def handle(
        self, child: Dict[str, Any], yaml_root_key: str, object_map: Dict[str, str]
    ) -> Optional[Dict[str, Any]]:
        data = extract_child_values(
            child, {"target_id": "SET OPACITY/Target", "value": "SET OPACITY/Value"}
        )

        if not data.get("target_id") or data["target_id"] not in object_map:
            return None
        if data.get("value") is None:
            data["value"] = 255

        return {
            "lvgl.widget.update": {
                "id": object_map[data["target_id"]],
                "opa": float(data["value"]) / 255.0,
            }
        }


class SliderPropertyHandler(ActionHandler):
    """Handler for SLIDER_PROPERTY actions."""

    def handle(
        self, child: Dict[str, Any], yaml_root_key: str, object_map: Dict[str, str]
    ) -> Optional[Dict[str, Any]]:
        data = extract_child_values(
            child,
            {
                "target_id": "SLIDER_PROPERTY/Target",
                "property": "SLIDER_PROPERTY/Property",
                "value": "SLIDER_PROPERTY/Value",
            },
        )

        if not validate_required_fields(data, ["target_id", "property"]):
            return None
        if data["target_id"] not in object_map or data.get("value") is None:
            return None

        return {
            "lvgl.slider.update": {
                "id": object_map[data["target_id"]],
                "animated": data["property"] == "Value_with_anim",
                "value": int(data["value"]),
            }
        }


class BarPropertyHandler(ActionHandler):
    """Handler for BAR_PROPERTY actions."""

    def handle(
        self, child: Dict[str, Any], yaml_root_key: str, object_map: Dict[str, str]
    ) -> Optional[Dict[str, Any]]:
        data = extract_child_values(
            child,
            {
                "target_id": "BAR_PROPERTY/Target",
                "property": "BAR_PROPERTY/Property",
                "value": "BAR_PROPERTY/Value",
            },
        )

        if not validate_required_fields(data, ["target_id", "property"]):
            return None
        if data["target_id"] not in object_map or data.get("value") is None:
            return None

        return {
            "lvgl.bar.update": {
                "id": object_map[data["target_id"]],
                "animated": data["property"] == "Value_with_anim",
                "value": int(data["value"]),
            }
        }


class RollerPropertyHandler(ActionHandler):
    """Handler for ROLLER_PROPERTY actions."""

    def handle(
        self, child: Dict[str, Any], yaml_root_key: str, object_map: Dict[str, str]
    ) -> Optional[Dict[str, Any]]:
        data = extract_child_values(
            child,
            {
                "target_id": "ROLLER_PROPERTY/Target",
                "property": "ROLLER_PROPERTY/Property",
                "value": "ROLLER_PROPERTY/Value",
            },
        )

        if not validate_required_fields(data, ["target_id", "property"]):
            return None
        if data["target_id"] not in object_map or data.get("value") is None:
            return None

        return {
            "lvgl.roller.update": {
                "id": object_map[data["target_id"]],
                "animated": data["property"] == "Value_with_anim",
                "selected_index": int(data["value"]),
            }
        }


class StepSpinboxHandler(ActionHandler):
    """Handler for STEP SPINBOX actions."""

    def handle(
        self, child: Dict[str, Any], yaml_root_key: str, object_map: Dict[str, str]
    ) -> Optional[Dict[str, Any]]:
        data = extract_child_values(
            child,
            {"target_id": "STEP SPINBOX/Target", "direction": "STEP SPINBOX/Direction"},
        )

        if not data.get("target_id") or data["target_id"] not in object_map:
            return None
        if data.get("direction") is None:
            return None

        if data["direction"] == "1":
            return {"lvgl.spinbox.increment": {"id": object_map[data["target_id"]]}}
        elif data["direction"] == "-1":
            return {"lvgl.spinbox.decrement": {"id": object_map[data["target_id"]]}}

        return None


class ModifyFlagHandler(ActionHandler):
    """Handler for MODIFY FLAG actions."""

    def handle(
        self, child: Dict[str, Any], yaml_root_key: str, object_map: Dict[str, str]
    ) -> Optional[Dict[str, Any]]:
        data = extract_child_values(
            child,
            {
                "target_id": "MODIFY FLAG/Object",
                "flag": "MODIFY FLAG/Flag",
                "action": "MODIFY FLAG/Action",
            },
        )

        if not validate_required_fields(data, ["target_id", "flag", "action"]):
            return None
        if data["target_id"] not in object_map:
            return None

        state = True
        if data["action"] == "REMOVE":
            state = False
        elif data["action"] == "TOGGLE":
            state = ESPHomeLambda(
                f"return !lv_obj_has_flag(id({object_map[data['target_id']]}), LV_OBJ_FLAG_{data['flag']});"
            )

        return {
            "lvgl.widget.update": {
                "id": object_map[data["target_id"]],
                data["flag"].lower(): state,
            }
        }


class ModifyStateHandler(ActionHandler):
    """Handler for MODIFY STATE actions."""

    def handle(
        self, child: Dict[str, Any], yaml_root_key: str, object_map: Dict[str, str]
    ) -> Optional[Dict[str, Any]]:
        data = extract_child_values(
            child,
            {
                "target_id": "MODIFY STATE/Object",
                "state": "MODIFY STATE/State",
                "action": "MODIFY STATE/Action",
            },
        )

        if not validate_required_fields(data, ["target_id", "state", "action"]):
            return None
        if data["target_id"] not in object_map:
            return None

        set_state = True
        if data["action"] == "REMOVE":
            set_state = False
        elif data["action"] == "TOGGLE":
            # Note: There's a bug in the original code - it uses 'flag' instead of 'state'
            # Keeping it for compatibility but this should be investigated
            set_state = ESPHomeLambda(
                f"return !lv_obj_has_flag(id({object_map[data['target_id']]}), LV_OBJ_FLAG_{data['state']});"
            )

        return {
            "lvgl.widget.update": {
                "id": object_map[data["target_id"]],
                "state": {
                    data["state"].lower(): set_state,
                },
            }
        }


class KeyboardSetTargetHandler(ActionHandler):
    """Handler for KEYBOARD SET TARGET actions."""

    def handle(
        self, child: Dict[str, Any], yaml_root_key: str, object_map: Dict[str, str]
    ) -> Optional[Dict[str, Any]]:
        data = extract_child_values(
            child,
            {
                "keyboard_id": "KEYBOARD SET TARGET/Keyboard",
                "textarea_id": "KEYBOARD SET TARGET/TextArea",
            },
        )

        if not validate_required_fields(data, ["keyboard_id", "textarea_id"]):
            return None
        if (
            data["keyboard_id"] not in object_map
            or data["textarea_id"] not in object_map
        ):
            return None

        return {
            "lvgl.keyboard.update": {
                "id": object_map[data["keyboard_id"]],
                "textarea": object_map[data["textarea_id"]],
            }
        }


class SetTextValueFromArcHandler(ActionHandler):
    """Handler for SET TEXT VALUE FROM ARC actions."""

    def handle(
        self, child: Dict[str, Any], yaml_root_key: str, object_map: Dict[str, str]
    ) -> Optional[Dict[str, Any]]:
        data = extract_child_values(
            child,
            {
                "target_id": "SET TEXT VALUE FROM ARC/Target",
                "prefix": "SET TEXT VALUE FROM ARC/Prefix",
                "postfix": "SET TEXT VALUE FROM ARC/Postfix",
            },
        )

        if not data.get("target_id") or data["target_id"] not in object_map:
            return None

        prefix = data.get("prefix", "")
        postfix = data.get("postfix", "")

        return {
            "lvgl.label.update": {
                "id": object_map[data["target_id"]],
                "text": {
                    "format": "%s%d%s",
                    "args": [f'"{prefix}"', "x", f'"{postfix}"'],
                },
            }
        }


class SetTextValueFromSliderHandler(ActionHandler):
    """Handler for SET TEXT VALUE FROM SLIDER actions."""

    def handle(
        self, child: Dict[str, Any], yaml_root_key: str, object_map: Dict[str, str]
    ) -> Optional[Dict[str, Any]]:
        data = extract_child_values(
            child,
            {
                "target_id": "SET TEXT VALUE FROM SLIDER/Target",
                "prefix": "SET TEXT VALUE FROM SLIDER/Prefix",
                "postfix": "SET TEXT VALUE FROM SLIDER/Postfix",
            },
        )

        if not data.get("target_id") or data["target_id"] not in object_map:
            return None

        prefix = data.get("prefix", "")
        postfix = data.get("postfix", "")

        return {
            "lvgl.label.update": {
                "id": object_map[data["target_id"]],
                "text": {
                    "format": "%s%d%s",
                    "args": [f'"{prefix}"', "x", f'"{postfix}"'],
                },
            }
        }


class SetTextValueWhenCheckedHandler(ActionHandler):
    """Handler for SET TEXT VALUE WHEN CHECKED actions."""

    def handle(
        self, child: Dict[str, Any], yaml_root_key: str, object_map: Dict[str, str]
    ) -> Optional[Dict[str, Any]]:
        data = extract_child_values(
            child,
            {
                "target_id": "SET TEXT VALUE WHEN CHECKED/Target",
                "on_text": "SET TEXT VALUE WHEN CHECKED/On_text",
                "off_text": "SET TEXT VALUE WHEN CHECKED/Off_text",
            },
        )

        if not validate_required_fields(data, ["target_id", "on_text", "off_text"]):
            return None
        if data["target_id"] not in object_map:
            return None

        return {
            "lvgl.label.update": {
                "id": object_map[data["target_id"]],
                "text": {
                    "format": "%s",
                    "args": [f'x ? ""{data["on_text"]}"" : ""{data["off_text"]}""'],
                },
            }
        }


# Factory registry for action handlers
ACTION_HANDLERS: Dict[str, ActionHandler] = {
    "CALL FUNCTION": CallFunctionHandler(),
    "LABEL_PROPERTY": LabelPropertyHandler(),
    "CHANGE SCREEN": ChangeScreenHandler(),
    "INCREMENT ARC": IncrementArcHandler(),
    "INCREMENT BAR": IncrementBarHandler(),
    "INCREMENT SLIDER": IncrementSliderHandler(),
    "BASIC_PROPERTY": BasicPropertyHandler(),
    "SET OPACITY": SetOpacityHandler(),
    "SLIDER_PROPERTY": SliderPropertyHandler(),
    "BAR_PROPERTY": BarPropertyHandler(),
    "ROLLER_PROPERTY": RollerPropertyHandler(),
    "STEP SPINBOX": StepSpinboxHandler(),
    "MODIFY FLAG": ModifyFlagHandler(),
    "MODIFY STATE": ModifyStateHandler(),
    "KEYBOARD SET TARGET": KeyboardSetTargetHandler(),
    "SET TEXT VALUE FROM ARC": SetTextValueFromArcHandler(),
    "SET TEXT VALUE FROM SLIDER": SetTextValueFromSliderHandler(),
    "SET TEXT VALUE WHEN CHECKED": SetTextValueWhenCheckedHandler(),
}


def event_parser(
    node: Dict[str, Any],
    yaml_root_key: str,
    images: Dict[str, Any],
    object_map: Dict[str, str],
) -> Dict[str, Any]:
    """Parse SquareLine event handlers and convert to ESPHome format using factory pattern."""
    # Skip disabled events
    if node.get("disabled", False):
        return {}

    event = node.get("strval")
    if event not in EVENT_MAP:
        return {}
    event = EVENT_MAP[event]

    handlers = []
    for child in node.get("childs", []):
        if child.get("strtype") == "_event/action":
            action_type = child.get("strval")

            # Look up handler in factory registry
            handler = ACTION_HANDLERS.get(action_type)
            if handler:
                try:
                    result = handler.handle(child, yaml_root_key, object_map)
                    if result:
                        handlers.append(result)
                except Exception as e:
                    print(f"Error handling action {action_type}: {e}")
            else:
                # Log unsupported action types for future implementation
                print(f"Unsupported action type: {action_type}")

    if handlers:
        return {
            f"on_{event}": {
                "then": handlers,
            }
        }
    return {}
