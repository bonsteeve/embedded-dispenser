# Projects

Feature subprojects built on the [core framework](../README.md). Each subproject is a self-contained demonstration of a major embedded control domain, generalized from production firmware patterns.

| Subproject | Package | Description |
|------------|---------|-------------|
| [Fluid Transfer](fluid-transfer/) | `fluid_transfer` | Operator-gated dispensing: pump, flow gate, pulse flow sensor, orchestrator |
| [Robot Arm](robot-arm/) | `robot_arm` | Multi-stage two-axis positioning with closed-loop retry |

## Repository layout

```
embedded-control-framework/
├── src/
│   ├── embedded_control/     # Core patterns (WebSocket, sensors, process FSM, motion math)
│   ├── fluid_transfer/       # Fluid transfer subproject
│   └── robot_arm/            # Robot arm subproject
├── projects/
│   ├── fluid-transfer/       # Docs and runnable examples
│   └── robot-arm/
├── tests/                    # Unit tests for all packages
└── examples/                 # Core framework demo server
```

## Install

All packages install together from the repository root:

```bash
pip install -e ".[dev]"
```

## Run subproject simulations

```bash
# Fluid transfer
python projects/fluid-transfer/examples/run_simulation.py

# Robot arm
python projects/robot-arm/examples/run_simulation.py
```

## Relationship to core framework

| Core module | Used by |
|-------------|---------|
| `embedded_control.process` | `fluid_transfer` — gated transfer state machine |
| `embedded_control.motion` | `robot_arm` — S-curve math (extend via `MotorDriver`) |
| `embedded_control.websocket` | Either subproject — wire orchestrators to WebSocket handlers |
| `embedded_control.sensors` | Either subproject — monitor hardware health alongside operations |

Each subproject defines its own `Protocol` interfaces for hardware. Swap `Simulated*` implementations for real drivers without changing orchestration logic.
