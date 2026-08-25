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
        import logging
        import subprocess
        import sys

        _LOGGER = logging.getLogger(__name__)

        # Targeted version of your custom fork
        REQUIRED_OCI_VERSION = "2.181.0.post3"
        needs_install = False
        try:
            import oci

            installed_ver = getattr(oci, "__version__", "")
            if installed_ver and (
                installed_ver == REQUIRED_OCI_VERSION
                or installed_ver.startswith("2.181")
            ):
                _LOGGER.debug(
                    "OCI SDK already installed (%s). Skipping git download.",
                    installed_ver,
                )
                return
            else:
                _LOGGER.info(
                    "OCI SDK version mismatch (installed: %s, required: %s). Updating...",
                    installed_ver,
                    REQUIRED_OCI_VERSION,
                )
                needs_install = True
        except ImportError:
            needs_install = True

        if needs_install:
            _LOGGER.info(
                "Installing/updating custom OCI Python SDK (%s)...",
                REQUIRED_OCI_VERSION,
            )
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "--upgrade",
                    "git+https://github.com/FaserF/oci-python-sdk.git@75b7f381f8885a967df461ebaf5396981e6a1e73#oci",
                ],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                _LOGGER.error(
                    "OCI SDK pip install failed (exit %d):\nSTDOUT: %s\nSTDERR: %s",
                    result.returncode,
                    result.stdout,
                    result.stderr,
                )
                raise RuntimeError(
                    f"pip install of oci-python-sdk failed: {result.stderr.strip()}"
                )
            # Purge cached oci modules so Python loads the freshly installed version
            for mod in list(sys.modules.keys()):
                if mod == "oci" or mod.startswith("oci."):
                    del sys.modules[mod]

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
