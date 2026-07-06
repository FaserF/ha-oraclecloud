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
    def check_and_install_oci() -> None:
        try:
            import oci
            if oci.__version__ == "2.181.0.post1":
                return
        except ImportError:
            pass

        import subprocess
        import sys
        subprocess.run([
            sys.executable, "-m", "pip", "install", "--quiet", "--upgrade",
            "git+https://github.com/FaserF/oci-python-sdk.git@28f956c93fd7d1718a5deaf49d25f900b2b280b4#oci"
        ], check=True)

    await hass.async_add_import_executor_job(check_and_install_oci)

    await hass.async_add_import_executor_job(
        importlib.import_module, "custom_components.oraclecloud.coordinator"
    )
    from .coordinator import OCIUpdateCoordinator

    coordinator = OCIUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Pre-load diagnostics platform to avoid blocking import warning
    try:
        await hass.async_add_import_executor_job(
            importlib.import_module, "custom_components.oraclecloud.diagnostics"
        )
    except Exception:
        pass

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
