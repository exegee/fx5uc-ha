# Mitsubishi FX5UC — Home Assistant Integration

Custom Home Assistant integration for Mitsubishi FX5UC PLC via Modbus TCP/IP.

## Features

- **Control outputs (Y)** — switch entities to turn PLC coils on/off
- **Read inputs (X)** — binary sensor entities showing PLC discrete input states
- **Custom naming** — assign aliases to each I/O point via Options Flow
- **Config Flow UI** — full configuration through Home Assistant UI (no YAML needed)
- **Auto-reconnect** — automatic reconnection on connection loss

## Requirements

- Mitsubishi FX5UC PLC with Modbus TCP enabled (configured in GX Works3)
- Network connectivity between Home Assistant and PLC
- PLC Modbus server configured with appropriate address mapping

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click the three dots menu → **Custom repositories**
3. Add this repository URL with category **Integration**
4. Search for "Mitsubishi FX5UC" and install
5. Restart Home Assistant

### Manual

1. Copy the `custom_components/fx5uc/` folder to your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **Mitsubishi FX5UC**
3. Enter:
   - **Host/IP** — IP address of your FX5UC
   - **Port** — Modbus TCP port (default: 502)
   - **Slave ID** — Modbus slave address (default: 1)
   - **Scan interval** — polling rate in seconds (default: 1)
4. Configure I/O address ranges:
   - **Input start address** and **count** (maps to Modbus discrete inputs)
   - **Output start address** and **count** (maps to Modbus coils)

## Naming / Aliases

After setup, go to the integration options to assign custom names:

1. Click **Configure** on the FX5UC integration card
2. Choose **Input Names (X)** or **Output Names (Y)**
3. Enter custom names for each I/O point
4. Names become the entity `friendly_name` in Home Assistant

## PLC Configuration (GX Works3)

In GX Works3, configure your FX5UC for Modbus TCP:

1. **Ethernet Port** — set IP address and subnet
2. **External Device Configuration** — add Modbus/TCP Connection Module
3. **Device Assignment**:
   - Map inputs (X) → Discrete Inputs (function code 02)
   - Map outputs (Y) → Coils (function codes 01/05)

> ⚠️ Ensure PLC network is isolated/firewalled. This integration writes directly to PLC coils.

## Entity Types

| Entity Type | Domain | PLC Device | Modbus Function | Access |
|---|---|---|---|---|
| Switch | `switch` | Y (outputs) | FC01/FC05 | Read/Write |
| Binary Sensor | `binary_sensor` | X (inputs) | FC02 | Read Only |

## Example Automations

```yaml
# Turn on output Y0 when input X0 is activated
automation:
  - alias: "X0 activates Y0"
    trigger:
      - platform: state
        entity_id: binary_sensor.fx5uc_x0
        to: "on"
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.fx5uc_y0
```

## License

MIT
