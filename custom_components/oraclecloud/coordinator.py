"""DataUpdateCoordinator for Oracle Cloud Infrastructure."""

from __future__ import annotations

import importlib
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

import oci
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

if TYPE_CHECKING:
    import oci.announcements_service
    import oci.budget
    import oci.core
    import oci.limits
    import oci.monitoring
    import oci.object_storage

from .const import (
    CONF_COMPARTMENT,
    CONF_FINGERPRINT,
    CONF_KEY_CONTENT,
    CONF_REGION,
    CONF_TENANCY,
    CONF_USER,
    DOMAIN,
    LOGGER,
)


class OCIUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching OCI data for all instances."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=60),
        )
        self.config = {
            "tenancy": entry.data[CONF_TENANCY],
            "user": entry.data[CONF_USER],
            "fingerprint": entry.data[CONF_FINGERPRINT],
            "region": entry.data[CONF_REGION],
            "key_content": entry.data[CONF_KEY_CONTENT],
        }
        self.compartment_id = (
            entry.data.get(CONF_COMPARTMENT) or entry.data[CONF_TENANCY]
        )
        self.compute_client: oci.core.ComputeClient | None = None
        self.monitoring_client: oci.monitoring.MonitoringClient | None = None
        self.network_client: oci.core.VirtualNetworkClient | None = None
        self.image_cache: dict[str, dict[str, str]] = {}
        self.budget_client: oci.budget.BudgetClient | None = None
        self.limits_client: oci.limits.LimitsClient | None = None
        self.announcements_client: (
            oci.announcements_service.AnnouncementClient | None
        ) = None
        self.blockstorage_client: oci.core.BlockstorageClient | None = None
        self.object_storage_client: oci.object_storage.ObjectStorageClient | None = None
        self.identity_client: oci.identity.IdentityClient | None = None
        self.username: str = entry.data[CONF_USER]

    def _ensure_clients(self) -> None:
        """Ensure OCI clients are initialized. Must be called from the executor."""
        # Ensure submodules are imported in the executor to avoid blocking the event loop
        importlib.import_module("oci.core")
        importlib.import_module("oci.monitoring")
        importlib.import_module("oci.budget")
        importlib.import_module("oci.limits")
        importlib.import_module("oci.announcements_service")
        importlib.import_module("oci.object_storage")
        importlib.import_module("oci.identity")
        importlib.import_module("oci.exceptions")

        if self.compute_client is None:
            self.compute_client = oci.core.ComputeClient(self.config)
        if self.monitoring_client is None:
            self.monitoring_client = oci.monitoring.MonitoringClient(self.config)
        if self.network_client is None:
            self.network_client = oci.core.VirtualNetworkClient(self.config)
        if self.budget_client is None:
            self.budget_client = oci.budget.BudgetClient(self.config)
        if self.limits_client is None:
            self.limits_client = oci.limits.LimitsClient(self.config)
        if self.announcements_client is None:
            self.announcements_client = oci.announcements_service.AnnouncementClient(
                self.config
            )
        if self.blockstorage_client is None:
            self.blockstorage_client = oci.core.BlockstorageClient(self.config)
        if self.object_storage_client is None:
            self.object_storage_client = oci.object_storage.ObjectStorageClient(
                self.config
            )
        if self.identity_client is None:
            self.identity_client = oci.identity.IdentityClient(self.config)

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from OCI for all instances."""
        try:
            return await self.hass.async_add_executor_job(self._fetch_all_oci_data)
        except Exception as err:
            raise UpdateFailed(f"Error communicating with OCI API: {err}") from err

    def _fetch_all_oci_data(self) -> dict[str, Any]:
        """Fetch data for all instances in the compartment."""
        self._ensure_clients()

        # Fetch username once if not already fetched
        if self.identity_client and self.username == self.config["user"]:
            try:
                user = self.identity_client.get_user(self.config["user"]).data
                if user.name:
                    self.username = user.name
            except Exception:
                pass
        assert self.compute_client is not None
        assert self.network_client is not None

        instances = self.compute_client.list_instances(
            compartment_id=self.compartment_id
        ).data

        results: dict[str, dict[str, Any]] = {}
        for instance in instances:
            if instance.lifecycle_state == "TERMINATED":
                continue

            instance_id = instance.id

            # Get OS Details
            os_name = None
            os_version = None
            if hasattr(instance.source_details, "image_id"):
                image_id = instance.source_details.image_id
                if image_id not in self.image_cache:
                    try:
                        image = self.compute_client.get_image(image_id).data
                        self.image_cache[image_id] = {
                            "os_name": image.os_name,
                            "os_version": image.os_version,
                        }
                    except Exception:
                        pass

                if image_id in self.image_cache:
                    os_name = self.image_cache[image_id]["os_name"]
                    os_version = self.image_cache[image_id]["os_version"]

            # Get VNIC for Public/Private IP
            vnics = self.compute_client.list_vnic_attachments(
                compartment_id=instance.compartment_id, instance_id=instance_id
            ).data
            public_ip = None
            private_ip = None
            mac_address = None
            if vnics:
                try:
                    vnic = self.network_client.get_vnic(vnics[0].vnic_id).data
                    public_ip = vnic.public_ip
                    private_ip = vnic.private_ip
                    mac_address = vnic.mac_address
                except Exception:
                    pass

            # Get Metrics
            end_time = datetime.now(UTC)
            start_time = end_time - timedelta(minutes=10)

            cpu = self._get_metric(
                "CpuUtilization",
                instance_id,
                start_time,
                end_time,
                instance.compartment_id,
            )
            mem = self._get_metric(
                "MemoryUtilization",
                instance_id,
                start_time,
                end_time,
                instance.compartment_id,
            )
            disk = self._get_metric(
                "DiskUtilization",
                instance_id,
                start_time,
                end_time,
                instance.compartment_id,
            )
            net_in = self._get_metric(
                "NetworkBytesIn",
                instance_id,
                start_time,
                end_time,
                instance.compartment_id,
            )
            net_out = self._get_metric(
                "NetworkBytesOut",
                instance_id,
                start_time,
                end_time,
                instance.compartment_id,
            )

            # Get Extended Metrics
            disk_read_bytes = self._get_metric(
                "DiskBytesRead",
                instance_id,
                start_time,
                end_time,
                instance.compartment_id,
            )
            disk_write_bytes = self._get_metric(
                "DiskBytesWritten",
                instance_id,
                start_time,
                end_time,
                instance.compartment_id,
            )
            disk_read_iops = self._get_metric(
                "DiskIopsRead",
                instance_id,
                start_time,
                end_time,
                instance.compartment_id,
            )
            disk_write_iops = self._get_metric(
                "DiskIopsWritten",
                instance_id,
                start_time,
                end_time,
                instance.compartment_id,
            )

            net_drop_in = self._get_metric(
                "NetworkDropIn",
                instance_id,
                start_time,
                end_time,
                instance.compartment_id,
            )
            net_drop_out = self._get_metric(
                "NetworkDropOut",
                instance_id,
                start_time,
                end_time,
                instance.compartment_id,
            )
            net_err_in = self._get_metric(
                "NetworkErrorIn",
                instance_id,
                start_time,
                end_time,
                instance.compartment_id,
            )
            net_err_out = self._get_metric(
                "NetworkErrorOut",
                instance_id,
                start_time,
                end_time,
                instance.compartment_id,
            )

            load_avg = self._get_metric(
                "LoadAverage",
                instance_id,
                start_time,
                end_time,
                instance.compartment_id,
            )

            results[instance_id] = {
                "instance": instance,
                "public_ip": public_ip,
                "private_ip": private_ip,
                "mac_address": mac_address,
                "os_name": os_name,
                "os_version": os_version,
                "cpu_utilization": cpu,
                "memory_utilization": mem,
                "disk_utilization": disk,
                "network_bytes_in": net_in,
                "network_bytes_out": net_out,
                "disk_bytes_read": disk_read_bytes,
                "disk_bytes_written": disk_write_bytes,
                "disk_iops_read": disk_read_iops,
                "disk_iops_written": disk_write_iops,
                "network_drop_in": net_drop_in,
                "network_drop_out": net_drop_out,
                "network_error_in": net_err_in,
                "network_error_out": net_err_out,
                "load_average": load_avg,
            }

        # Fetch Account-Wide Metrics (Budgets, Limits, Announcements)
        account_data: dict[str, Any] = {}

        # Budgets
        try:
            assert self.budget_client is not None
            # Use tenancy OCID for budgets as they are usually defined at the root
            budgets = self.budget_client.list_budgets(self.config["tenancy"]).data
            if budgets:
                budget = budgets[0]  # Take first budget for simplicity
                account_data["budget"] = {
                    "amount": budget.amount,
                    "actual_spend": budget.actual_spend,
                    "forecasted_spend": budget.forecasted_spend,
                    "alert_rule_count": budget.alert_rule_count,
                }
            else:
                LOGGER.debug("No budgets found for tenancy %s", self.config["tenancy"])
        except Exception as err:
            LOGGER.error("Failed to fetch budgets: %s", err)

        # Limits (Always Free ARM/AMD)
        try:
            assert self.limits_client is not None
            # Use list_limit_values as it's more robust and doesn't require AD
            limits = self.limits_client.list_limit_values(
                compartment_id=self.config["tenancy"],
                service_name="compute",
            ).data
            relevant_limits = {}
            for limit in limits:
                if limit.name in ["standard-a1-memory-count", "standard-a1-core-count"]:
                    relevant_limits[limit.name] = limit.value
            account_data["limits"] = relevant_limits
        except Exception as err:
            LOGGER.error("Failed to fetch limits: %s", err)

        # Announcements
        try:
            assert self.announcements_client is not None
            announcements = self.announcements_client.list_announcements(
                compartment_id=self.config["tenancy"],
                lifecycle_state="ACTIVE",
            ).data
            # AnnouncementsCollection has an 'items' attribute which is the list
            account_data["announcements"] = len(announcements.items)
        except Exception as err:
            LOGGER.error("Failed to fetch announcements: %s", err)

        # Block Storage
        try:
            assert self.blockstorage_client is not None
            volumes = self.blockstorage_client.list_volumes(
                compartment_id=self.compartment_id
            ).data
            volume_data = []
            for vol in volumes:
                volume_data.append(
                    {
                        "id": vol.id,
                        "display_name": vol.display_name,
                        "size_in_gbs": vol.size_in_gbs,
                        "lifecycle_state": vol.lifecycle_state,
                    }
                )
            account_data["volumes"] = volume_data
        except Exception:
            pass

        # Object Storage
        try:
            assert self.object_storage_client is not None
            namespace = self.object_storage_client.get_namespace().data
            buckets = self.object_storage_client.list_buckets(
                namespace, self.compartment_id
            ).data
            account_data["buckets"] = []
            for bucket in buckets:
                # get_bucket is a separate call for size/count
                bucket_details = self.object_storage_client.get_bucket(
                    namespace, bucket.name
                ).data
                account_data["buckets"].append(
                    {
                        "name": bucket.name,
                        "size": bucket_details.approximate_size,
                        "count": bucket_details.approximate_count,
                    }
                )
        except Exception:
            pass

        return {"instances": results, "account": account_data}

    def _get_metric(
        self,
        metric_name: str,
        instance_id: str,
        start_time: datetime,
        end_time: datetime,
        compartment_id: str,
    ) -> float | None:
        """Fetch a specific metric from OCI Monitoring."""
        self._ensure_clients()
        assert self.monitoring_client is not None

        # Select best namespace based on metric name for better performance
        if (
            metric_name.startswith("Network")
            or metric_name.startswith("DiskBytes")
            or metric_name.startswith("DiskIops")
        ):
            namespaces = ["oci_compute_infrastructure", "oci_computeagent"]
        else:
            namespaces = ["oci_computeagent", "oci_compute_infrastructure"]

        # Cloud monitoring data often has a propagation delay.
        # We look back 60 minutes and add a 2-minute buffer from "now" to ensure data is available.
        now = datetime.now(UTC)
        end_time_eff = now - timedelta(minutes=2)
        start_time_eff = now - timedelta(minutes=62)

        for namespace in namespaces:
            try:
                # Use a robust MQL query. [1m] interval for high-res agents, fallback to infraestructura
                # We use .mean() but since we've buffered, we should get the most recent valid point.
                details = oci.monitoring.models.SummarizeMetricsDataDetails(
                    namespace=namespace,
                    query=f'{metric_name}[1m]{{resourceId="{instance_id}"}}.mean()',
                    start_time=start_time_eff,
                    end_time=end_time_eff,
                )
                stats = self.monitoring_client.summarize_metrics_data(
                    compartment_id, details
                ).data

                if stats and stats[0].aggregated_datapoints:
                    # Return the latest available data point in the window
                    val = stats[0].aggregated_datapoints[-1].value
                    if val is not None:
                        return round(float(val), 2)

            except Exception as err:
                LOGGER.debug(
                    "Failed to fetch metric %s from %s for %s: %s",
                    metric_name,
                    namespace,
                    instance_id,
                    err,
                )
        return None
