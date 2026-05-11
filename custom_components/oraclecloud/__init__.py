"""The Oracle Cloud Infrastructure integration."""

from __future__ import annotations

import sys

import six  # type: ignore[import-untyped]

# Workaround for OCI SDK vendored urllib3/six compatibility on Python 3.14+
# This must be applied before any 'import oci' happens.
# Since this is in __init__.py, it will run whenever any submodule is imported.
sys.modules["oci._vendor.urllib3.packages.six"] = six
sys.modules["oci._vendor.urllib3.packages.six.moves"] = six.moves
if hasattr(six.moves, "http_client"):
    sys.modules["oci._vendor.urllib3.packages.six.moves.http_client"] = (
        six.moves.http_client
    )
if hasattr(six.moves, "urllib"):
    sys.modules["oci._vendor.urllib3.packages.six.moves.urllib"] = six.moves.urllib
    if hasattr(six.moves.urllib, "parse"):
        sys.modules["oci._vendor.urllib3.packages.six.moves.urllib.parse"] = (
            six.moves.urllib.parse
        )

from homeassistant.config_entries import ConfigEntry  # noqa: E402
from homeassistant.const import Platform  # noqa: E402
from homeassistant.core import HomeAssistant  # noqa: E402
from homeassistant.loader import async_get_integration  # noqa: E402

from .const import DOMAIN  # noqa: E402
from .coordinator import OCIUpdateCoordinator  # noqa: E402

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BUTTON,
    Platform.BINARY_SENSOR,
    Platform.DEVICE_TRACKER,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Oracle Cloud Infrastructure from a config entry."""
    coordinator = OCIUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Pre-load diagnostics platform to avoid blocking import warning
    try:
        integration = await async_get_integration(hass, DOMAIN)
        hass.async_create_task(integration.async_get_platform("diagnostics"))
    except Exception:
        pass

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
