"""Tests for the Oracle Cloud Infrastructure coordinator."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from homeassistant.core import HomeAssistant

from custom_components.oraclecloud.coordinator import OCIUpdateCoordinator

from .test_config_flow import MOCK_DATA


@patch("oci.core.ComputeClient")
@patch("oci.monitoring.MonitoringClient")
@patch("oci.core.VirtualNetworkClient")
@patch("oci.budget.BudgetClient")
@patch("oci.limits.LimitsClient")
@patch("oci.announcements.AnnouncementsClient")
@patch("oci.core.BlockstorageClient")
@patch("oci.object_storage.ObjectStorageClient")
async def test_coordinator_update(
    mock_objectstorage: Any,
    mock_blockstorage: Any,
    mock_announcements: Any,
    mock_limits: Any,
    mock_budget: Any,
    mock_vnic_client: Any,
    mock_monitoring: Any,
    mock_compute: Any,
    hass: HomeAssistant,
) -> None:
    """Test coordinator data update."""
    mock_entry = MagicMock()
    mock_entry.data = MOCK_DATA

    coordinator = OCIUpdateCoordinator(hass, mock_entry)

    # Mock Instance response
    mock_instance = MagicMock()
    mock_instance.id = "inst1"
    mock_instance.display_name = "My VM"
    mock_instance.lifecycle_state = "RUNNING"
    mock_instance.compartment_id = "comp1"
    mock_instance.shape = "VM.Standard.A1.Flex"
    mock_instance.shape_config = MagicMock()
    mock_instance.shape_config.ocpus = 4
    mock_instance.shape_config.memory_in_gbs = 24
    mock_instance.source_details = MagicMock()
    mock_instance.source_details.image_id = "image1"
    mock_compute.return_value.list_instances.return_value.data = [mock_instance]

    # Mock Image response
    mock_image = MagicMock()
    mock_image.os_name = "Ubuntu"
    mock_image.os_version = "22.04"
    mock_compute.return_value.get_image.return_value.data = mock_image

    # Mock VNIC response
    mock_vnic_attach = MagicMock()
    mock_vnic_attach.vnic_id = "vnic1"
    mock_compute.return_value.list_vnic_attachments.return_value.data = [
        mock_vnic_attach
    ]

    mock_vnic_data = MagicMock()
    mock_vnic_data.public_ip = "1.2.3.4"
    mock_vnic_data.private_ip = "10.0.0.1"
    mock_vnic_data.mac_address = "00:11:22:33:44:55"
    mock_vnic_client.return_value.get_vnic.return_value.data = mock_vnic_data

    # Mock Metric response
    mock_datapoint = MagicMock()
    mock_datapoint.value = 45.5
    mock_stats = MagicMock()
    mock_stats.aggregated_datapoints = [mock_datapoint]
    mock_monitoring.return_value.summarize_metrics_data.return_value.data = [mock_stats]

    # Mock Budget response
    mock_budget_data = MagicMock()
    mock_budget_data.amount = 100.0
    mock_budget_data.actual_spend = 10.5
    mock_budget_data.forecasted_spend = 50.0
    mock_budget_data.alert_rule_count = 1
    mock_budget.return_value.list_budgets.return_value.data = [mock_budget_data]

    # Mock Limits response
    mock_limit_value = MagicMock()
    mock_limit_value.name = "standard-a1-core-count"
    mock_limit_value.value = 4
    mock_limits.return_value.list_limit_values.return_value.data = [mock_limit_value]

    # Mock Announcements response
    mock_announcements.return_value.list_announcements.return_value.data = [MagicMock()]

    # Mock Block Storage response
    mock_volume = MagicMock()
    mock_volume.id = "vol1"
    mock_volume.display_name = "Boot Volume"
    mock_volume.size_in_gbs = 50
    mock_volume.lifecycle_state = "AVAILABLE"
    mock_blockstorage.return_value.list_volumes.return_value.data = [mock_volume]

    # Mock Object Storage response
    mock_objectstorage.return_value.get_namespace.return_value.data = "namespace"
    mock_bucket = MagicMock()
    mock_bucket.name = "my-bucket"
    mock_objectstorage.return_value.list_buckets.return_value.data = [mock_bucket]
    mock_bucket_details = MagicMock()
    mock_bucket_details.approximate_size = 1024
    mock_bucket_details.approximate_count = 5
    mock_objectstorage.return_value.get_bucket.return_value.data = mock_bucket_details

    # Fetch data
    data = await coordinator._async_update_data()

    assert "instances" in data
    assert "inst1" in data["instances"]
    assert data["instances"]["inst1"]["instance"] == mock_instance
    assert data["instances"]["inst1"]["public_ip"] == "1.2.3.4"
    assert data["instances"]["inst1"]["private_ip"] == "10.0.0.1"
    assert data["instances"]["inst1"]["mac_address"] == "00:11:22:33:44:55"
    assert data["instances"]["inst1"]["os_name"] == "Ubuntu"
    assert data["instances"]["inst1"]["cpu_utilization"] == 45.5

    assert "account" in data
    assert data["account"]["budget"]["actual_spend"] == 10.5
    assert data["account"]["limits"]["standard-a1-core-count"] == 4
    assert data["account"]["announcements"] == 1
    assert len(data["account"]["volumes"]) == 1
    assert data["account"]["volumes"][0]["display_name"] == "Boot Volume"
    assert len(data["account"]["buckets"]) == 1
    assert data["account"]["buckets"][0]["name"] == "my-bucket"
    assert data["account"]["buckets"][0]["size"] == 1024
