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

        # Extract data from liveHeroView
        hero_view = data.get("liveHeroView", {})
        summary_cards = data.get("summaryCards", {})

        # Photovoltaic from summaryCards
        pv_data = summary_cards.get("photovoltaic", {})
        production = pv_data.get("production", {})
        result["photovoltaic"] = production.get("value", 0)

        # Grid data from liveHeroView
        grid_consumption = hero_view.get("gridConsumption", {})
        grid_feedin = hero_view.get("gridFeedIn", {})
        result["grid_consumption"] = grid_consumption.get("value", 0) if isinstance(grid_consumption, dict) else grid_consumption
        result["grid_feedin"] = grid_feedin.get("value", 0) if isinstance(grid_feedin, dict) else grid_feedin

        # Battery from summaryCards
        battery_data = summary_cards.get("battery", {})
        battery_power = battery_data.get("power", {})
        result["battery"] = battery_power.get("value", 0) if isinstance(battery_power, dict) else battery_power
        # State of charge (convert from 0-1 to 0-100%)
        soc = battery_data.get("stateOfCharge", hero_view.get("totalStateOfCharge", 0))
        result["battery_soc"] = round(soc * 100, 1) if soc <= 1 else soc

        # Heat pumps from summaryCards (aggregated)
        heat_pumps = summary_cards.get("heatPumps", [])
        total_hp_power = 0
        for hp in heat_pumps:
            hp_power = hp.get("power", {})
            total_hp_power += hp_power.get("value", 0) if isinstance(hp_power, dict) else hp_power
        result["heat_pump"] = total_hp_power

        # Also check aggregated heat pump power from liveHeroView
        hp_agg = hero_view.get("heatPumpsAggregated", {})
        hp_agg_power = hp_agg.get("power", {})
        if hp_agg_power:
            result["heat_pump"] = hp_agg_power.get("value", 0) if isinstance(hp_agg_power, dict) else hp_agg_power

        # EV Chargers / Wallbox from summaryCards (aggregated)
        ev_chargers = summary_cards.get("evChargers", [])
        total_ev_power = 0
        for ev in ev_chargers:
            ev_power = ev.get("power", {})
            total_ev_power += ev_power.get("value", 0) if isinstance(ev_power, dict) else ev_power
        result["wallbox"] = total_ev_power

        # Also check aggregated EV charger power from liveHeroView
        ev_agg = hero_view.get("evChargersAggregated", {})
        ev_agg_power = ev_agg.get("power", {})
        if ev_agg_power:
            result["wallbox"] = ev_agg_power.get("value", 0) if isinstance(ev_agg_power, dict) else ev_agg_power

        # Household from summaryCards
        household_data = summary_cards.get("household", {})
        household_power = household_data.get("power", {})
        result["household"] = household_power.get("value", 0) if isinstance(household_power, dict) else household_power

        # Total consumption from liveHeroView
        consumption = hero_view.get("consumption", {})
        result["total_consumption"] = consumption.get("value", 0) if isinstance(consumption, dict) else consumption

        # Self-sufficiency / Autarky rate from liveHeroView (convert from 0-1 to 0-100%)
        self_sufficiency = hero_view.get("selfSufficiency", 0)
        result["autarky_rate"] = round(self_sufficiency * 100, 1) if self_sufficiency <= 1 else self_sufficiency

        # Calculate self-consumption rate if we have production and feed-in
        pv_power = result.get("photovoltaic", 0)
        feedin = result.get("grid_feedin", 0)
        if pv_power > 0:
            self_consumed = pv_power - feedin
            result["self_consumption_rate"] = round((self_consumed / pv_power) * 100, 1)
        else:
            result["self_consumption_rate"] = 0

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
