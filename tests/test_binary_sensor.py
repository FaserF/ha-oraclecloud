"""Tests for the Oracle Cloud Infrastructure binary sensors."""

from unittest.mock import MagicMock

from homeassistant.core import HomeAssistant

from custom_components.oraclecloud.binary_sensor import (
    BINARY_SENSORS,
    OCIBinarySensor,
    OCIBudgetAlertBinarySensor,
)


async def test_binary_sensors(hass: HomeAssistant) -> None:
    """Test OCI binary sensors."""
    mock_coordinator = MagicMock()
    mock_instance = MagicMock()
    mock_instance.display_name = "Test VM"
    mock_instance.shape = "VM.Standard.A1.Flex"

    mock_coordinator.data = {
        "instances": {
            "inst1": {
                "instance": mock_instance,
                "memory_utilization": 50.0,
            }
        },
        "account": {
            "budget": {"actual_spend": 100.0, "amount": 90.0},
        },
    }
    mock_coordinator.config = {"region": "us-ashburn-1", "tenancy": "tenancy1"}

    # Test Agent Status (On)
    description = next(b for b in BINARY_SENSORS if b.key == "agent_status")
    sensor = OCIBinarySensor(mock_coordinator, "inst1", description)
    assert sensor.is_on is True

    # Test Agent Status (Off - no metric data)
    mock_coordinator.data["instances"]["inst1"]["memory_utilization"] = None
    assert sensor.is_on is False

    # Test Budget Alert (On)
    sensor = OCIBudgetAlertBinarySensor(mock_coordinator)
    assert sensor.is_on is True

    # Test Budget Alert (Off)
    mock_coordinator.data["account"]["budget"]["actual_spend"] = 50.0
    assert sensor.is_on is False
