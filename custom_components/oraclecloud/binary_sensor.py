"""Binary sensor platform for Oracle Cloud Infrastructure."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import OCIUpdateCoordinator

BINARY_SENSORS: tuple[BinarySensorEntityDescription, ...] = (
    BinarySensorEntityDescription(
        key="agent_status",
        name="Compute Agent Status",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up OCI binary sensors based on a config entry."""
    coordinator: OCIUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[BinarySensorEntity] = []

    # Instance Binary Sensors
    instances_data = coordinator.data.get("instances", {})
    for instance_id in instances_data:
        for description in BINARY_SENSORS:
            entities.append(OCIBinarySensor(coordinator, instance_id, description))

    # Account Binary Sensors
    account_data = coordinator.data.get("account", {})
    if account_data and "budget" in account_data:
        entities.append(OCIBudgetAlertBinarySensor(coordinator))

    async_add_entities(entities)


class OCIBinarySensor(CoordinatorEntity[OCIUpdateCoordinator], BinarySensorEntity):
    """Representation of an OCI binary sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: OCIUpdateCoordinator,
        instance_id: str,
        description: BinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor."""
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
            configuration_url=f"https://cloud.oracle.com/compute/instances/{instance_id}/details?region={coordinator.config['region']}",
        )

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        instance_data = self.coordinator.data["instances"].get(self.instance_id)
        if not instance_data:
            return False

        if self.entity_description.key == "agent_status":
            # Agent is considered "on" if we have memory utilization data
            return instance_data.get("memory_utilization") is not None

        return False


class OCIBudgetAlertBinarySensor(
    CoordinatorEntity[OCIUpdateCoordinator], BinarySensorEntity
):
    """Representation of an OCI Budget Alert binary sensor."""

    _attr_has_entity_name = True
    _attr_name = "Budget Alert"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator: OCIUpdateCoordinator) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"account_{coordinator.config['tenancy']}_budget_alert"
        self._attr_unique_id = f"account_{coordinator.config['tenancy']}_budget_alert"

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
    def is_on(self) -> bool:
        """Return true if the budget is exceeded."""
        account_data = self.coordinator.data.get("account", {})
        budget = account_data.get("budget")
        if (
            not budget
            or budget.get("actual_spend") is None
            or budget.get("amount") is None
        ):
            return False

        return budget["actual_spend"] >= budget["amount"]
