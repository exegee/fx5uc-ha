"""Constants for the Mitsubishi FX5UC integration."""

DOMAIN = "fx5uc"

# Config keys
CONF_HOST = "host"
CONF_PORT = "port"
CONF_SLAVE = "slave"
CONF_SCAN_INTERVAL = "scan_interval"

# I/O config
CONF_INPUT_START = "input_start"
CONF_INPUT_COUNT = "input_count"
CONF_OUTPUT_START = "output_start"
CONF_OUTPUT_COUNT = "output_count"

# Options — aliases
CONF_IO_NAMES = "io_names"

# Defaults
DEFAULT_PORT = 502
DEFAULT_SLAVE = 255
DEFAULT_SCAN_INTERVAL = 1  # seconds
DEFAULT_INPUT_START = 0
DEFAULT_INPUT_COUNT = 32
DEFAULT_OUTPUT_START = 0
DEFAULT_OUTPUT_COUNT = 32

MAX_IO_COUNT = 64

# Platforms
PLATFORMS = ["switch", "binary_sensor"]
