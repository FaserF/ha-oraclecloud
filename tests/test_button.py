"""Tests for the Oracle Cloud Infrastructure buttons."""

from unittest.mock import MagicMock

from homeassistant.core import HomeAssistant

from custom_components.oraclecloud.button import BUTTONS, OCIButton


async def test_buttons(hass: HomeAssistant) -> None:
    """Test OCI buttons."""
    mock_coordinator = MagicMock()
    mock_instance = MagicMock()
    mock_instance.display_name = "Test VM"
    mock_instance.shape = "VM.Standard.A1.Flex"

    mock_coordinator.data = {
        "instances": {
            "inst1": {
                "instance": mock_instance,
            }
        }
    }
    mock_coordinator.config = {"region": "us-ashburn-1"}
    mock_coordinator.compute_client = MagicMock()

    # Test Start Button
    description = next(b for b in BUTTONS if b.key == "start")
    button = OCIButton(mock_coordinator, "inst1", description)
    button.hass = hass

    await button.async_press()
    mock_coordinator.compute_client.instance_action.assert_called_with("inst1", "start")

    # Test Reboot Button (Soft Reset)
    description = next(b for b in BUTTONS if b.key == "reboot")
    button = OCIButton(mock_coordinator, "inst1", description)
    button.hass = hass

    await button.async_press()
    mock_coordinator.compute_client.instance_action.assert_called_with(
        "inst1", "softreset"
    )

    # Test Reset Button (Hard Reset)
    description = next(b for b in BUTTONS if b.key == "reset")
    button = OCIButton(mock_coordinator, "inst1", description)
    button.hass = hass

    await button.async_press()
    mock_coordinator.compute_client.instance_action.assert_called_with("inst1", "reset")
