"""Button platform for Oracle Cloud Infrastructure."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import oci
from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, LOGGER
from .coordinator import OCIUpdateCoordinator

BUTTONS: tuple[ButtonEntityDescription, ...] = (
    ButtonEntityDescription(
        key="start",
        name="Start",
        icon="mdi:play",
    ),
    ButtonEntityDescription(
        key="stop",
        name="Stop",
        icon="mdi:stop",
    ),
    ButtonEntityDescription(
        key="reboot",
        name="Soft Reboot",
        icon="mdi:restart",
    ),
    ButtonEntityDescription(
        key="reset",
        name="Hard Reset",
        icon="mdi:restart-alert",
        entity_registry_enabled_default=False,
    ),
    ButtonEntityDescription(
        key="diagnostic_reboot",
        name="Diagnostic Reboot",
        icon="mdi:bug-play-outline",
        entity_registry_enabled_default=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up OCI buttons based on a config entry."""
    coordinator: OCIUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[OCIButton] = []

    # Instance Buttons
    instances_data = coordinator.data.get("instances", {})
    for instance_id in instances_data:
        for description in BUTTONS:
            entities.append(OCIButton(coordinator, instance_id, description))

    async_add_entities(entities)


class OCIButton(CoordinatorEntity[OCIUpdateCoordinator], ButtonEntity):
    """Representation of an OCI button."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: OCIUpdateCoordinator,
        instance_id: str,
        description: ButtonEntityDescription,
    ) -> None:
        """Initialize the button."""
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

    async def async_press(self) -> None:
        """Handle the button press."""
        action = ""
        if self.entity_description.key == "start":
            action = "start"
        elif self.entity_description.key == "stop":
            action = "stop"
        elif self.entity_description.key == "reboot":
            action = "softreset"
        elif self.entity_description.key == "reset":
            action = "reset"
        elif self.entity_description.key == "diagnostic_reboot":
            action = "diagnosticreboot"

        try:
            assert self.coordinator.compute_client is not None
            await self.hass.async_add_executor_job(
                self.coordinator.compute_client.instance_action,
                self.instance_id,
                action,
            )
            # Trigger an update soon to reflect the state change
            await self.coordinator.async_request_refresh()
        except oci.exceptions.ServiceError as err:
            LOGGER.error(
                "Failed to perform OCI action %s on %s: %s",
                action,
                self.instance_id,
                err,
            )
