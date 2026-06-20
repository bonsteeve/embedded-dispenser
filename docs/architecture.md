# Architecture

This document describes the design decisions behind the Embedded Control Framework and how the modules fit together.

## System context

The framework targets **Linux-based embedded controllers** that:

- Expose a network API to upstream applications
- Coordinate physical I/O through a hardware abstraction layer (not included here)
- Must remain responsive under concurrent sensor polling and command traffic

The four packages map to common firmware layers:

| Layer | Package | Responsibility |
|-------|---------|----------------|
| Communication | `websocket` | Parse, route, and respond to client messages |
| Orchestration | `process` | Model multi-step operations with timeouts |
| Observation | `sensors` | Register sensors and fan out change events |
| Actuation math | `motion` | Generate smooth acceleration profiles |

## WebSocket handler architecture

### Problem

A single WebSocket endpoint receives heterogeneous messages: heartbeats, status queries, long-running commands, and unknown payloads. A monolithic `if/elif` dispatcher becomes unmaintainable as handlers accumulate.

### Solution

The **Chain of Responsibility** pattern with explicit priorities:

1. Each handler implements `can_handle()` and `handle()`
2. `MessageRouter` sorts handlers by priority (ascending)
3. The first matching handler processes the message
4. A low-priority `EchoHandler` acts as fallback

### Key types

- `MessageHandler` — abstract handler contract
- `HandlerResponse` — typed response with optional broadcast flag
- `MessageProcessor` — coordinates routing and WebSocket I/O

### Extension

Add a handler by subclassing `MessageHandler`, choosing a priority, and calling `processor.add_handler()`. Handlers with priority `5` run before priority `100`.

```
Priority 5   → PingHandler      (heartbeat)
Priority 10  → HealthHandler    (structured status)
Priority 20  → YourHandler      (domain commands)
Priority 1000 → EchoHandler     (fallback)
```

## Gated transfer state machine

### Problem

Many industrial processes require an **operator trigger** to start, pause, and resume — for example a foot pedal, hold-to-run button, or safety interlock. The controller must:

- Wait for operator confirmation before starting
- Pause when the trigger is released
- Enforce timeouts at every wait point
- Report structured progress to clients

### Solution

`GatedTransferStateMachine` models the lifecycle as an explicit finite state machine:

```
IDLE ──start──▶ WAITING_OPERATOR ──press──▶ ACTIVE ◀──┐
                  │                         │         │
                  │ timeout                 │ release │
                  ▼                         ▼         │
               TIMEOUT                    PAUSED ──press┘
                                            │
                                         timeout
                                            ▼
                                         TIMEOUT

ACTIVE ──target reached──▶ COMPLETED
ACTIVE ──abort──────────▶ ABORTED
```

### Design details

- **Async lock** — All transitions are serialized to prevent race conditions between sensor callbacks and WebSocket commands.
- **Cancellable timeouts** — Each wait state starts an `asyncio` task; transitions cancel the previous timer.
- **Structured progress** — `ProcessProgress` tracks quantity, pauses, and elapsed time excluding pause duration.
- **Callback hook** — `on_state_change` enables WebSocket progress push without coupling the FSM to transport.

### Configuration

`ProcessConfig` holds timeout values. Use `ProcessConfig.for_testing()` in unit tests to avoid long sleeps.

## Sensor monitoring

### Problem

Dozens of sensors may be polled at different intervals. Downstream consumers (logging, safety interlocks, analytics) should not block the polling loop.

### Solution

A lightweight **observer** architecture:

1. `MonitorableSensor` — ABC implemented by hardware or simulated sensors
2. `SensorRegistry` — Central catalog with grouping and critical-sensor lookup
3. `EventDispatcher` — Background thread draining a bounded queue to registered listeners

### Event flow

```
Polling loop                EventDispatcher              Listeners
     │                            │                         │
     ├─ read_value()              │                         │
     ├─ detect change ──enqueue──▶ │                         │
     │                            ├─ dispatch change ──────▶│ on_sensor_change()
     │                            ├─ dispatch error ───────▶│ on_sensor_error()
```

Listeners can be registered per-sensor or globally. The queue is bounded (1000 events) to prevent unbounded memory growth under fault conditions.

## Motion profiling

### Problem

Stepper motors and pulse-driven actuators vibrate and lose steps when started or stopped abruptly. S-curve profiles ramp frequency smoothly through jerk-limited phases.

### Solution

Pure mathematical modules with zero hardware imports:

- `SCurveFunctions` — Jerk, linear, and constant frequency functions
- `MovementPhaseBuilder` — Assembles acceleration, cruise, and deceleration phases
- `AccelerationProfileCalculator` — Orchestrates a complete profile for a given step count

The calculator returns an `AccelerationProfile` containing phase durations and callable frequency functions. A GPIO pulse generator (not included) would iterate phases at runtime.

## Testing strategy

| Module | Approach |
|--------|----------|
| WebSocket | Async unit tests against handlers and router |
| Process | Async tests with short `ProcessConfig` timeouts |
| Sensors | Thread-based dispatcher tests with `SimulatedSensor` |
| Motion | Deterministic math assertions on profile shape |

No physical hardware is required. This mirrors how production firmware should be structured: business logic and math are testable in CI; hardware drivers are integration-tested separately.

## What is intentionally excluded

To keep this repository portable and safe for public distribution:

- GPIO pin assignments and I2C addresses
- Product-specific calibration constants
- Deployment configuration and environment secrets
- Proprietary message schemas and client integration details
- Hardware driver implementations (gpiozero, smbus, etc.)

These belong in a private firmware repository behind a thin adapter layer that implements the ABCs defined here.

## Subproject architecture

### Fluid transfer (`fluid_transfer`)

Layers production dispensing logic into composable controllers:

```
FluidTransferOrchestrator
  ├── GatedTransferStateMachine    (from embedded_control.process)
  ├── GateController               (delayed close scheduling)
  ├── PumpController               (speed + interlock handling)
  ├── FlowSensorMonitor            (pulse counting, low-flow detection)
  └── OperatorTriggerMonitor       (debounced press/release)
```

Hardware is accessed through `Protocol` interfaces (`TransferPump`, `FlowGate`, `PulseFlowSensor`, `OperatorTrigger`). Simulated implementations enable full integration tests without a physical dispensing unit.

### Robot arm (`robot_arm`)

Implements a five-stage positioning pipeline with the same structural pattern as production move-to-target controllers:

```
MultiStageMotionOrchestrator
  └── MotionStageExecutor
        ├── RETRACT → CLEARANCE → VERTICAL_ALIGN → HORIZONTAL_ALIGN → FINAL_APPROACH
        └── PositioningRetryHandler    (tolerance-based correction loop)
```

`PositionFeedback` and `MotorDriver` protocols abstract ADC reads and motor execution. In production, `MotorDriver` would delegate to the S-curve executor in `embedded_control.motion`.

See [projects/fluid-transfer/README.md](../projects/fluid-transfer/README.md) and [projects/robot-arm/README.md](../projects/robot-arm/README.md) for subproject-specific documentation.

- [README](../README.md) — Installation and quick-start examples
- [examples/demo_server.py](../examples/demo_server.py) — Runnable FastAPI WebSocket server
