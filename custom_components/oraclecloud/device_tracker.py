"""Device tracker platform for Oracle Cloud Infrastructure."""

from __future__ import annotations

from typing import Any

from homeassistant.components.device_tracker import SourceType
from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import OCIUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up OCI device trackers based on a config entry."""
    coordinator: OCIUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[OCIDeviceTracker] = []

    # Instance Trackers
    instances_data = coordinator.data.get("instances", {})
    for instance_id in instances_data:
        entities.append(OCIDeviceTracker(coordinator, instance_id))

    async_add_entities(entities)


class OCIDeviceTracker(CoordinatorEntity[OCIUpdateCoordinator], TrackerEntity):
    """Representation of an OCI device tracker."""

    _attr_has_entity_name = True
    _attr_name = "Presence"

    def __init__(
        self,
        coordinator: OCIUpdateCoordinator,
        instance_id: str,
    ) -> None:
        """Initialize the device tracker."""
        super().__init__(coordinator)
        self.instance_id = instance_id
        self._attr_unique_id = f"{instance_id}_tracker"

        instance_data = coordinator.data["instances"].get(instance_id)
        if not instance_data:
            return
        instance = instance_data["instance"]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, instance_id)},
            name=instance.display_name,
            manufacturer="Oracle",
            model=instance.shape,
            configuration_url=f"https://cloud.oracle.com/compute/instances/{instance_id}/details?region={coordinator.config['region']}",
        )

    @property
    def mac_address(self) -> str | None:
        """Return the mac address of the device."""
        instance_data = self.coordinator.data["instances"].get(self.instance_id)
        if not instance_data:
            return None
        return instance_data.get("mac_address")

    @property
    def is_connected(self) -> bool:
        """Return true if the device is connected."""
        instance_data = self.coordinator.data["instances"].get(self.instance_id)
        if not instance_data:
            return False
        return instance_data["instance"].lifecycle_state == "RUNNING"

    @property
    def state(self) -> str:
        """Return the state of the device tracker."""
        return "home" if self.is_connected else "not_home"

    @property
    def source_type(self) -> SourceType:
        """Return the source type."""
        return SourceType.ROUTER

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return device state attributes."""
        instance_data = self.coordinator.data["instances"].get(self.instance_id)
        if not instance_data:
            return {}

        instance = instance_data["instance"]
        attrs = {
            "ocid": self.instance_id,
            "region": self.coordinator.config["region"],
            "availability_domain": instance.availability_domain,
            "fault_domain": instance.fault_domain,
            "shape": instance.shape,
            "state": instance.lifecycle_state,
            "public_ip": instance_data.get("public_ip"),
            "private_ip": instance_data.get("private_ip"),
            "time_created": instance.time_created.isoformat()
            if instance.time_created
            else None,
        }

        # Add Specs from shape_config
        if hasattr(instance, "shape_config") and instance.shape_config:
            if (val := instance.shape_config.ocpus) is not None:
                attrs["ocpus"] = val
            if (val := instance.shape_config.memory_in_gbs) is not None:
                attrs["memory_gb"] = val
            if (val := instance.shape_config.local_disks_total_size_in_gbs) is not None:
                attrs["local_disks_size_gb"] = val
            if (val := instance.shape_config.processor_description) is not None:
                attrs["processor_description"] = val

        # Add OS Details from Coordinator
        if (val := instance_data.get("os_name")) is not None:
            attrs["os_name"] = val
        if (val := instance_data.get("os_version")) is not None:
            attrs["os_version"] = val

        return attrs
