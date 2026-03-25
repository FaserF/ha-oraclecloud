"""Tests for the Oracle Cloud Infrastructure sensors."""

from __future__ import annotations

from unittest.mock import MagicMock

from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant

from custom_components.oraclecloud.sensor import (
    ACCOUNT_SENSORS,
    SENSORS,
    VOLUME_SENSORS,
    OCIAccountSensor,
    OCISensor,
    OCIVolumeSensor,
)


async def test_sensors(hass: HomeAssistant) -> None:
    """Test OCI sensors."""
    mock_coordinator = MagicMock()
    mock_instance = MagicMock()
    mock_instance.display_name = "Test VM"
    mock_instance.shape = "VM.Standard.A1.Flex"
    mock_instance.lifecycle_state = "RUNNING"
    mock_instance.source_details = MagicMock()
    mock_instance.source_details.image_id = "image1"

    mock_coordinator.data = {
        "instances": {
            "inst1": {
                "instance": mock_instance,
                "cpu_utilization": 12.34,
                "memory_utilization": 50.0,
                "disk_utilization": 20.0,
                "network_bytes_in": 1024,
                "network_bytes_out": 2048,
                "public_ip": "1.1.1.1",
                "os_name": "Ubuntu",
                "os_version": "22.04",
            }
        },
        "account": {
            "budget": {"actual_spend": 10.5, "forecasted_spend": 50.0},
            "announcements": 1,
            "used_arm_ocpu": 4.0,
            "used_arm_mem": 24.0,
            "volumes": [
                {
                    "id": "vol1",
                    "display_name": "Boot Volume",
                    "size_in_gbs": 50,
                    "lifecycle_state": "AVAILABLE",
                    "volume_throttled_ios": 0.0,
                }
            ],
            "buckets": [
                {
                    "name": "my-bucket",
                    "size": 1024,
                    "count": 5,
                }
            ],
        },
    }
    mock_coordinator.config = {
        "region": "us-ashburn-1",
        "tenancy": "tenancy1",
        "user": "user1",
    }
    mock_coordinator.username = "Test User"

    # Test CPU Sensor
    description = next(s for s in SENSORS if s.key == "cpu_utilization")
    sensor = OCISensor(mock_coordinator, "inst1", description)
    assert sensor.native_value == 12.34
    assert sensor.native_unit_of_measurement == PERCENTAGE
    assert sensor.name == "CPU Utilization"

    # Test Memory Sensor
    description = next(s for s in SENSORS if s.key == "memory_utilization")
    sensor = OCISensor(mock_coordinator, "inst1", description)
    assert sensor.native_value == 50.0

    # Test State Sensor
    description = next(s for s in SENSORS if s.key == "instance_state")
    sensor = OCISensor(mock_coordinator, "inst1", description)
    assert sensor.native_value == "RUNNING"

    # Test Account Sensor (Used OCPU)
    description = next(s for s in ACCOUNT_SENSORS if s.key == "used_arm_ocpu")
    sensor = OCIAccountSensor(mock_coordinator, description)
    assert sensor.native_value == 4.0

    # Test Account Sensor (Used Memory)
    description = next(s for s in ACCOUNT_SENSORS if s.key == "used_arm_mem")
    sensor = OCIAccountSensor(mock_coordinator, description)
    assert sensor.native_value == 24.0

    # Test Volume Sensor
    description = next(s for s in VOLUME_SENSORS if s.key == "volume_size")
    sensor = OCIVolumeSensor(mock_coordinator, "vol1", description)
    assert sensor.native_value == 50
    assert sensor.name == "Boot Volume Volume Size"

    # Test Volume Throttling Sensor
    description = next(s for s in VOLUME_SENSORS if s.key == "volume_throttled_ios")
    sensor = OCIVolumeSensor(mock_coordinator, "vol1", description)
    assert sensor.native_value == 0.0
