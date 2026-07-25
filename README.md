# Car AI

An on-device diagnostic assistant for cars. Ask your car a question in plain
English — *"is my engine running hot?"* — and a local LLM reads the relevant
OBD-II sensor and answers like a mechanic explaining it to a normal person.

No cloud — the model, the tools, and the logic all run locally on the device.

---

## Status — read this first

**Designed for a Raspberry Pi 5 (16GB). This repository runs against simulated
OBD-II data, not a live vehicle.**

| Component | State |
|---|---|
| Six OBD-II reader tools + dispatcher, each with a JSON schema | ✅ Verified by self-test |
| Tools return value + unit + context (not bare numbers) | ✅ Verified by self-test |
| Graceful recovery from hallucinated tool names | ✅ Verified by self-test |
| Simulated OBD-II data source (`MOCK_OBD`) | ✅ Working |
| Full LLM chat loop — end-to-end tool calling with `llama3.2:3b` | ⚠️ Code complete; not yet run end-to-end |
| Live OBD-II reads (ELM327 adapter + python-OBD) | ⛔ Not started |
| In-car screen + 3D-printed enclosure | ⛔ Not started |
| Validated on-vehicle / on-Pi performance | ⛔ Not yet verified |

**"Verified by self-test"** means exercised by `python car_ai.py --selftest`,
which runs the tool layer with no model attached. The full chat loop is written
but has **not yet been run end-to-end** against a live Ollama server, and
nothing has been validated on the Pi or in a vehicle yet.

This is a working local-AI **tool layer** with a complete-but-unverified LLM
loop, running on **simulated** vehicle input. It is not a finished in-car
product, and this README does not pretend otherwise.

---

## Why local, not cloud

- Cars lose signal in tunnels, garages, and rural roads — exactly where you
  most need to know whether a noise or a warning light matters.
- Paying a cloud API call to be told your coolant is fine is absurd.
- Vehicle telemetry is effectively location data; it shouldn't leave the car.

Every technical decision below follows from that constraint.

---

## How it works

1. You ask a question. It goes to `llama3.2:3b` running under Ollama, together
   with the list of tool schemas (the six readers).
2. Instead of guessing a number, the model emits a **tool call** — e.g.
   `get_coolant_temp()`.
3. The dispatcher runs that Python function, which reads the (currently
   simulated) sensor and returns a dict with the **value, its unit, and
   context**.
4. That result is appended to the conversation and sent back to the model.
5. The model may call more tools, or — once it has what it needs — answer in
   plain language.

Two deliberate design choices make a small model reliable here:

- **Tools return dicts with units and context, not bare numbers.** A 3B model
  handed the integer `91` will confidently guess what it means. Handed
  `{"value": 91, "unit": "°C", "context": "normal is ~90-104 °C"}`, it stays
  grounded.
- **The dispatcher never throws.** Small local models sometimes hallucinate a
  tool name. The dispatcher returns a structured error listing the real tools,
  so the model recovers on its next turn instead of crashing the loop.

### The six tools

| Tool | Reads |
|---|---|
| `get_speed` | road speed (km/h) |
| `get_rpm` | engine speed (rpm) |
| `get_coolant_temp` | coolant temperature (°C) |
| `get_fuel_level` | fuel remaining (%) |
| `get_engine_load` | calculated engine load (%) |
| `get_fault_codes` | stored diagnostic trouble codes (DTCs) |

### The simulator seam

Every tool reads through one dict, `MOCK_OBD`. Swapping in live python-OBD
reads is a contained change inside those six functions — nothing above them
moves. That is why the AI layer was built against a simulator first instead of
blocking on hardware.

---

## Running it

### Tool layer only — no model, no dependencies

```bash
python car_ai.py --selftest
```

Exercises all six tools and the hallucinated-tool-name recovery path. Runs
anywhere Python runs.

### Full assistant

Requires Ollama serving `llama3.2:3b` locally.

```bash
python -m venv car_ai_env
source car_ai_env/bin/activate        # Windows: car_ai_env\Scripts\activate
pip install -r requirements.txt

ollama pull llama3.2:3b               # ~2 GB
python car_ai.py
```

Then ask things like *"is my engine running hot?"* or *"do I have any fault
codes?"*

---

## Why `llama3.2:3b` (Q4_K_M)

The Pi 5 has no usable GPU, so the model search was limited to small quantized
models that support function calling. `llama3.2:3b` at Q4_K_M is ~2.0 GB and is
one of the smallest that does. Whether it calls these six tools reliably enough
in practice is exactly what the end-to-end verification (see Status) still needs
to confirm. This was a hardware-constraint problem, not an ML problem.

---

## Roadmap

- [ ] Run the full chat loop end-to-end against Ollama and confirm the model
      calls the six tools reliably
- [ ] Live OBD-II reads via an ELM327 adapter (python-OBD), behind the same six
      functions
- [ ] Verify end-to-end operation on the Pi 5 and measure latency under real
      driving conditions
- [ ] In-car screen
- [ ] 3D-printed enclosure

---

## Team

- **Ibrahim Qureshi** — AI & software layer: Ollama setup, model selection and
  testing, tool-call design, and Pi environment setup (Ollama, model,
  virtualenv, SSH).
- Collaborator — hardware integration and the in-car screen.
- Collaborator — CAD and the 3D-printed enclosure.
