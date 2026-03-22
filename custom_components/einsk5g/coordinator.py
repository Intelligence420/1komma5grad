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

            # Update history data periodically (every 15 minutes for more accurate daily totals)
            now = datetime.now()
            if (
                self._last_history_update is None
                or now - self._last_history_update > timedelta(minutes=15)
            ):
                try:
                    # Fetch today's data (use today's date for both from and to)
                    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
                    history = await self.api.get_history(
                        self.system_id,
                        start_date=today,
                        end_date=today,
                        resolution="15m",  # API requires 15m, hour, month, or year
                    )
                    self._history_data = self._parse_history_data(history)
                    self._last_history_update = now
                    _LOGGER.debug("History data updated: %s", self._history_data)
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
        # API returns negative values for charging, positive for discharging
        # Split into two sensors: battery_charge and battery_discharge (both positive)
        battery_data = summary_cards.get("battery", {})
        battery_power = battery_data.get("power", {})
        battery_value = battery_power.get("value", 0) if isinstance(battery_power, dict) else battery_power

        # battery_charge: positive when charging (API value < 0)
        # battery_discharge: positive when discharging (API value > 0)
        if battery_value < 0:
            result["battery_charge"] = abs(battery_value)
            result["battery_discharge"] = 0
        else:
            result["battery_charge"] = 0
            result["battery_discharge"] = battery_value

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

        # Extract energy values from the new API structure (in kWh)
        # energyProduced -> photovoltaic_energy
        if "energyProduced" in data:
            energy_produced = data["energyProduced"]
            if isinstance(energy_produced, dict):
                result["photovoltaic_energy"] = energy_produced.get("value", 0)
            else:
                result["photovoltaic_energy"] = energy_produced or 0

        # grid.supply -> grid_consumption_energy (energy from grid)
        # grid.feedIn -> grid_feedin_energy (energy to grid)
        grid = data.get("grid", {})
        if "supply" in grid:
            supply = grid["supply"]
            if isinstance(supply, dict):
                result["grid_consumption_energy"] = supply.get("value", 0)
            else:
                result["grid_consumption_energy"] = supply or 0

        if "feedIn" in grid:
            feed_in = grid["feedIn"]
            if isinstance(feed_in, dict):
                result["grid_feedin_energy"] = feed_in.get("value", 0)
            else:
                result["grid_feedin_energy"] = feed_in or 0

        # battery.charge -> battery_charge_energy
        # battery.discharge -> battery_discharge_energy
        battery = data.get("battery", {})
        if "charge" in battery:
            charge = battery["charge"]
            if isinstance(charge, dict):
                result["battery_charge_energy"] = charge.get("value", 0)
            else:
                result["battery_charge_energy"] = charge or 0

        if "discharge" in battery:
            discharge = battery["discharge"]
            if isinstance(discharge, dict):
                result["battery_discharge_energy"] = discharge.get("value", 0)
            else:
                result["battery_discharge_energy"] = discharge or 0

        # consumption.consumers for individual device energy
        consumption = data.get("consumption", {})
        consumers = consumption.get("consumers", {})

        # Heat pump energy
        if "heatPump" in consumers:
            hp = consumers["heatPump"]
            if isinstance(hp, dict):
                result["heat_pump_energy"] = hp.get("value", 0)
            else:
                result["heat_pump_energy"] = hp or 0

        # EV/Wallbox energy
        if "ev" in consumers:
            ev = consumers["ev"]
            if isinstance(ev, dict):
                result["wallbox_energy"] = ev.get("value", 0)
            else:
                result["wallbox_energy"] = ev or 0

        # Household energy
        if "household" in consumers:
            household = consumers["household"]
            if isinstance(household, dict):
                result["household_energy"] = household.get("value", 0)
            else:
                result["household_energy"] = household or 0

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
