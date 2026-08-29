"""Config flow for Oracle Cloud Infrastructure integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import voluptuous as vol

if TYPE_CHECKING:
    pass

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError

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
            import oci.exceptions
            import oci.identity  # pylint: disable=import-outside-toplevel

            identity = oci.identity.IdentityClient(config)
            response = identity.get_tenancy(config["tenancy"])
            return response.data.name
        except oci.exceptions.ServiceError as err:
            LOGGER.error("OCI validation service error: %s", err)
            if (
                err.status in (401, 403)
                or "NotAuthenticated" in str(err)
                or "NotAuthorized" in str(err)
            ):
                raise InvalidAuth from err
            raise CannotConnect from err
        except Exception as err:
            LOGGER.error("OCI validation failed: %s", err)
            raise CannotConnect from err

    title = await hass.async_add_executor_job(_validate)

    return {"title": title}


class OracleCloudConfigFlow(ConfigFlow, domain=DOMAIN):
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

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        """Handle initiation of reauthentication."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle re-authentication with new API credentials."""
        errors: dict[str, str] = {}
        reauth_entry = self._get_reauth_entry()

        if user_input is not None:
            # Merge user_input with tenancy and user if not in schema
            data = {
                CONF_TENANCY: reauth_entry.data[CONF_TENANCY],
                CONF_USER: reauth_entry.data[CONF_USER],
                CONF_FINGERPRINT: user_input[CONF_FINGERPRINT],
                CONF_REGION: user_input[CONF_REGION],
                CONF_KEY_CONTENT: user_input[CONF_KEY_CONTENT],
                CONF_COMPARTMENT: user_input.get(
                    CONF_COMPARTMENT, reauth_entry.data.get(CONF_COMPARTMENT, "")
                ),
            }
            try:
                await validate_input(self.hass, data)
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data_updates=data,
                )
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_FINGERPRINT,
                    default=reauth_entry.data.get(CONF_FINGERPRINT),
                ): str,
                vol.Required(
                    CONF_REGION,
                    default=reauth_entry.data.get(CONF_REGION),
                ): str,
                vol.Required(
                    CONF_KEY_CONTENT,
                    default=reauth_entry.data.get(CONF_KEY_CONTENT),
                ): str,
                vol.Optional(
                    CONF_COMPARTMENT,
                    default=reauth_entry.data.get(CONF_COMPARTMENT, ""),
                ): str,
            }
        )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=schema,
            errors=errors,
            description_placeholders={"user": reauth_entry.data.get(CONF_USER, "")},
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration of the integration."""
        errors: dict[str, str] = {}
        reconfigure_entry = self._get_reconfigure_entry()

        if user_input is not None:
            try:
                await validate_input(self.hass, user_input)
                return self.async_update_reload_and_abort(
                    reconfigure_entry,
                    data_updates=user_input,
                )
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        # Pre-populate schema with current config entry values
        data = reconfigure_entry.data
        schema = vol.Schema(
            {
                vol.Required(CONF_TENANCY, default=data.get(CONF_TENANCY)): str,
                vol.Required(CONF_USER, default=data.get(CONF_USER)): str,
                vol.Required(CONF_FINGERPRINT, default=data.get(CONF_FINGERPRINT)): str,
                vol.Required(CONF_REGION, default=data.get(CONF_REGION)): str,
                vol.Required(CONF_KEY_CONTENT, default=data.get(CONF_KEY_CONTENT)): str,
                vol.Optional(
                    CONF_COMPARTMENT, default=data.get(CONF_COMPARTMENT, "")
                ): str,
            }
        )

        return self.async_show_form(
            step_id="reconfigure", data_schema=schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> OracleCloudOptionsFlowHandler:
        """Get the options flow for this handler."""
        return OracleCloudOptionsFlowHandler(config_entry)


class OracleCloudOptionsFlowHandler(OptionsFlow):
    """Handle OCI options."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry
        self.handler = config_entry.entry_id

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                await validate_input(self.hass, user_input)
                # Update the entry data instead of options, as these are core config values
                self.hass.config_entries.async_update_entry(
                    self.config_entry, data=user_input
                )
                return self.async_create_entry(title="", data={})
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        # Pre-populate schema with current values
        data = self.config_entry.data
        schema = vol.Schema(
            {
                vol.Required(CONF_TENANCY, default=data.get(CONF_TENANCY)): str,
                vol.Required(CONF_USER, default=data.get(CONF_USER)): str,
                vol.Required(CONF_FINGERPRINT, default=data.get(CONF_FINGERPRINT)): str,
                vol.Required(CONF_REGION, default=data.get(CONF_REGION)): str,
                vol.Required(CONF_KEY_CONTENT, default=data.get(CONF_KEY_CONTENT)): str,
                vol.Optional(
                    CONF_COMPARTMENT, default=data.get(CONF_COMPARTMENT, "")
                ): str,
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
