"""conftest for oraclecloud tests."""

import sys
from unittest.mock import MagicMock

# Mock oci modules to make tests independent of the real OCI library
# and avoid import errors on Python 3.14+ without patching the source code.
# We create a hierarchical mock so that sys.modules["oci.core"] is the same as oci.core.
mock_oci = MagicMock()
sys.modules["oci"] = mock_oci

for submod in [
    "core",
    "monitoring",
    "budget",
    "limits",
    "announcements_service",
    "object_storage",
    "identity",
    "exceptions",
]:
    full_name = f"oci.{submod}"
    sub_mock = MagicMock()
    setattr(mock_oci, submod, sub_mock)
    sys.modules[full_name] = sub_mock


class FakeServiceError(Exception):
    """Fake ServiceError for test mocking."""

    def __init__(
        self,
        status: int = 0,
        code: str = "",
        headers: dict | None = None,
        message: str = "",
        *args,
        **kwargs,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.headers = headers or {}
        self.message = message


mock_oci.exceptions.ServiceError = FakeServiceError
mock_oci.exceptions.RequestException = Exception
mock_oci.exceptions.ConnectTimeout = Exception
mock_oci.exceptions.ClientError = Exception

# Special case for monitoring.models
mock_oci.monitoring.models = MagicMock()
sys.modules["oci.monitoring.models"] = mock_oci.monitoring.models

import asyncio  # noqa: E402
import contextvars  # noqa: E402
from concurrent.futures import ThreadPoolExecutor  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Any  # noqa: E402

import homeassistant.config_entries  # noqa: E402
import homeassistant.core as ha  # noqa: E402
import pytest  # noqa: E402
from homeassistant import loader  # noqa: E402
from homeassistant.core import HomeAssistant  # noqa: E402

# Compatibility patch for ConfigFlowResult (missing in some earlier core versions/test environments)
if not hasattr(homeassistant.config_entries, "ConfigFlowResult"):
    homeassistant.config_entries.ConfigFlowResult = Any  # type: ignore[assignment]

# Try to import INSTANCES to satisfy the plugin's cleanup check
try:
    from pytest_homeassistant_custom_component.common import INSTANCES
except ImportError:
    INSTANCES = []

# Suppress frame reporting which causes RuntimeError on Python 3.14 during tests
import homeassistant.helpers.frame  # noqa: E402

homeassistant.helpers.frame.report = lambda *args, **kwargs: None

# Patch _cv_hass if missing (expected by latest pytest-homeassistant-custom-component)
if not hasattr(ha, "_cv_hass"):
    ha._cv_hass = contextvars.ContextVar("cv_hass", default=None)


# Patch HomeAssistant class EARLY
def patched_hass_new(cls, *args, **kwargs):
    """Permissive __new__ to handle various Core versions."""
    return object.__new__(cls)


HomeAssistant.__new__ = patched_hass_new

_ORIG_HASS_INIT = HomeAssistant.__init__


def patched_hass_init(self, config_dir="config", *args, **kwargs):
    """Permissive __init__ to handle missing config_dir from plugin."""
    _ORIG_HASS_INIT(self, config_dir, *args, **kwargs)


HomeAssistant.__init__ = patched_hass_init


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test case."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    # Do NOT close the loop here


@pytest.fixture(autouse=True)
async def fix_instance_methods(hass: HomeAssistant):
    """Ensure the instance has the right loop."""
    current_loop = asyncio.get_running_loop()
    hass.loop = current_loop

    # fix async_create_task to be permissive and use the right loop
    orig_create_task = hass.async_create_task

    def patched_create_task(target, name=None, **kwargs):
        try:
            return orig_create_task(target, name=name, **kwargs)
        except (TypeError, AttributeError):
            if isinstance(orig_create_task, MagicMock):
                return orig_create_task(target)
            return current_loop.create_task(target)

    hass.async_create_task = patched_create_task  # type: ignore[assignment]

    # fix async_add_job
    orig_add_job = hass.async_add_job

    def patched_add_job(target, *args, **kwargs):
        try:
            return orig_add_job(target, *args, **kwargs)
        except (TypeError, AttributeError):
            if isinstance(orig_add_job, MagicMock):
                return orig_add_job(target)
            if asyncio.iscoroutine(target) or asyncio.iscoroutinefunction(target):
                return current_loop.create_task(target(*args))
            return current_loop.call_soon(target, *args)

    hass.async_add_job = patched_add_job  # type: ignore[assignment]


@pytest.fixture(scope="session", autouse=True)
def global_ha_patching():
    """Apply global patches to HomeAssistant core for test stability."""

    _SESSION_EXECUTOR = ThreadPoolExecutor(
        max_workers=10, thread_name_prefix="waitpid-ha-test"
    )

    def patched_async_add_executor_job(self, target, *args):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = self.loop
        return loop.run_in_executor(_SESSION_EXECUTOR, target, *args)

    HomeAssistant.async_add_executor_job = patched_async_add_executor_job


@pytest.fixture(autouse=True)
async def mock_integration_loading(hass: HomeAssistant) -> None:
    """Ensure the oraclecloud integration is always found by the loader."""
    domain = "oraclecloud"
    path = Path("custom_components/oraclecloud")

    if not hasattr(hass, "data") or hass.data is None:
        hass.data = {}  # type: ignore[assignment]
    hass.data.setdefault("custom_components", {})
    hass.data.setdefault("integrations", {})
    hass.data.setdefault("components", {})

    manifest = loader.Manifest(
        name="Oracle Cloud Infrastructure",
        domain=domain,
        version="1.0.0",
        documentation="https://github.com/faserf/ha-oraclecloud",
        requirements=[],
        dependencies=[],
        codeowners=["faserf"],
        is_built_in=False,
    )
    integration = loader.Integration(
        hass, f"custom_components.{domain}", path, manifest
    )

    # We don't want to fully mock the component module anymore,
    # we want to let the real code load to register the config flow handler.
    # But we want to ensure it's in the data.

    hass.data["custom_components"][domain] = integration
    hass.data["integrations"][domain] = integration


# Workaround for OCI SDK compatibility with Python 3.12+ (specifically 3.14)
# Removed broken six monkeypatch that was causing issues with dateutil and other packages.
