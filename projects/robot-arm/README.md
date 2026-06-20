# Robot Arm

Multi-stage two-axis motion orchestration with closed-loop positioning, tolerance-based retry, and structured progress reporting.

## Overview

This subproject demonstrates a **five-stage positioning pipeline** for a two-axis robotic arm — the same architectural pattern used in production systems for moving to named target positions with safety clearance zones.

```
move_to_slot("B2")
     │
     ▼
MultiStageMotionOrchestrator
     │
     ▼
MotionStageExecutor ── per stage ──▶ StageResult
     │
     ├── RETRACT           (safe vertical position)
     ├── CLEARANCE         (shared transit height)
     ├── VERTICAL_ALIGN    (closed-loop with retry)
     ├── HORIZONTAL_ALIGN  (closed-loop with retry)
     └── FINAL_APPROACH    (precision docking)
```

## Key design decisions

| Pattern | Implementation |
|---------|----------------|
| Stage pipeline | Ordered `MotionStage` enum with per-stage `StageResult` |
| Progress callbacks | `MotionProgressCallback` Protocol for WebSocket/UI integration |
| Closed-loop retry | `PositioningRetryHandler` corrects until within tolerance |
| Hardware abstraction | `PositionFeedback` and `MotorDriver` protocols |
| Configuration-driven | Slot coordinates and tolerances in `RobotArmConfig` |

## Package

```python
from robot_arm import MultiStageMotionOrchestrator, RobotArmConfig
from robot_arm.simulated import SimulatedPositionFeedback, SimulatedMotorDriver
```

## Run the simulation

```bash
cd projects/robot-arm/examples
python run_simulation.py
```

## Stage sequence

| Stage | Purpose |
|-------|---------|
| `RETRACT` | Move to safe retracted height |
| `CLEARANCE` | Traverse shared clearance zone |
| `VERTICAL_ALIGN` | Align to target level with retry |
| `HORIZONTAL_ALIGN` | Align to target column with retry |
| `FINAL_APPROACH` | Precision final positioning |

## Mapping from production firmware

| Production concept | Generalized name |
|--------------------|------------------|
| Move-to-container controller | `MultiStageMotionOrchestrator` |
| Movement stages (undock, free space, etc.) | `MotionStage` enum |
| ADC position tracker | `PositionFeedback` protocol |
| S-curve executor | `MotorDriver` protocol (simplified) |
| Positioning retry handler | `PositioningRetryHandler` |
| Container bays | Configurable slots in `RobotArmConfig` |

The core framework's `embedded_control.motion` package provides the S-curve math used in production. This subproject focuses on orchestration and closed-loop positioning. NFC scanning, docking switches, and GPIO pin management are excluded as product-specific integration layers.

## Extending with real hardware

1. Implement `PositionFeedback` against your ADC/encoder driver
2. Implement `MotorDriver` using the S-curve executor from `embedded_control.motion`
3. Replace `Simulated*` classes in the orchestrator constructor
4. Wire `MotionProgressCallback` to your WebSocket handler for live updates
