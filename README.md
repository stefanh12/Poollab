# Poollab Integration for Home Assistant

A custom Home Assistant integration for Poollab/LabCom Cloud API, allowing you to monitor your pool water quality parameters directly in Home Assistant.

## Features

- � **Multiple Pools Support** - Monitor all your pools/devices with a single integration
- �🏖️ Monitor pH levels
- 💧 Track chlorine levels
- 🌡️ Monitor water temperature
- ⚗️ Alkalinity tracking
- 🛡️ Stabilizer (CYA) monitoring
- 🧂 Salt level monitoring
- ☁️ Cloud-based GraphQL API integration
- 🔄 Automatic updates every 5 minutes

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

1. Go to Settings → Devices & Services → Integrations
2. Click "Create Integration" and search for "Poollab"
3. **Get your personal API token:**
   - Visit: https://backend.labcom.cloud/graphiql
   - Your token is in the URL: `?token=YOUR_PERSONAL_TOKEN`
   - Copy the entire token string
4. Paste your **personal token** into the Home Assistant config
5. The integration will automatically discover **all your devices/pools**
6. Configuration complete!

⚠️ **Important**: Each account has a **unique personal token**. Never share it!

### Getting Your Personal API Token

Each LabCom account has a **unique personal token** that grants access to your specific device(s).

1. **Visit the token interface:**
   - Go to: https://backend.labcom.cloud/graphiql
   - You'll be automatically redirected with your personal token in the URL

2. **Find your token in the URL:**
   - Look at your browser's address bar
   - Your token is the long string after `?token=`
   - Example: `https://backend.labcom.cloud/graphiql?token=TOKEN...`

3. **Copy your personal token:**
   - Highlight the entire token string (the long alphanumeric sequence)
   - Copy it to clipboard
   - Don't include the `?token=` part, just the token itself

4. **Use in Home Assistant:**
   - When adding the Poollab integration, paste your personal token
   - Home Assistant will store it securely
   - **Never share your personal token** - it's like a password for your account

⚠️ **Security**: Your token is unique and personal to your account. Treat it like a password and never share it publicly.

### Multiple Pools/Devices

If your LabCom account has multiple pools or devices:
- **Automatic Discovery**: The integration automatically discovers ALL your pools when you add it
- **One Integration Entry**: You only need to enter your token once per account
- **Separate Device Entries**: Each pool appears as a separate device in Home Assistant
- **Named Devices**: Sensors are named with your pool name (e.g., "Backyard Pool pH", "Front Pool Temperature")
- **Manage Separately**: You can enable/disable sensors per pool in Home Assistant settings

## Supported Sensors

The integration creates the following sensors:

- **pH Level** - Current pool pH (0-14)
- **Chlorine Level** - Current chlorine concentration (ppm)
- **Free Chlorine** - Active chlorine available for sanitization (ppm)
- **Total Chlorine** - Total chlorine in pool (free + combined) (ppm)
- **Combined Chlorine** - Chlorine bound to contaminants/chloramines (ppm) - *calculated*
- **Water Temperature** - Current pool temperature (°C)
- **Alkalinity** - Current alkalinity level (ppm)
- **Stabilizer (CYA)** - Current stabilizer level (ppm)
- **Salt Level** - Current salt concentration (ppm)

### Chlorine Chemistry

The integration provides detailed chlorine measurements:

- **Free Chlorine (Active Chlorine)**: The chlorine available for sanitization. Ideal range: 1-3 ppm
- **Total Chlorine**: All chlorine in the pool (free + combined)
- **Combined Chlorine**: Automatically calculated as (Total - Free). This represents chloramines and indicates water quality. Should be < 0.5 ppm

**Note**: If your device provides `freeChlorine` and `totalChlorine`, the integration automatically calculates and displays combined chlorine.

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

## Support

For issues, feature requests, or questions, please visit:
https://github.com/yourusername/ha-poollab/issues

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
