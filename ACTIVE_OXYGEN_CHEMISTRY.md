# Pool Active Oxygen Chemistry - Understanding Your Active Oxygen Sensor

## Overview

The Poollab integration supports active oxygen monitoring for systems that sanitize with active oxygen products (commonly based on MPS). This document explains how to interpret active oxygen values in Home Assistant.

## Active Oxygen Sensor

### Active Oxygen 🫧

**What it is**: The residual active oxygen measurement available for sanitization support.

**Sensor**: `sensor.pool_name_active_oxygen`

**API field compatibility**: The integration accepts multiple LabCom names:
- `PL Active Oxygen`
- `PL Active Oxygen (MPS)`
- `PL Active Oxygen MPS`
- `PL MPS`
- `PL Aktivsauerstoff`
- `PL Aktivsauerstoff (MPS)`

**Integration behavior**: Direct measurement from LabCom. No local active-oxygen formula is calculated by the integration.

**Valid integration range**: 0-30 ppm

## Practical Target Guidance

Typical active oxygen product targets often sit around 4-8 ppm, but exact values can vary by product line and pool type.

Always follow your chemical manufacturer instructions and local pool guidance as the primary source of truth.

## What the Numbers Tell You

**Scenario 1: In target range** ✅
- Active Oxygen: 5.0 ppm

**Analysis**: Typical value for many active oxygen treatment programs.

**Scenario 2: Low residual** ⚠️
- Active Oxygen: 2.5 ppm

**Analysis**: Oxidation/sanitizing support may be weak. Consider product-specific re-dosing guidance.

**Scenario 3: High residual** ⚠️
- Active Oxygen: 12.0 ppm

**Analysis**: Value may be above your operational target. Re-check dose timing and product instructions.

## Using Active Oxygen Sensors in Home Assistant

### Dashboard Example

```yaml
type: entities
title: Pool Active Oxygen Status
entities:
  - entity: sensor.backyard_pool_active_oxygen
    name: Active Oxygen
    icon: mdi:molecule
```

### Automation: Low Active Oxygen Alert

```yaml
alias: "Pool: Low Active Oxygen Alert"
description: Alert when active oxygen residual is too low
trigger:
  - platform: numeric_state
    entity_id: sensor.backyard_pool_active_oxygen
    below: 4.0
    for:
      hours: 1
action:
  - service: notify.mobile_app
    data:
      title: "Pool Active Oxygen Low"
      message: >
        Active oxygen is {{ states('sensor.backyard_pool_active_oxygen') }} ppm.
        Check your MPS/active oxygen dosing schedule.
      data:
        priority: high
        icon: mdi:molecule
```

### Automation: High Active Oxygen Alert

```yaml
alias: "Pool: High Active Oxygen Alert"
description: Alert when active oxygen residual is above your comfort threshold
trigger:
  - platform: numeric_state
    entity_id: sensor.backyard_pool_active_oxygen
    above: 10.0
    for:
      hours: 1
action:
  - service: notify.mobile_app
    data:
      title: "Pool Active Oxygen High"
      message: >
        Active oxygen is {{ states('sensor.backyard_pool_active_oxygen') }} ppm.
        Verify target range and adjust treatment if required.
      data:
        priority: high
        icon: mdi:water-alert
```

## Troubleshooting

### Active Oxygen Sensor Shows "Unavailable"

Possible causes:
1. No active oxygen measurement is present in the latest synced LabCom data.
2. Latest value is outside the integration's valid range (0-30 ppm).
3. Temporary API/connectivity issue.

### Your LabCom Export Uses a Different Label

The integration already supports both English and German labels plus MPS variants. If your label still differs, open an issue and include the exact parameter name from your measurement data.

## Related Documentation

- [README.md](README.md)
- [CHLORINE_CHEMISTRY.md](CHLORINE_CHEMISTRY.md)
- [BROMINE_CHEMISTRY.md](BROMINE_CHEMISTRY.md)
