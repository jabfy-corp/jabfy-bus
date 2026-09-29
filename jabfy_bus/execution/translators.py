"""Traducteurs : commande normalisée -> requête native par protocole.

Même action logique, cibles différentes :

| Protocole | turn_on                                     |
|-----------|---------------------------------------------|
| MQTT      | publish `<topic>/set {"state": "ON"}`       |
| HTTP      | POST /relay/0?turn=on                       |
| Modbus    | write coil <address> = true                 |
"""

from __future__ import annotations

from typing import Any, Callable

from jabfy_bus.core.errors import UnknownProtocol
from jabfy_bus.core.types import Action

# Un traducteur reçoit le dict `command` du message et retourne la
# requête native : {"target": ..., "payload": ...}.
Translator = Callable[[dict[str, Any]], dict[str, Any]]

_MQTT_STATE = {
    Action.TURN_ON: "ON",
    Action.TURN_OFF: "OFF",
    Action.TOGGLE: "TOGGLE",
}


def to_mqtt(command: dict[str, Any]) -> dict[str, Any]:
    action = Action(command["action"])
    topic = command.get("mqtt_topic") or command["target"]
    if not topic.endswith("/set"):
        topic = f"{topic}/set"
    if action in _MQTT_STATE:
        payload: dict[str, Any] = {"state": _MQTT_STATE[action]}
    elif action is Action.SET_BRIGHTNESS:
        payload = {"brightness": command["params"]["brightness"]}
    elif action is Action.SET_COLOR:
        payload = {"color": command["params"]["color"]}
    elif action is Action.SET_TEMPERATURE:
        payload = {"occupied_heating_setpoint": command["params"]["temperature"]}
    elif action is Action.SET_POSITION:
        payload = {"position": command["params"]["position"]}
    elif action is Action.SET_TILT:
        payload = {"tilt": command["params"]["tilt"]}
    elif action is Action.SET_MODE:
        payload = {"system_mode": command["params"]["mode"]}
    else:
        payload = {"action": action.value, **command.get("params", {})}
    return {"target": topic, "payload": payload}


_HTTP_TURN = {Action.TURN_ON: "on", Action.TURN_OFF: "off", Action.TOGGLE: "toggle"}


def to_http(command: dict[str, Any]) -> dict[str, Any]:
    action = Action(command["action"])
    base_url = command.get("http_url") or command["target"]
    if action in _HTTP_TURN:
        return {
            "target": f"{base_url}?turn={_HTTP_TURN[action]}",
            "payload": None,
            "method": "POST",
        }
    return {
        "target": base_url,
        "payload": {"action": action.value, **command.get("params", {})},
        "method": "POST",
    }


def to_modbus(command: dict[str, Any]) -> dict[str, Any]:
    action = Action(command["action"])
    address = command.get("modbus_address") or command["target"]
    if action is Action.TURN_ON:
        value: Any = True
    elif action is Action.TURN_OFF:
        value = False
    elif action is Action.SET_VALUE:
        value = command["params"]["value"]
    else:
        raise ValueError(f"action '{action.value}' not supported over modbus")
    return {
        "target": address,
        "payload": {"register_type": command.get("register_type", "coil"), "value": value},
    }


def to_simulation(command: dict[str, Any]) -> dict[str, Any]:
    """Le lab de simulation consomme la commande normalisée telle quelle."""
    return {"target": command["target"], "payload": dict(command)}


TRANSLATORS: dict[str, Translator] = {
    "mqtt": to_mqtt,
    "zigbee": to_mqtt,  # via zigbee2mqtt, la cible reste un topic MQTT
    "http": to_http,
    "modbus_tcp": to_modbus,
    "simulation": to_simulation,
}


def translate(protocol: str, command: dict[str, Any]) -> dict[str, Any]:
    translator = TRANSLATORS.get(protocol)
    if translator is None:
        raise UnknownProtocol(protocol)
    return translator(command)
