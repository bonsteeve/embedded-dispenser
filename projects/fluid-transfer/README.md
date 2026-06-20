# Fluid Transfer

Operator-gated fluid transfer with pump interlocks, flow-gate control, pulse-based volume tracking, and async process orchestration.

## Overview

This subproject demonstrates how to coordinate a **dispensing unit** — pump, solenoid gate, flow sensor, and operator trigger — as a single cohesive system. It builds on the core framework's `GatedTransferStateMachine` and adds hardware-specific controllers with protocol-based interfaces.

```
Client request
     │
     ▼
TransferRequestParser ──▶ FluidTransferOrchestrator
                                │
           ┌────────────────────┼────────────────────┐
           ▼                    ▼                    ▼
   GatedTransferStateMachine  GateController    PumpController
           │                    │                    │
           ▼                    ▼                    ▼
   OperatorTriggerMonitor   FlowGate (protocol)  TransferPump (protocol)
                                │
                                ▼
                        FlowSensorMonitor
                                │
                                ▼
                        PulseFlowSensor (protocol)
```

## Key design decisions

| Pattern | Implementation |
|---------|----------------|
| Safety interlock | Pump refuses to start unless gate is open |
| Delayed gate close | Gate stays open briefly after operator release (prevents fluid hammer) |
| Operator gating | State machine enforces wait → active → pause → complete flow |
| Hardware abstraction | `Protocol` interfaces for pump, gate, sensor, trigger |
| Testability | `Simulated*` classes run full flows without GPIO |

## Package

```python
from fluid_transfer import FluidTransferOrchestrator, FluidTransferConfig
from fluid_transfer.simulated import (
    SimulatedFlowGate,
    SimulatedTransferPump,
    SimulatedPulseFlowSensor,
    SimulatedOperatorTrigger,
)
```

## Run the simulation

```bash
cd projects/fluid-transfer/examples
python run_simulation.py
```

## Request format

```json
{
  "action": "transfer",
  "volume": 100.0,
  "request_id": "req-001",
  "slot": "A1"
}
```

## Mapping from production firmware

| Production concept | Generalized name |
|--------------------|------------------|
| Dispense pump | `TransferPump` |
| Solenoid valve | `FlowGate` |
| Flow meter | `PulseFlowSensor` |
| Foot switch | `OperatorTrigger` |
| Dispense handler | `FluidTransferOrchestrator` |
| Bay (C1–C6) | Slot (A1–B3) |

Product-specific pin maps, calibration constants, and GPIO drivers are intentionally excluded. Implement the `Protocol` interfaces against your hardware layer.
