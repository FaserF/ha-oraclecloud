"""Config flow for Oracle Cloud Infrastructure integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import voluptuous as vol

if TYPE_CHECKING:
    pass

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

try:
    from homeassistant.config_entries import ConfigFlowResult
except ImportError:
    from homeassistant.data_entry_flow import FlowResult as ConfigFlowResult

from .const import (
    CONF_COMPARTMENT,
    CONF_FINGERPRINT,
    CONF_KEY_CONTENT,
    CONF_REGION,
    CONF_TENANCY,
    CONF_USER,
    DOMAIN,
    LOGGER,
)


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_TENANCY): str,
        vol.Required(CONF_USER): str,
        vol.Required(CONF_FINGERPRINT): str,
        vol.Required(CONF_REGION): str,
        vol.Required(CONF_KEY_CONTENT): str,
        vol.Optional(CONF_COMPARTMENT): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    config = {
        "tenancy": data[CONF_TENANCY],
        "user": data[CONF_USER],
        "fingerprint": data[CONF_FINGERPRINT],
        "region": data[CONF_REGION],
        "key_content": data[CONF_KEY_CONTENT],
    }

    def _validate() -> str:
        try:
            import oci.identity  # pylint: disable=import-outside-toplevel

            identity = oci.identity.IdentityClient(config)
            response = identity.get_tenancy(config["tenancy"])
            return response.data.name
        except Exception as err:
            LOGGER.error("OCI validation failed: %s", err)
            raise CannotConnect from err

    title = await hass.async_add_executor_job(_validate)

    return {"title": title}


class OracleCloudConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Oracle Cloud Infrastructure."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)

                await self.async_set_unique_id(user_input[CONF_TENANCY])
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=info["title"],
                    data=user_input,
                )
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )
