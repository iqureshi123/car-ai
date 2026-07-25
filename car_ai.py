#!/usr/bin/env python3
"""
Car AI — an on-device diagnostic assistant for cars.

A local LLM (llama3.2:3b, served by Ollama) answers plain-English questions
about a vehicle by calling small "tool" functions that read OBD-II telemetry,
then explaining the result like a mechanic talking to a non-technical driver.

STATUS
------
Designed for a Raspberry Pi 5 (16GB). This repository runs against a SIMULATED
OBD-II data source (the MOCK_OBD dict below) — not a live vehicle. Swapping in
real readings via an ELM327 adapter and python-OBD is a contained change inside
the six reader functions; nothing above that layer moves.

Run the tool layer with no LLM and no third-party dependencies:
    python car_ai.py --selftest

Run the full assistant (requires Ollama serving llama3.2:3b locally):
    python car_ai.py
"""

from __future__ import annotations

import argparse
import json

MODEL = "llama3.2:3b"


# ---------------------------------------------------------------------------
# 1. SIMULATED VEHICLE STATE
# ---------------------------------------------------------------------------
# Every tool reads through this single dict. It is the seam between the AI layer
# and the car: when the ELM327 adapter is in hand, each reader below swaps its
# dict lookup for a python-OBD query and NOTHING above this layer changes. That
# is the whole reason the AI layer was built against a simulator first — the
# hardware integration becomes a six-function edit, not a rewrite.
MOCK_OBD = {
    "speed_kmh": 82,
    "rpm": 2400,
    "coolant_temp_c": 91,
    "fuel_level_pct": 47,
    "engine_load_pct": 34,
    "fault_codes": ["P0420"],
}

# Raw OBD-II hands you bare DTC strings like "P0420" — never the English
# meaning. We keep interpretation separate from the raw read, mirroring what
# live python-OBD actually returns.
DTC_DESCRIPTIONS = {
    "P0420": "Catalyst system efficiency below threshold (Bank 1)",
    "P0128": "Coolant thermostat below regulating temperature",
    "P0301": "Cylinder 1 misfire detected",
    "P0171": "System too lean (Bank 1)",
}


# ---------------------------------------------------------------------------
# 2. TOOL FUNCTIONS — the model may call any of these on its own
# ---------------------------------------------------------------------------
# Each returns a dict carrying the value, its UNIT, and a short CONTEXT string.
# This matters: hand a 3B model the bare integer 91 and it will confidently
# invent what it means. Hand it {"value": 91, "unit": "°C", "context": "...
# normal operating range is ~90-104 °C"} and it stays grounded in reality.

def get_speed() -> dict:
    return {
        "value": MOCK_OBD["speed_kmh"],
        "unit": "km/h",
        "context": "Current road speed of the vehicle.",
    }


def get_rpm() -> dict:
    return {
        "value": MOCK_OBD["rpm"],
        "unit": "rpm",
        "context": "Engine crankshaft speed. Idle is ~600-900 rpm; highway "
                   "cruising is ~1500-3000 rpm.",
    }


def get_coolant_temp() -> dict:
    return {
        "value": MOCK_OBD["coolant_temp_c"],
        "unit": "°C",
        "context": "Engine coolant temperature. Normal operating range is "
                   "~90-104 °C; sustained readings above ~110 °C risk "
                   "overheating.",
    }


def get_fuel_level() -> dict:
    return {
        "value": MOCK_OBD["fuel_level_pct"],
        "unit": "%",
        "context": "Fuel remaining as a percentage of tank capacity.",
    }


def get_engine_load() -> dict:
    return {
        "value": MOCK_OBD["engine_load_pct"],
        "unit": "%",
        "context": "Calculated engine load — the share of maximum available "
                   "torque currently being used.",
    }


def get_fault_codes() -> dict:
    codes = MOCK_OBD["fault_codes"]
    detailed = [
        {
            "code": code,
            "description": DTC_DESCRIPTIONS.get(
                code, "Unknown code — look up in a DTC reference."
            ),
        }
        for code in codes
    ]
    return {
        "codes": detailed,
        "count": len(detailed),
        "context": "Stored diagnostic trouble codes (DTCs). An empty list "
                   "means no codes are stored — i.e. no faults recorded.",
    }


# ---------------------------------------------------------------------------
# 3. TOOL REGISTRY + SCHEMAS
# ---------------------------------------------------------------------------
# TOOL_DISPATCH maps the name the model emits -> the Python function we run.
# TOOLS_SPEC is the JSON-schema description we send to the model so it knows
# what it is allowed to call. None of our tools take arguments, so each
# parameter block is empty.
TOOL_DISPATCH = {
    "get_speed": get_speed,
    "get_rpm": get_rpm,
    "get_coolant_temp": get_coolant_temp,
    "get_fuel_level": get_fuel_level,
    "get_engine_load": get_engine_load,
    "get_fault_codes": get_fault_codes,
}


def _tool_schema(name: str, description: str) -> dict:
    """Build the JSON schema for one no-argument tool."""
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    }


TOOLS_SPEC = [
    _tool_schema("get_speed", "Read the car's current road speed in km/h."),
    _tool_schema("get_rpm", "Read the engine's current speed in RPM."),
    _tool_schema("get_coolant_temp", "Read the engine coolant temperature in °C."),
    _tool_schema("get_fuel_level", "Read the fuel level as a percentage of tank capacity."),
    _tool_schema("get_engine_load", "Read the current calculated engine load as a percentage."),
    _tool_schema("get_fault_codes", "Read any stored OBD-II diagnostic trouble codes (DTCs)."),
]


# ---------------------------------------------------------------------------
# 4. TOOL DISPATCHER — never crashes the loop
# ---------------------------------------------------------------------------
def dispatch_tool(name: str, arguments: dict | None = None) -> dict:
    """Run the tool the model asked for and return a JSON-serialisable dict.

    Small local models sometimes hallucinate a tool name that doesn't exist.
    Rather than raise (which would kill the chat loop), we hand the model a
    structured error listing the real tools, so it can correct itself on the
    next turn instead of crashing.
    """
    fn = TOOL_DISPATCH.get(name)
    if fn is None:
        return {
            "error": f"Unknown tool '{name}'.",
            "available_tools": list(TOOL_DISPATCH),
        }
    try:
        return fn()  # our tools take no arguments
    except Exception as exc:  # defensive: a bad read must not kill the loop
        return {"error": f"Tool '{name}' failed: {exc}"}


# ---------------------------------------------------------------------------
# 5. THE ASSISTANT
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = (
    "You are Car AI, an on-device diagnostic assistant running inside a "
    "vehicle. When the user asks about the car's condition, CALL the "
    "appropriate tool to read the real sensor value — never guess or invent a "
    "number. After reading, explain what it means in plain language, like a "
    "good mechanic talking to a driver who isn't technical. Be concise and "
    "concrete, and say clearly whether the reading looks normal or not."
)


def chat_loop() -> None:
    # Imported here (not at module top) so `--selftest` runs with zero
    # third-party dependencies and without a running model server.
    try:
        import ollama
    except ImportError:
        print("The 'ollama' package isn't installed. Activate your venv, then:\n"
              "    pip install -r requirements.txt")
        return

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    print("Car AI ready — ask about your car. Type 'quit' to exit.\n")

    while True:
        try:
            user_input = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye")
            return
        if user_input.lower() in {"quit", "exit"}:
            return
        if not user_input:
            continue

        messages.append({"role": "user", "content": user_input})

        # Inner loop: the model may call one or more tools before it has enough
        # information to answer. We keep feeding tool results back until it
        # replies with plain text instead of another tool call.
        while True:
            try:
                response = ollama.chat(model=MODEL, messages=messages, tools=TOOLS_SPEC)
            except Exception as exc:
                print(f"car-ai> Couldn't reach the model ({exc}).\n"
                      f"        Is Ollama running and is '{MODEL}' pulled? Try:\n"
                      f"          ollama serve      # in another terminal\n"
                      f"          ollama pull {MODEL}\n")
                break

            message = response.message
            messages.append(message)

            # No tool call -> the model answered in plain text. Show it and
            # go back to waiting for the next user question.
            if not message.tool_calls:
                print(f"car-ai> {message.content}\n")
                break

            # Otherwise run every tool the model asked for and feed the
            # results back into the conversation for the next turn.
            for call in message.tool_calls:
                name = call.function.name
                args = call.function.arguments or {}
                result = dispatch_tool(name, args)
                print(f"  [tool] {name}() -> {result}")
                messages.append({
                    "role": "tool",
                    "content": json.dumps(result),
                    "tool_name": name,
                })


def self_test() -> None:
    """Exercise the tool layer without the LLM — no Ollama, no network."""
    print("Car AI — tool-layer self-test (no LLM required)\n")
    for name in TOOL_DISPATCH:
        print(f"  {name}() -> {dispatch_tool(name)}")
    # Prove graceful recovery from a hallucinated tool name:
    print("\n  Simulating a hallucinated tool name:")
    print(f"  dispatch_tool('get_tire_pressure') -> {dispatch_tool('get_tire_pressure')}")
    print("\nSelf-test complete — tool layer OK.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Car AI — a local LLM diagnostic assistant for cars."
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="Exercise the tool layer without calling the LLM (no Ollama needed).",
    )
    args = parser.parse_args()

    if args.selftest:
        self_test()
    else:
        chat_loop()


if __name__ == "__main__":
    main()
