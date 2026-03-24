"""Tests for the Oracle Cloud Infrastructure device tracker."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

from homeassistant.components.device_tracker import SourceType
from homeassistant.core import HomeAssistant

from custom_components.oraclecloud.device_tracker import OCIDeviceTracker


async def test_device_tracker(hass: HomeAssistant) -> None:
    """Test OCI device tracker."""
    mock_coordinator = MagicMock()
    mock_instance = MagicMock()
    mock_instance.display_name = "Test VM"
    mock_instance.shape = "VM.Standard.A1.Flex"
    mock_instance.lifecycle_state = "RUNNING"
    mock_instance.availability_domain = "AD1"
    mock_instance.fault_domain = "FAULT-1"
    mock_instance.time_created = datetime(2024, 1, 1, tzinfo=UTC)

    mock_instance.shape_config = MagicMock()
    mock_instance.shape_config.ocpus = 4
    mock_instance.shape_config.memory_in_gbs = 24
    mock_instance.shape_config.local_disks_total_size_in_gbs = 0.0
    mock_instance.shape_config.processor_description = "ARM"

    mock_instance.source_details = MagicMock()
    mock_instance.source_details.image_id = "image1"

    mock_coordinator.data = {
        "instances": {
            "inst1": {
                "instance": mock_instance,
                "public_ip": "1.2.3.4",
                "private_ip": "10.0.0.1",
                "os_name": "Ubuntu",
                "os_version": "22.04",
            }
        }
    }
    mock_coordinator.config = {
        "region": "us-ashburn-1",
        "tenancy": "tenancy1",
        "user": "user1",
    }
    mock_coordinator.username = "Test User"

    tracker = OCIDeviceTracker(mock_coordinator, "inst1")

    assert tracker.is_connected is True
    assert tracker.source_type == SourceType.ROUTER

    attrs = tracker.extra_state_attributes
    assert attrs["ocpus"] == 4
    assert attrs["memory_gb"] == 24
    assert attrs["public_ip"] == "1.2.3.4"
    assert attrs["private_ip"] == "10.0.0.1"
    assert attrs["os_name"] == "Ubuntu"
    assert attrs["os_version"] == "22.04"
    assert attrs["state"] == "RUNNING"

    # Test disconnected
    mock_instance.lifecycle_state = "STOPPED"
    assert tracker.is_connected is False
