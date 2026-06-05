# Pool Bromine Chemistry - Understanding Your Bromine Sensor

## Overview

The Poollab integration supports bromine monitoring for pools and spas that use bromine-based sanitation instead of chlorine. This document explains how to interpret bromine values in Home Assistant.

## Bromine Sensor

### Bromine 🟤

**What it is**: The residual bromine currently available for sanitization.

**Sensor**: `sensor.pool_name_bromine`

**API field**: `PL Bromine`

**Integration behavior**: Direct measurement from LabCom. No local bromine formula is calculated by the integration.

**Valid integration range**: 0-13.5 ppm

**Why it matters**: Bromine is the sanitizer that actively oxidizes contaminants and keeps water safe.

## Practical Target Guidance

Typical bromine targets used by many pool and spa operators are around 2-5 ppm, with spas often run slightly higher. Exact targets depend on local regulations, water temperature, and your treatment products.

Always follow your chemical manufacturer instructions and local pool guidance as the primary source of truth.

## What the Numbers Tell You

**Scenario 1: In target range** ✅
- Bromine: 3.2 ppm

**Analysis**: Typical healthy residual for many bromine systems.

**Scenario 2: Low residual** ⚠️
- Bromine: 1.1 ppm

**Analysis**: Sanitizer reserve may be too low. Consider dosing according to your treatment plan.

**Scenario 3: High residual** ⚠️
- Bromine: 8.0 ppm

**Analysis**: Residual may be above your preferred comfort target. Let it decay or adjust treatment according to your product guidance.

## Using Bromine Sensors in Home Assistant

### Dashboard Example

```yaml
type: entities
title: Pool Bromine Status
entities:
  - entity: sensor.backyard_pool_bromine
    name: Bromine
    icon: mdi:water-check
```

### Automation: Low Bromine Alert

```yaml
alias: "Pool: Low Bromine Alert"
description: Alert when bromine residual is too low
trigger:
  - platform: numeric_state
    entity_id: sensor.backyard_pool_bromine
    below: 2.0
    for:
      hours: 1
action:
  - service: notify.mobile_app
    data:
      title: "Pool Bromine Low"
      message: >
        Bromine is {{ states('sensor.backyard_pool_bromine') }} ppm.
        Check your bromine feeder/tablets and adjust dosing.
      data:
        priority: high
        icon: mdi:water-check
```

### Automation: High Bromine Alert

```yaml
alias: "Pool: High Bromine Alert"
description: Alert when bromine residual is above your comfort threshold
trigger:
  - platform: numeric_state
    entity_id: sensor.backyard_pool_bromine
    above: 6.0
    for:
      hours: 1
action:
  - service: notify.mobile_app
    data:
      title: "Pool Bromine High"
      message: >
        Bromine is {{ states('sensor.backyard_pool_bromine') }} ppm.
        Verify your target and reduce dosing if needed.
      data:
        priority: high
        icon: mdi:water-alert
```

## Troubleshooting

### Bromine Sensor Shows "Unavailable"

Possible causes:
1. No bromine measurement is present in the latest synced LabCom data.
2. Latest bromine value is outside the integration's valid range (0-13.5 ppm).
3. Temporary API/connectivity issue.

### Bromine Sensor Is Always Empty

Possible causes:
1. Your device/profile may not provide `PL Bromine` measurements.
2. Your setup may be running chlorine or active oxygen only.

## Related Documentation

- [README.md](README.md)
- [CHLORINE_CHEMISTRY.md](CHLORINE_CHEMISTRY.md)
- [ACTIVE_OXYGEN_CHEMISTRY.md](ACTIVE_OXYGEN_CHEMISTRY.md)
