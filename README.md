# Poollab Integration for Home Assistant

A custom Home Assistant integration for Poollab/LabCom Cloud API, allowing you to monitor your pool water quality parameters directly in Home Assistant.

## Features

- 🏊 **Multiple Pools Support** - Monitor all your pools/devices with a single integration
- 🏖️ Monitor pH levels
- 💧 Track chlorine levels (free, total, combined, unbound, and CYA-bound)
- 🟤 Monitor bromine residual
- 🫧 Monitor active oxygen (MPS) residual
- 🌡️ Monitor water temperature
- ⚗️ Alkalinity tracking
- 🛡️ Stabilizer (CYA) monitoring in chlorine mode
- 🧂 Salt level monitoring
- 🔄 Automatic updates every 5 minutes
- ✅ Data validation — out-of-range values are discarded automatically

## Chemistry Guides

- [CHLORINE_CHEMISTRY.md](CHLORINE_CHEMISTRY.md)
- [BROMINE_CHEMISTRY.md](BROMINE_CHEMISTRY.md)
- [ACTIVE_OXYGEN_CHEMISTRY.md](ACTIVE_OXYGEN_CHEMISTRY.md)

## Installation

### Via HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to Integrations
3. Click the three-dot menu → "Custom repositories"
4. Add `https://github.com/stefanh12/poollab` with category "Integration"
5. Search for "Poollab" and install
6. Restart Home Assistant

### Manual Installation

1. Download the latest release
2. Copy the `poollab` folder to `custom_components/` in your Home Assistant config directory
3. Restart Home Assistant

## Configuration

### Setup Steps

1. **Ensure that you have synced at least one measurement from your device to Labcom cloud**
   If you do not have any readings the setup will **fail**
2. Go to Settings → Devices & Services → Integrations
3. Click "Create Integration" and search for "Poollab"
4. **Get your personal API token:**
   - Visit: https://labcom.cloud
   - Your token is generated in https://labcom.cloud/pages/user-setting GraphiQL.
   - Generate a token and copy the token string
5. Paste your **personal token** into the Home Assistant config
6. The integration will automatically discover **all your devices/pools**
7. Configuration complete!

⚠️ **Important**: Each account has a **unique personal token**. Never share it!

### Multiple Pools/Devices

If your LabCom account has multiple pools or devices:

- **Automatic Discovery**: The integration automatically discovers ALL your pools when you add it
- **One Integration Entry**: You only need to enter your token once per account
- **Separate Device Entries**: Each pool appears as a separate device in Home Assistant
- **Named Devices**: Sensors are named with your pool name (e.g., "Backyard Pool pH", "Front Pool Temperature")
- **Manage Separately**: You can enable/disable sensors per pool in Home Assistant settings

## Supported Sensors

The integration creates the following sensors for each pool/device:

During setup, each device is assigned a sanitation method:

- **Chlorine**: exposes chlorine sensors, Stabilizer (CYA), and chlorine chemistry calculations
- **Bromine + Active Oxygen**: exposes bromine and active oxygen sensors instead of chlorine-family sensors and CYA

### Water Quality Measurements

| Sensor                    | Description                                                       | Unit     | Valid Range |
| ------------------------- | ----------------------------------------------------------------- | -------- | ----------- |
| **pH**                    | Current pool pH                                                   | pH       | 0 – 14      |
| **Chlorine**              | General chlorine level (legacy)                                   | ppm      | 0 – 10      |
| **Free Chlorine**         | Active chlorine available for sanitization                        | ppm      | 0 – 10      |
| **Total Chlorine**        | Free + combined chlorine                                          | ppm      | 0 – 10      |
| **Combined Chlorine**     | Chloramines — _calculated_ (Total − Free)                         | ppm      | 0 – 5       |
| **Unbound Chlorine**      | Free chlorine from ActiveChlorine model — _calculated_            | ppm      | 0 – 5       |
| **Chlorine Bound to CYA** | Chlorine sequestered by stabilizer — _calculated_                 | ppm      | 0 – 5       |
| **Temperature**           | Pool water temperature                                            | °C       | 0 – 50      |
| **Alkalinity**            | Total alkalinity                                                  | ppm      | 0 – 300     |
| **Stabilizer (CYA)**      | Cyanuric acid level _(chlorine mode only)_                        | ppm      | 0 – 200     |
| **Salt Level**            | Salt concentration                                                | ppm      | 0 – 3600    |
| **Bromine**               | Bromine concentration _(bromine + active oxygen mode only)_       | mg/l Br₂ | 0 – 9       |
| **Active Oxygen**         | Active Oxygen concentration _(bromine + active oxygen mode only)_ | mg/l O₂  | 0 – 20      |

### Diagnostic Sensors

| Sensor                | Description                                        |
| --------------------- | -------------------------------------------------- |
| **Measurement Count** | Total number of measurements stored for the device |
| **Last Measurement**  | Timestamp of the most recent measurement           |

### Sanitizer Comparison (Quick Reference)

| Sanitizer | Sensor | Integration Behavior | Typical Practical Target* | Documented Valid Range |
|-----------|--------|----------------------|---------------------------|------------------------|
| Chlorine | `sensor.pool_name_free_chlorine` (plus total/combined/unbound/bound variants) | Mix of direct values + calculated metrics (combined/unbound/bound) | Free chlorine: 1-3 ppm; Combined chlorine: < 0.5 ppm | 0-10 ppm (free/total), 0-5 ppm (combined), 0-10 ppm (unbound/bound) |
| Bromine | `sensor.pool_name_bromine` | Direct LabCom measurement (`PL Bromine`) | Often 2-5 ppm | 0-13.5 ppm |
| Active Oxygen | `sensor.pool_name_active_oxygen` | Direct LabCom measurement with multiple aliases (MPS and localized names) | Often 4-8 ppm | 0-30 ppm |

\* Practical targets depend on product instructions, local regulations, pool/spa type, and water conditions.

### Chlorine Chemistry

The integration provides detailed chlorine measurements in **chlorine mode**:

- **Free Chlorine (Active Chlorine)**: The chlorine available for sanitization. Ideal range: 1–3 ppm.
- **Total Chlorine**: All chlorine in the pool (free + combined).
- **Combined Chlorine**: Automatically calculated as (Total − Free). Represents chloramines and water quality. Should be < 0.5 ppm.
- **Unbound Chlorine / Bound to CYA**: Calculated by the LabCom `ActiveChlorine` API using your pH, temperature, chlorine, and CYA readings. Requires at least pH and free chlorine measurements to be available.

### Bromine Chemistry

- **Bromine**: Direct bromine residual measurement from LabCom (`PL Bromine`). No local formula is applied by the integration.
- Useful when your pool or spa uses bromine tablets/systems instead of chlorine.

See [BROMINE_CHEMISTRY.md](BROMINE_CHEMISTRY.md) for detailed bromine guidance and automation ideas.

### Active Oxygen Chemistry

- **Active Oxygen**: Direct residual measurement from LabCom. The integration supports multiple field name variants used by LabCom exports, including `PL Active Oxygen`, `PL Active Oxygen (MPS)`, `PL Active Oxygen MPS`, `PL MPS`, and German labels.
- Useful when your system uses MPS/active oxygen sanitizing products.

See [ACTIVE_OXYGEN_CHEMISTRY.md](ACTIVE_OXYGEN_CHEMISTRY.md) for interpretation guidance and automation examples.

For chlorine-specific deep guidance, see [CHLORINE_CHEMISTRY.md](CHLORINE_CHEMISTRY.md).

## Data Validation

The integration validates all measurement values from the API against the physical ranges listed in the table above. Values outside these ranges (e.g. a pH reading of −1 or 99) are treated as invalid and the sensor reports **unavailable** instead, with a warning logged. The same validation applies to inputs used for the `ActiveChlorine` calculation — if any required input is out of range, the calculation is skipped for that update cycle.

## API Requirements

This integration requires:

- Valid Labcom API token
- At least one Poollab device registered in your account
- Internet connectivity for API communication

## Troubleshooting

### Integration won't authenticate

- Verify your API token is correct
- Check the token at https://backend.labcom.cloud/graphiql
- Ensure your Labcom account is active
- Check your internet connection

### No devices found

- Log in to your Labcom account
- Verify you have a Poollab device registered
- Ensure the device is associated with your account

### Sensors showing "unavailable"

- Check network connectivity
- Verify API token is still valid
- Check Home Assistant logs for error messages
- If a specific sensor is unavailable, verify the measurement is synced to the Poollab backend
- A value that is out of the valid range listed above will also cause the sensor to report unavailable (a warning will appear in the logs)

## Support

For issues, feature requests, or questions, please visit:
https://github.com/stefanh12/poollab/issues

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
