"""Sensor platform for Oracle Cloud Infrastructure."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfInformation
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_AVAILABILITY_DOMAIN,
    ATTR_REGION,
    ATTR_SHAPE,
    DOMAIN,
)
from .coordinator import OCIUpdateCoordinator

SENSORS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="cpu_utilization",
        name="CPU Utilization",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:cpu-64-bit",
    ),
    SensorEntityDescription(
        key="memory_utilization",
        name="Memory Utilization",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="disk_utilization",
        name="Disk Utilization",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:harddisk",
    ),
    SensorEntityDescription(
        key="network_bytes_in",
        name="Network In",
        native_unit_of_measurement=UnitOfInformation.BYTES,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="network_bytes_out",
        name="Network Out",
        native_unit_of_measurement=UnitOfInformation.BYTES,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="instance_state",
        name="Instance State",
        device_class=SensorDeviceClass.ENUM,
        options=[
            "RUNNING",
            "STOPPED",
            "STARTING",
            "STOPPING",
            "TERMINATED",
            "TERMINATING",
            "PROVISIONING",
        ],
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="memory_total",
        name="Total Memory",
        native_unit_of_measurement=UnitOfInformation.GIGABYTES,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="memory_used",
        name="Used Memory",
        native_unit_of_measurement=UnitOfInformation.GIGABYTES,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="memory_free",
        name="Free Memory",
        native_unit_of_measurement=UnitOfInformation.GIGABYTES,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="public_ip",
        name="Public IP",
        icon="mdi:ip-network",
    ),
    SensorEntityDescription(
        key="private_ip",
        name="Private IP",
        icon="mdi:ip-network-outline",
        entity_registry_enabled_default=False,
    ),
    # Advanced Metrics (Disabled by default)
    SensorEntityDescription(
        key="disk_bytes_read",
        name="Disk Read Bytes",
        native_unit_of_measurement=UnitOfInformation.BYTES,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="disk_bytes_written",
        name="Disk Write Bytes",
        native_unit_of_measurement=UnitOfInformation.BYTES,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="disk_iops_read",
        name="Disk Read IOPS",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:harddisk-arrow-down",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="disk_iops_written",
        name="Disk Write IOPS",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:harddisk-arrow-up",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="network_drop_in",
        name="Network In Drops",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:network-off-outline",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="network_drop_out",
        name="Network Out Drops",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:network-off-outline",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="network_error_in",
        name="Network In Errors",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:alert-circle-outline",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="network_error_out",
        name="Network Out Errors",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:alert-circle-outline",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="load_average",
        name="Load Average (1m)",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:speedometer",
        entity_registry_enabled_default=False,
    ),
    # Instance Metadata (Disabled by default)
    SensorEntityDescription(
        key="ocid",
        name="Instance OCID",
        icon="mdi:identifier",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="fault_domain",
        name="Fault Domain",
        icon="mdi:server-network",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="time_created",
        name="Created At",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="availability_domain",
        name="Availability Domain",
        icon="mdi:earth",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="shape",
        name="Shape",
        icon="mdi:cpu-64-bit",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="region",
        name="Region",
        icon="mdi:map-marker",
        entity_registry_enabled_default=False,
    ),
)

ACCOUNT_SENSORS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="budget_actual",
        name="Monthly Spend",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
    ),
    SensorEntityDescription(
        key="budget_forecast",
        name="Forecasted Spend",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
    ),
    SensorEntityDescription(
        key="announcements_count",
        name="Active Announcements",
        icon="mdi:bullhorn",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="limit_arm_ocpu",
        name="Remaining ARM OCPUs",
        icon="mdi:cpu-64-bit",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="limit_arm_mem",
        name="Remaining ARM Memory",
        native_unit_of_measurement=UnitOfInformation.GIGABYTES,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
)

VOLUME_SENSORS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="volume_size",
        name="Volume Size",
        native_unit_of_measurement=UnitOfInformation.GIGABYTES,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="volume_state",
        name="Volume State",
        icon="mdi:database",
    ),
)

BUCKET_SENSORS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="bucket_size",
        name="Bucket Size",
        native_unit_of_measurement=UnitOfInformation.BYTES,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="bucket_count",
        name="Object Count",
        icon="mdi:file-multiple",
        state_class=SensorStateClass.MEASUREMENT,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up OCI sensors based on a config entry."""
    coordinator: OCIUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = []

    # Instance Sensors
    instances_data = coordinator.data.get("instances", {})
    for instance_id in instances_data:
        for description in SENSORS:
            entities.append(OCISensor(coordinator, instance_id, description))

    # Account Sensors
    account_data = coordinator.data.get("account", {})
    if account_data:
        for description in ACCOUNT_SENSORS:
            entities.append(OCIAccountSensor(coordinator, description))

        # Volume Sensors
        for volume in account_data.get("volumes", []):
            for description in VOLUME_SENSORS:
                entities.append(OCIVolumeSensor(coordinator, volume["id"], description))

        # Bucket Sensors
        for bucket in account_data.get("buckets", []):
            for description in BUCKET_SENSORS:
                entities.append(
                    OCIBucketSensor(coordinator, bucket["name"], description)
                )

    async_add_entities(entities)


class OCISensor(CoordinatorEntity[OCIUpdateCoordinator], SensorEntity):
    """Representation of an OCI sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: OCIUpdateCoordinator,
        instance_id: str,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.instance_id = instance_id
        self.entity_description = description
        self._attr_unique_id = f"{instance_id}_{description.key}"

        instance_data = coordinator.data["instances"].get(instance_id)
        if not instance_data:
            return
        instance = instance_data["instance"]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, instance_id)},
            name=instance.display_name,
            manufacturer="Oracle",
            model=instance.shape,
            sw_version=f"{instance.source_details.os_name} {instance.source_details.os_version}"
            if hasattr(instance.source_details, "os_name")
            else None,
            configuration_url=f"https://cloud.oracle.com/compute/instances/{instance_id}/details?region={coordinator.config['region']}",
        )

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        instance_data = self.coordinator.data["instances"].get(self.instance_id)
        if not instance_data:
            return None

        if self.entity_description.key == "instance_state":
            instance = instance_data.get("instance")
            return instance.lifecycle_state if instance else None

        if self.entity_description.key == "ocid":
            return self.instance_id

        if self.entity_description.key == "fault_domain":
            return instance_data["instance"].fault_domain

        if self.entity_description.key == "time_created":
            return instance_data["instance"].time_created

        if self.entity_description.key == "availability_domain":
            return instance_data["instance"].availability_domain

        if self.entity_description.key == "shape":
            return instance_data["instance"].shape

        if self.entity_description.key == "region":
            return self.coordinator.config["region"]

        if self.entity_description.key == "private_ip":
            return instance_data.get("private_ip")

        if self.entity_description.key == "memory_total":
            instance = instance_data.get("instance")
            return (
                instance.shape_config.memory_in_gbs
                if hasattr(instance, "shape_config") and instance.shape_config
                else None
            )

        if self.entity_description.key == "memory_used":
            instance = instance_data.get("instance")
            utilization = instance_data.get("memory_utilization")
            if (
                hasattr(instance, "shape_config")
                and instance.shape_config
                and utilization is not None
            ):
                return round(
                    (instance.shape_config.memory_in_gbs * utilization) / 100, 2
                )
            return None

        if self.entity_description.key == "memory_free":
            instance = instance_data.get("instance")
            utilization = instance_data.get("memory_utilization")
            if (
                hasattr(instance, "shape_config")
                and instance.shape_config
                and utilization is not None
            ):
                return round(
                    instance.shape_config.memory_in_gbs * (1 - utilization / 100), 2
                )
            return None

        return instance_data.get(self.entity_description.key)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity specific state attributes."""
        instance_data = self.coordinator.data["instances"].get(self.instance_id)
        if not instance_data:
            return {}
        instance = instance_data["instance"]
        return {
            ATTR_REGION: self.coordinator.config["region"],
            ATTR_AVAILABILITY_DOMAIN: instance.availability_domain,
            ATTR_SHAPE: instance.shape,
        }


class OCIAccountSensor(CoordinatorEntity[OCIUpdateCoordinator], SensorEntity):
    """Representation of an OCI Account sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: OCIUpdateCoordinator,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"account_{description.key}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self.coordinator.config['tenancy']}_account")},
            name=f"OCI Account ({self.coordinator.username})",
            manufacturer="Oracle",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        account_data = self.coordinator.data.get("account", {})
        if not account_data:
            return None

        if self.entity_description.key == "budget_actual":
            val = account_data.get("budget", {}).get("actual_spend")
            return round(val, 2) if val is not None else None
        if self.entity_description.key == "budget_forecast":
            val = account_data.get("budget", {}).get("forecasted_spend")
            return round(val, 2) if val is not None else None
        if self.entity_description.key == "announcements_count":
            return account_data.get("announcements")
        if self.entity_description.key == "limit_arm_ocpu":
            return account_data.get("limits", {}).get("standard-a1-core-count")
        if self.entity_description.key == "limit_arm_mem":
            return account_data.get("limits", {}).get("standard-a1-memory-count")

        return None


class OCIVolumeSensor(CoordinatorEntity[OCIUpdateCoordinator], SensorEntity):
    """Representation of an OCI Volume sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: OCIUpdateCoordinator,
        volume_id: str,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.volume_id = volume_id
        self.entity_description = description
        self._attr_unique_id = f"{volume_id}_{description.key}"

        volume_data = next(
            (
                v
                for v in coordinator.data.get("account", {}).get("volumes", [])
                if v["id"] == volume_id
            ),
            None,
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, volume_id)},
            name=volume_data["display_name"] if volume_data else "OCI Volume",
            manufacturer="Oracle",
            model="Block Volume",
        )

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        account_data = self.coordinator.data.get("account", {})
        volume_data = next(
            (v for v in account_data.get("volumes", []) if v["id"] == self.volume_id),
            None,
        )
        if not volume_data:
            return None

        if self.entity_description.key == "volume_size":
            return volume_data.get("size_in_gbs")
        if self.entity_description.key == "volume_state":
            return volume_data.get("lifecycle_state")

        return None


class OCIBucketSensor(CoordinatorEntity[OCIUpdateCoordinator], SensorEntity):
    """Representation of an OCI Bucket sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: OCIUpdateCoordinator,
        bucket_name: str,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.bucket_name = bucket_name
        self.entity_description = description
        self._attr_unique_id = f"bucket_{bucket_name}_{description.key}"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"bucket_{bucket_name}")},
            name=f"Bucket {bucket_name}",
            manufacturer="Oracle",
            model="Object Storage Bucket",
        )

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        account_data = self.coordinator.data.get("account", {})
        bucket_data = next(
            (
                b
                for b in account_data.get("buckets", [])
                if b["name"] == self.bucket_name
            ),
            None,
        )
        if not bucket_data:
            return None

        if self.entity_description.key == "bucket_size":
            val = bucket_data.get("size")
            return round(val, 2) if val is not None else None
        if self.entity_description.key == "bucket_count":
            return bucket_data.get("count")

        return None
