"""Diagnostics support for Oracle Cloud Infrastructure."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data as redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_FINGERPRINT, CONF_KEY_CONTENT, CONF_TENANCY, CONF_USER, DOMAIN
from .coordinator import OCIUpdateCoordinator

TO_REDACT = {
    CONF_USER,
    CONF_TENANCY,
    CONF_FINGERPRINT,
    CONF_KEY_CONTENT,
    "id",
    "compartment_id",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: OCIUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    diag_data = {
        "entry": redact_data(entry.as_dict(), TO_REDACT),
        "data": {
            "instances": {
                inst_id: redact_data(inst_data, TO_REDACT)
                for inst_id, inst_data in coordinator.data.get("instances", {}).items()
            },
            "account": redact_data(coordinator.data.get("account", {}), TO_REDACT),
        },
    }

    return diag_data
