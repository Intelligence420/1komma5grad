"""Constants for the 1KOMMA5GRAD integration."""
from datetime import timedelta

DOMAIN = "einsk5g"
MANUFACTURER = "1KOMMA5GRAD"

# API endpoints
AUTH_URL = "https://auth.1komma5grad.com"
HEARTBEAT_URL = "https://heartbeat.1komma5grad.com"
CUSTOMER_IDENTITY_URL = "https://customer-identity.1komma5grad.com"

# Auth0 client configuration
CLIENT_ID = "zJTm6GFGM5zHcmpl07xTsi6MP0TwRAw6"
AUTH0_CLIENT = "eyJuYW1lIjoiYXV0aDAtc3BhLWpzIiwidmVyc2lvbiI6IjIuMC44In0="

# Update interval
SCAN_INTERVAL = timedelta(seconds=10)
HISTORY_SCAN_INTERVAL = timedelta(hours=1)

# Config keys
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_SYSTEM_ID = "system_id"

# Sensor types
SENSOR_TYPES = {
    "photovoltaic": {
        "name": "Photovoltaik",
        "icon": "mdi:solar-power",
        "unit": "W",
        "device_class": "power",
        "state_class": "measurement",
    },
    "grid_consumption": {
        "name": "Netzbezug",
        "icon": "mdi:transmission-tower-import",
        "unit": "W",
        "device_class": "power",
        "state_class": "measurement",
    },
    "grid_feedin": {
        "name": "Netzeinspeisung",
        "icon": "mdi:transmission-tower-export",
        "unit": "W",
        "device_class": "power",
        "state_class": "measurement",
    },
    "battery": {
        "name": "Batterie",
        "icon": "mdi:battery",
        "unit": "W",
        "device_class": "power",
        "state_class": "measurement",
    },
    "battery_soc": {
        "name": "Batterie Ladestand",
        "icon": "mdi:battery-charging",
        "unit": "%",
        "device_class": "battery",
        "state_class": "measurement",
    },
    "heat_pump": {
        "name": "Waermepumpe",
        "icon": "mdi:heat-pump",
        "unit": "W",
        "device_class": "power",
        "state_class": "measurement",
    },
    "wallbox": {
        "name": "Wallbox",
        "icon": "mdi:ev-station",
        "unit": "W",
        "device_class": "power",
        "state_class": "measurement",
    },
    "household": {
        "name": "Haushalt",
        "icon": "mdi:home-lightning-bolt",
        "unit": "W",
        "device_class": "power",
        "state_class": "measurement",
    },
    "total_consumption": {
        "name": "Gesamtverbrauch",
        "icon": "mdi:lightning-bolt",
        "unit": "W",
        "device_class": "power",
        "state_class": "measurement",
    },
    "self_consumption_rate": {
        "name": "Eigenverbrauchsquote",
        "icon": "mdi:percent",
        "unit": "%",
        "device_class": None,
        "state_class": "measurement",
    },
    "autarky_rate": {
        "name": "Autarkiegrad",
        "icon": "mdi:percent",
        "unit": "%",
        "device_class": None,
        "state_class": "measurement",
    },
}

# Energy sensor types (for historical data - kWh)
# Using state_class "total" since these are daily energy values
ENERGY_SENSOR_TYPES = {
    "photovoltaic_energy": {
        "name": "Photovoltaik Energie Heute",
        "icon": "mdi:solar-power",
        "unit": "kWh",
        "device_class": "energy",
        "state_class": "total",
    },
    "grid_consumption_energy": {
        "name": "Netzbezug Energie Heute",
        "icon": "mdi:transmission-tower-import",
        "unit": "kWh",
        "device_class": "energy",
        "state_class": "total",
    },
    "grid_feedin_energy": {
        "name": "Netzeinspeisung Energie Heute",
        "icon": "mdi:transmission-tower-export",
        "unit": "kWh",
        "device_class": "energy",
        "state_class": "total",
    },
    "battery_charge_energy": {
        "name": "Batterie Ladung Energie Heute",
        "icon": "mdi:battery-charging",
        "unit": "kWh",
        "device_class": "energy",
        "state_class": "total",
    },
    "battery_discharge_energy": {
        "name": "Batterie Entladung Energie Heute",
        "icon": "mdi:battery-minus",
        "unit": "kWh",
        "device_class": "energy",
        "state_class": "total",
    },
    "heat_pump_energy": {
        "name": "Waermepumpe Energie Heute",
        "icon": "mdi:heat-pump",
        "unit": "kWh",
        "device_class": "energy",
        "state_class": "total",
    },
    "wallbox_energy": {
        "name": "Wallbox Energie Heute",
        "icon": "mdi:ev-station",
        "unit": "kWh",
        "device_class": "energy",
        "state_class": "total",
    },
    "household_energy": {
        "name": "Haushalt Energie Heute",
        "icon": "mdi:home-lightning-bolt",
        "unit": "kWh",
        "device_class": "energy",
        "state_class": "total",
    },
}
