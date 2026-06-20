![CI](https://github.com/bonsteeve/embedded-dispenser/actions/workflows/ci.yml/badge.svg?branch=main)
![Python](https://img.shields.io/badge/python-3.10%20|%203.11%20|%203.12-blue)
![License](https://img.shields.io/badge/license-MIT-green)
# Embedded Control Framework

A Python library of reusable patterns for building embedded control systems on Linux-based hardware (Raspberry Pi, industrial SBCs, and similar platforms). The framework demonstrates production-grade approaches to real-time communication, process orchestration, sensor monitoring, and motion profiling — without tying you to a specific product or hardware bill of materials.

## Why this exists

Industrial and IoT firmware often shares the same structural problems:

- Multiple clients need a **real-time control interface** (WebSocket, MQTT bridge, etc.)
- Long-running operations require **explicit state machines** with timeouts and operator gates
- Sensors must be monitored **continuously** without blocking control loops
- Actuators benefit from **smooth motion profiles** rather than abrupt start/stop

This repository extracts and generalizes those patterns into small, testable modules that run entirely in software — no GPIO, no proprietary configuration, no deployment secrets.

## Feature subprojects

Beyond the core framework, two domain-specific subprojects demonstrate full end-to-end systems:

| Subproject | Package | What it demonstrates |
|------------|---------|---------------------|
| **[Fluid Transfer](projects/fluid-transfer/)** | `fluid_transfer` | Pump + flow gate interlocks, pulse flow sensing, operator-gated dispensing orchestration |
| **[Robot Arm](projects/robot-arm/)** | `robot_arm` | Six-stage positioning pipeline, closed-loop retry, progress callbacks |

Each subproject has its own README, runnable simulation, and tests. See [projects/README.md](projects/README.md) for the full index.

```
┌─────────────────────────────────────────────────────────────┐
│                     Client Applications                      │
└───────────────────────────┬─────────────────────────────────┘
                            │ WebSocket / JSON
┌───────────────────────────▼─────────────────────────────────┐
│  websocket/          Priority-based message routing          │
│  ├── MessageRouter   First-match handler dispatch             │
│  ├── MessageProcessor  Response + broadcast coordination      │
│  └── handlers/       Ping, health, echo (extensible)          │
└───────────────────────────┬─────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌───────────────┐  ┌────────────────┐  ┌──────────────────┐
│  process/     │  │  sensors/      │  │  motion/         │
│  Gated        │  │  Registry +    │  │  S-curve profile │
│  transfer FSM │  │  event dispatch│  │  calculator      │
└───────────────┘  └────────────────┘  └──────────────────┘
```

See [docs/architecture.md](docs/architecture.md) for design rationale and extension points.

## Modules

| Module | Purpose |
|--------|---------|
| `embedded_control.websocket` | Extensible handler architecture with priority routing |
| `embedded_control.process` | Async state machine for operator-gated transfer operations |
| `embedded_control.sensors` | Observer-pattern sensor registry and event dispatcher |
| `embedded_control.motion` | Pure-math S-curve acceleration profile generation |
| `fluid_transfer` | Operator-gated fluid transfer orchestration (subproject) |
| `robot_arm` | Multi-stage motion orchestration with positioning retry (subproject) |

## Architecture

### Install

```bash
git clone https://github.com/bonsteeve/embedded-dispenser.git
cd embedded-control-framework
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### Run tests

```bash
pytest -v
```

### Run the demo server

```bash
cd examples
python demo_server.py
```

Then connect with any WebSocket client:

```bash
# Plain-text heartbeat
websocat ws://localhost:8080/ws
> ping
< pong

# JSON health check
> {"action": "health"}
< {"type": "health", "status": "ok", "service": "embedded-control"}
```

## Usage examples

### WebSocket handler routing

```python
from embedded_control.websocket import MessageHandler, MessageProcessor, HandlerResponse, ResponseType

class StatusHandler(MessageHandler):
    def __init__(self):
        super().__init__(priority=20)

    def can_handle(self, message, parsed_data=None):
        return parsed_data and parsed_data.get("action") == "status"

    async def handle(self, message, parsed_data=None):
        return HandlerResponse(
            type=ResponseType.STATUS,
            data={"type": "status", "state": "idle"},
        )

processor = MessageProcessor()
processor.add_handler(StatusHandler())
```

### Operator-gated process state machine

```python
from embedded_control.process import GatedTransferStateMachine, ProcessRequest

machine = GatedTransferStateMachine()
await machine.start(ProcessRequest("req-1", target_quantity=100.0, target_slot="A1"))
await machine.on_operator_pressed()   # operator trigger engaged
await machine.update_progress(100.0)  # target reached → COMPLETED
```

### Sensor event dispatch

```python
from embedded_control.sensors import SensorRegistry, SensorConfig, SimulatedSensor, EventDispatcher

registry = SensorRegistry()
registry.register(SimulatedSensor("temp-1"), SensorConfig(group="thermal", is_critical=True))

dispatcher = EventDispatcher()
dispatcher.start_processing()
# Enqueue SensorChangeEvent instances from your polling loop
```

### S-curve motion profile

```python
from embedded_control.motion import AccelerationProfileCalculator, SCurveParameters

calculator = AccelerationProfileCalculator(min_frequency=100.0, max_frequency=5000.0)
profile = calculator.calculate_s_curve_profile(
    SCurveParameters(acceleration_time=0.5, deceleration_time=0.5),
    target_frequency=3000.0,
    total_steps=1000,
)
print(f"Duration: {profile.total_duration:.3f}s, phases: {len(profile.phases)}")
```

## Design principles

1. **Hardware abstraction** — Interfaces are defined against protocols and ABCs; swap in real GPIO/I2C drivers behind the same contracts.
2. **Testability first** — Every module runs in CI without physical hardware via mocks and simulated sensors.
3. **Explicit state** — Long-running operations use enumerated states, structured progress tracking, and cancellable timeouts.
4. **Separation of concerns** — Routing, process logic, sensor events, and motion math live in independent packages.

