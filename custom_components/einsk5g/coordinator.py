"""Data update coordinator for 1KOMMA5GRAD."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import EinsK5GApi, EinsK5GApiError
from .const import DOMAIN, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class EinsK5GDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching 1KOMMA5GRAD data."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: EinsK5GApi,
        system_id: str,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.api = api
        self.system_id = system_id
        self._last_history_update: datetime | None = None
        self._history_data: dict[str, Any] = {}

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the API."""
        try:
            # Get live overview data
            live_data = await self.api.get_live_overview(self.system_id)

            # Parse the live data into sensor values
            data = self._parse_live_data(live_data)

            # Update history data periodically (every hour)
            now = datetime.now()
            if (
                self._last_history_update is None
                or now - self._last_history_update > timedelta(hours=1)
            ):
                try:
                    history = await self.api.get_history(
                        self.system_id,
                        start_date=now - timedelta(days=1),
                        end_date=now,
                        resolution="day",
                    )
                    self._history_data = self._parse_history_data(history)
                    self._last_history_update = now
                except EinsK5GApiError as err:
                    _LOGGER.warning("Failed to fetch history data: %s", err)

            # Merge history data with live data
            data.update(self._history_data)

            return data

        except EinsK5GApiError as err:
            raise UpdateFailed(f"Error fetching data: {err}") from err

    def _parse_live_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Parse live overview data into sensor values."""
        result: dict[str, Any] = {}

        # The API response structure may vary, handle common patterns
        # Power values (in Watts)
        if "photovoltaic" in data:
            pv = data["photovoltaic"]
            result["photovoltaic"] = pv.get("power", pv.get("currentPower", 0))

        if "grid" in data:
            grid = data["grid"]
            grid_power = grid.get("power", grid.get("currentPower", 0))
            if grid_power >= 0:
                result["grid_consumption"] = grid_power
                result["grid_feedin"] = 0
            else:
                result["grid_consumption"] = 0
                result["grid_feedin"] = abs(grid_power)

        if "battery" in data:
            battery = data["battery"]
            result["battery"] = battery.get("power", battery.get("currentPower", 0))
            result["battery_soc"] = battery.get("soc", battery.get("stateOfCharge", 0))

        if "heatPump" in data:
            hp = data["heatPump"]
            result["heat_pump"] = hp.get("power", hp.get("currentPower", 0))

        if "wallbox" in data or "evCharger" in data:
            wb = data.get("wallbox", data.get("evCharger", {}))
            result["wallbox"] = wb.get("power", wb.get("currentPower", 0))

        if "household" in data:
            hh = data["household"]
            result["household"] = hh.get("power", hh.get("currentPower", 0))

        if "consumption" in data:
            cons = data["consumption"]
            result["total_consumption"] = cons.get("power", cons.get("total", 0))

        # Calculate rates if not provided
        if "selfConsumptionRate" in data:
            result["self_consumption_rate"] = data["selfConsumptionRate"]
        elif "selfConsumption" in data:
            result["self_consumption_rate"] = data["selfConsumption"].get("rate", 0)

        if "autarkyRate" in data:
            result["autarky_rate"] = data["autarkyRate"]
        elif "autarky" in data:
            result["autarky_rate"] = data["autarky"].get("rate", 0)

        # Handle flat structure responses
        for key in [
            "pvPower",
            "gridPower",
            "batteryPower",
            "batterySoc",
            "heatPumpPower",
            "wallboxPower",
            "householdPower",
        ]:
            if key in data:
                mapped_key = {
                    "pvPower": "photovoltaic",
                    "gridPower": "grid_consumption",
                    "batteryPower": "battery",
                    "batterySoc": "battery_soc",
                    "heatPumpPower": "heat_pump",
                    "wallboxPower": "wallbox",
                    "householdPower": "household",
                }.get(key)
                if mapped_key and mapped_key not in result:
                    result[mapped_key] = data[key]

        return result

    def _parse_history_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Parse historical data into energy values."""
        result: dict[str, Any] = {}

        # Extract cumulative energy values (in kWh)
        if "totals" in data:
            totals = data["totals"]

            if "photovoltaic" in totals:
                result["photovoltaic_energy"] = totals["photovoltaic"].get("energy", 0)

            if "gridConsumption" in totals:
                result["grid_consumption_energy"] = totals["gridConsumption"].get("energy", 0)

            if "gridFeedIn" in totals:
                result["grid_feedin_energy"] = totals["gridFeedIn"].get("energy", 0)

            if "batteryCharge" in totals:
                result["battery_charge_energy"] = totals["batteryCharge"].get("energy", 0)

            if "batteryDischarge" in totals:
                result["battery_discharge_energy"] = totals["batteryDischarge"].get("energy", 0)

            if "heatPump" in totals:
                result["heat_pump_energy"] = totals["heatPump"].get("energy", 0)

            if "wallbox" in totals:
                result["wallbox_energy"] = totals["wallbox"].get("energy", 0)

            if "household" in totals:
                result["household_energy"] = totals["household"].get("energy", 0)

        return result


class EinsK5GHistoryCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for fetching historical data."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: EinsK5GApi,
        system_id: str,
    ) -> None:
        """Initialize the history coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_history",
            update_interval=timedelta(hours=1),
        )
        self.api = api
        self.system_id = system_id

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch historical data from the API."""
        try:
            now = datetime.now()

            # Fetch last 30 days of data
            history = await self.api.get_history(
                self.system_id,
                start_date=now - timedelta(days=30),
                end_date=now,
                resolution="day",
            )

            return self._parse_history(history)

        except EinsK5GApiError as err:
            raise UpdateFailed(f"Error fetching history: {err}") from err

    def _parse_history(self, data: dict[str, Any]) -> dict[str, Any]:
        """Parse historical data."""
        result: dict[str, Any] = {
            "entries": [],
            "totals": {},
        }

        if "data" in data:
            result["entries"] = data["data"]

        if "totals" in data:
            result["totals"] = data["totals"]

        return result
