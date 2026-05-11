"""Tests for the Oracle Cloud Infrastructure config flow."""

from typing import Any
from unittest.mock import MagicMock, patch

from homeassistant import config_entries, data_entry_flow
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigConfigEntry as MockConfigEntry

from custom_components.oraclecloud.const import DOMAIN

MOCK_DATA = {
    "tenancy": "ocid1.tenancy.oc1..abc",
    "user": "ocid1.user.oc1..def",
    "fingerprint": "12:34:56:78",
    "region": "us-ashburn-1",
    "key_content": "PRIVATE_KEY_CONTENT",
}


async def test_flow_user_init(hass: HomeAssistant) -> None:
    """Test the initial step of the config flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"


@patch("oci.identity.IdentityClient")
async def test_flow_user_validate_success(
    mock_identity: Any, hass: HomeAssistant
) -> None:
    """Test successful validation of OCI credentials."""
    mock_identity_instance = MagicMock()
    mock_identity.return_value = mock_identity_instance

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.oraclecloud.config_flow.validate_input",
        return_value={"title": "OCI (ocid1.te...)"},
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            MOCK_DATA,
        )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "OCI (ocid1.te...)"
    assert result["data"] == MOCK_DATA


async def test_options_flow(hass: HomeAssistant) -> None:
    """Test the options flow."""
    mock_entry = MagicMock()
    mock_entry.data = MOCK_DATA
    mock_entry.options = {}

    with patch(
        "custom_components.oraclecloud.config_flow.validate_input",
        return_value={"title": "OCI (ocid1.te...)"},
    ):
        # Use MockConfigEntry to test options flow
        entry = MockConfigEntry(
            version=1,
            domain=DOMAIN,
            title="OCI",
            data=MOCK_DATA,
            source=config_entries.SOURCE_USER,
            options={},
            entry_id="test",
        )
        # Manually add entry to hass
        entry.add_to_hass(hass)
        from custom_components.oraclecloud.config_flow import (
            OracleCloudOptionsFlowHandler,
        )

        handler = OracleCloudOptionsFlowHandler(entry)
        handler.hass = hass

        result = await handler.async_step_init()
        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "init"

        new_data = MOCK_DATA.copy()
        new_data["region"] = "eu-frankfurt-1"

        with patch.object(hass.config_entries, "async_update_entry") as mock_update:
            result = await handler.async_step_init(new_data)
            assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
            mock_update.assert_called_once_with(entry, data=new_data)
