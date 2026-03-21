"""Sensor platform for 1KOMMA5GRAD."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, ENERGY_SENSOR_TYPES, MANUFACTURER, SENSOR_TYPES
from .coordinator import EinsK5GDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the 1KOMMA5GRAD sensors."""
    coordinator: EinsK5GDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]
    system_id = hass.data[DOMAIN][entry.entry_id]["system_id"]
    system_info = hass.data[DOMAIN][entry.entry_id].get("system_info", {})

    entities: list[SensorEntity] = []

    # Create power sensors
    for sensor_type, config in SENSOR_TYPES.items():
        entities.append(
            EinsK5GPowerSensor(
                coordinator=coordinator,
                sensor_type=sensor_type,
                config=config,
                system_id=system_id,
                system_info=system_info,
            )
        )

    # Create energy sensors
    for sensor_type, config in ENERGY_SENSOR_TYPES.items():
        entities.append(
            EinsK5GEnergySensor(
                coordinator=coordinator,
                sensor_type=sensor_type,
                config=config,
                system_id=system_id,
                system_info=system_info,
            )
        )

    async_add_entities(entities)


class EinsK5GSensorBase(CoordinatorEntity[EinsK5GDataUpdateCoordinator], SensorEntity):
    """Base class for 1KOMMA5GRAD sensors."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EinsK5GDataUpdateCoordinator,
        sensor_type: str,
        config: dict[str, Any],
        system_id: str,
        system_info: dict[str, Any],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._sensor_type = sensor_type
        self._config = config
        self._system_id = system_id
        self._system_info = system_info

        self._attr_unique_id = f"{system_id}_{sensor_type}"
        self._attr_name = config["name"]
        self._attr_icon = config["icon"]
        self._attr_native_unit_of_measurement = config["unit"]

        if config["device_class"]:
            self._attr_device_class = SensorDeviceClass(config["device_class"])

        if config["state_class"]:
            self._attr_state_class = SensorStateClass(config["state_class"])

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._system_id)},
            name=self._system_info.get("name", "1KOMMA5GRAD System"),
            manufacturer=MANUFACTURER,
            model=self._system_info.get("model", "Heartbeat"),
            sw_version=self._system_info.get("firmwareVersion"),
        )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success


class EinsK5GPowerSensor(EinsK5GSensorBase):
    """Power sensor for 1KOMMA5GRAD."""

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        if self.coordinator.data is None:
            return None

        value = self.coordinator.data.get(self._sensor_type)
        if value is None:
            return None

        # Round to 1 decimal place
        return round(float(value), 1)

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return UnitOfPower.WATT


class EinsK5GEnergySensor(EinsK5GSensorBase):
    """Energy sensor for 1KOMMA5GRAD (historical data)."""

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        if self.coordinator.data is None:
            return None

        value = self.coordinator.data.get(self._sensor_type)
        if value is None:
            return None

        # Energy values should be in kWh, round to 2 decimal places
        return round(float(value), 2)

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return UnitOfEnergy.KILO_WATT_HOUR
