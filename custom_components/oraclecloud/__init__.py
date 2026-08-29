"""The Oracle Cloud Infrastructure integration."""

from __future__ import annotations

import importlib

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BUTTON,
    Platform.BINARY_SENSOR,
    Platform.DEVICE_TRACKER,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Oracle Cloud Infrastructure from a config entry."""
    await hass.async_add_import_executor_job(
        importlib.import_module, "custom_components.oraclecloud.coordinator"
    )
    from .coordinator import OCIUpdateCoordinator

    coordinator = OCIUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register update listener for configuration/options changes
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    # Pre-load diagnostics platform to avoid blocking import warning
    try:
        await hass.async_add_import_executor_job(
            importlib.import_module, "custom_components.oraclecloud.diagnostics"
        )
    except Exception:
        pass

    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
