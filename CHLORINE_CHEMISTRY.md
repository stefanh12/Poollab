# Pool Chlorine Chemistry - Understanding Your Chlorine Sensors

## Overview

The Poollab integration provides detailed chlorine measurements to help you maintain optimal pool water quality. Understanding the different types of chlorine is essential for proper pool chemistry management.

## Chlorine Sensor Types

### 1. Free Chlorine (Active Chlorine) 🟢

**What it is**: The amount of chlorine actively available to sanitize your pool and kill bacteria, viruses, and algae.

**Sensor**: `sensor.pool_name_free_chlorine`

**Ideal Range**: 1-3 ppm (parts per million)

**Attributes**:
- `also_known_as`: "Active Chlorine"
- `description`: "Active chlorine available for sanitization"
- `ideal_range`: "1-3 ppm"

**Why it matters**: This is the most important chlorine measurement. It tells you how much sanitizing power your pool has right now.

### 2. Total Chlorine 🔵

**What it is**: The total amount of all chlorine in the pool, including both free (active) and combined (used) chlorine.

**Sensor**: `sensor.pool_name_total_chlorine`

**Formula**: Total Chlorine = Free Chlorine + Combined Chlorine

**Attributes**:
- `description`: "Total chlorine (free + combined)"
- `calculation`: "Total = Free + Combined"

**Why it matters**: Helps you understand the complete chlorine picture in your pool.

### 3. Combined Chlorine (Chloramines) 🔴

**What it is**: Chlorine that has already reacted with contaminants (sweat, oils, urine, organic matter). Also known as chloramines. This is what causes the "chlorine smell" and eye irritation.

**Sensor**: `sensor.pool_name_combined_chlorine`

**Formula**: Combined Chlorine = Total Chlorine - Free Chlorine

**Calculated**: ✅ Automatically calculated by the integration

**Ideal Range**: < 0.5 ppm (should be as low as possible)

**Attributes**:
- `description`: "Chlorine bound to contaminants (chloramines)"
- `calculation`: "Combined = Total - Free"
- `ideal_range`: "< 0.5 ppm"
- `warning`: "High combined chlorine indicates poor water quality"
- `free_chlorine`: The free chlorine value used in calculation
- `total_chlorine`: The total chlorine value used in calculation

**Why it matters**: High combined chlorine means:
- Poor water quality
- Pool needs shocking
- Irritation risk for swimmers
- "Chlorine smell" problems

### 4. Legacy Chlorine Sensor

**Sensor**: `sensor.pool_name_chlorine`

This sensor is maintained for backward compatibility and may represent either free chlorine or a general chlorine measurement from the device.

## Pool Chemistry Guidelines

### Ideal Chlorine Levels

| Measurement | Target Range | Action Needed If Outside Range |
|-------------|--------------|-------------------------------|
| Free Chlorine | 1-3 ppm | Below: Add chlorine<br>Above: Dilute or wait |
| Combined Chlorine | < 0.5 ppm | Above: Shock pool to break chloramines |
| Total Chlorine | 1-3.5 ppm | Should be close to free chlorine |

### What the Numbers Tell You

**Scenario 1: Healthy Pool** ✅
- Free Chlorine: 2.5 ppm
- Total Chlorine: 2.6 ppm
- Combined Chlorine: 0.1 ppm (calculated)

**Analysis**: Excellent! Very little combined chlorine, most is free and active.

**Scenario 2: Needs Shocking** ⚠️
- Free Chlorine: 1.5 ppm
- Total Chlorine: 3.0 ppm
- Combined Chlorine: 1.5 ppm (calculated)

**Analysis**: High combined chlorine! Pool needs shocking to break down chloramines.

**Scenario 3: Low Chlorine** 🔴
- Free Chlorine: 0.5 ppm
- Total Chlorine: 1.2 ppm
- Combined Chlorine: 0.7 ppm (calculated)

**Analysis**: Both free and combined chlorine are problems. Add chlorine and consider shocking.

## Using Chlorine Sensors in Home Assistant

### Dashboard Example

```yaml
type: entities
title: Pool Chlorine Status
entities:
  - entity: sensor.backyard_pool_free_chlorine
    name: Active Chlorine
    icon: mdi:water-check
  - entity: sensor.backyard_pool_total_chlorine
    name: Total Chlorine
  - entity: sensor.backyard_pool_combined_chlorine
    name: Combined Chlorine (Chloramines)
    icon: mdi:water-alert
```

### Automation: Alert When Shocking Needed

```yaml
alias: "Pool: Shock Needed (High Combined Chlorine)"
description: Alert when combined chlorine is too high
trigger:
  - platform: numeric_state
    entity_id: sensor.backyard_pool_combined_chlorine
    above: 0.5
    for:
      hours: 1
action:
  - service: notify.mobile_app
    data:
      title: "Pool Needs Shocking"
      message: >
        Combined chlorine is {{ states('sensor.backyard_pool_combined_chlorine') }} ppm.
        This indicates chloramines buildup. Time to shock the pool!
      data:
        priority: high
        icon: mdi:water-alert
```

### Automation: Low Active Chlorine Alert

```yaml
alias: "Pool: Low Active Chlorine"
description: Alert when sanitizing chlorine is too low
trigger:
  - platform: numeric_state
    entity_id: sensor.backyard_pool_free_chlorine
    below: 1.0
condition:
  - condition: time
    after: "08:00:00"
    before: "22:00:00"
action:
  - service: notify.mobile_app
    data:
      title: "Pool Chlorine Low"
      message: >
        Free chlorine is {{ states('sensor.backyard_pool_free_chlorine') }} ppm.
        Add chlorine to reach 1-3 ppm target range.
      data:
        priority: high
        icon: mdi:water-check
```

### Template Sensor: Chlorine Health Status

```yaml
template:
  - sensor:
      - name: "Pool Chlorine Status"
        state: >
          {% set free = states('sensor.backyard_pool_free_chlorine') | float(0) %}
          {% set combined = states('sensor.backyard_pool_combined_chlorine') | float(0) %}
          
          {% if free < 1.0 %}
            Critically Low
          {% elif free < 2.0 and combined > 0.5 %}
            Needs Attention
          {% elif combined > 0.5 %}
            Needs Shocking
          {% elif free >= 1.0 and free <= 3.0 and combined <= 0.5 %}
            Healthy
          {% elif free > 3.0 %}
            Too High
          {% else %}
            Unknown
          {% endif %}
        icon: >
          {% set free = states('sensor.backyard_pool_free_chlorine') | float(0) %}
          {% set combined = states('sensor.backyard_pool_combined_chlorine') | float(0) %}
          
          {% if free < 1.0 or combined > 0.5 %}
            mdi:water-alert
          {% else %}
            mdi:water-check
          {% endif %}
```

## How the Integration Calculates Combined Chlorine

The integration automatically calculates combined chlorine using this logic:

```python
def calculate_combined_chlorine(total_chlorine, free_chlorine):
    """Calculate combined chlorine."""
    if total_chlorine is not None and free_chlorine is not None:
        combined = total_chlorine - free_chlorine
        # Combined chlorine cannot be negative
        return max(0.0, combined)
    return None
```

**Requirements**:
- Your Poollab device must provide both `freeChlorine` and `totalChlorine` values
- If either value is missing, combined chlorine sensor will show "unavailable"
- The calculation is performed locally, no API call needed

## Troubleshooting

### Combined Chlorine Shows "Unavailable"

**Cause**: Your device doesn't provide both free and total chlorine measurements

**Solution**: 
1. Check if your Poollab device model supports these measurements
2. Verify the device has recent readings
3. Some devices only provide a single "chlorine" measurement

### All Chlorine Sensors Show Same Value

**Cause**: Device may only provide one chlorine measurement type

**Solution**: This is normal for some Poollab models. The integration creates all sensor entities, but only those with available data will show values.

### Combined Chlorine is Negative

**Solution**: The integration automatically prevents negative values. If you see 0.0 when free chlorine equals total chlorine, this is correct and indicates no combined chlorine (excellent water quality).

## Technical Details

### API Fields

The integration queries these chlorine fields from the LabCom API:

```graphql
query GetDeviceReadings($deviceId: ID!) {
  device(id: $deviceId) {
    lastReading {
      chlorine          # Legacy/general chlorine
      freeChlorine      # Active chlorine
      totalChlorine     # Total chlorine
    }
  }
}
```

### Sensor Entity IDs

For a pool named "Backyard Pool":
- `sensor.backyard_pool_chlorine` (legacy)
- `sensor.backyard_pool_free_chlorine` 
- `sensor.backyard_pool_total_chlorine`
- `sensor.backyard_pool_combined_chlorine` (calculated)

## FAQ

### Q: What's the difference between "Chlorine" and "Free Chlorine" sensors?

**A**: "Chlorine" is a legacy sensor maintained for backward compatibility. "Free Chlorine" specifically represents active, sanitizing chlorine. Use Free Chlorine for accurate pool management.

### Q: Why is my combined chlorine always 0?

**A**: This is excellent! It means all your chlorine is free/active. No chloramines present.

### Q: Should combined chlorine ever be higher than free chlorine?

**A**: No! If it is, your pool needs immediate shocking. This indicates severe chloramine buildup.

### Q: Can I hide sensors I don't need?

**A**: Yes! Go to Settings → Devices & Services → Devices → [Your Pool] → Click on the sensor → Disable entity.

### Q: Which chlorine sensor should I use for automations?

**A**: Use **Free Chlorine** for normal monitoring and **Combined Chlorine** to trigger shocking alerts.

## References

- [CDC Pool Chlorine Guidelines](https://www.cdc.gov/healthywater/swimming/residential/disinfection-testing.html)
- Pool & Hot Tub Alliance Standards
- WHO Guidelines for Pool Water Quality

---

**Note**: Always follow manufacturer recommendations for your specific pool type and size. This guide provides general information for educational purposes.
