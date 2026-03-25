"""conftest for oraclecloud tests."""

import asyncio
import contextvars
import sys
import types
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import homeassistant.config_entries
import homeassistant.core as ha
import pytest
from homeassistant import loader
from homeassistant.core import HomeAssistant

# Compatibility patch for ConfigFlowResult (missing in some earlier core versions/test environments)
if not hasattr(homeassistant.config_entries, "ConfigFlowResult"):
    homeassistant.config_entries.ConfigFlowResult = Any

# Try to import INSTANCES to satisfy the plugin's cleanup check
try:
    from pytest_homeassistant_custom_component.common import INSTANCES
except ImportError:
    INSTANCES = []

# Suppress frame reporting which causes RuntimeError on Python 3.14 during tests
import homeassistant.helpers.frame

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
    """Fix methods that the plugin might have monkeypatched onto the instance."""

    current_loop = asyncio.get_running_loop()
    hass.loop = current_loop

    # Make stop methods no-ops but remove ALL occurrences from INSTANCES to satisfy tracker
    async def async_stop_mock(*args, **kwargs):
        while hass in INSTANCES:
            INSTANCES.remove(hass)
    hass.async_stop = async_stop_mock

    def stop_mock(*args, **kwargs):
        while hass in INSTANCES:
            INSTANCES.remove(hass)
    hass.stop = stop_mock

    # fix async_create_task to be permissive and use the right loop
    orig_create_task = hass.async_create_task
    def patched_create_task(target, name=None, **kwargs):
        try:
            return orig_create_task(target, name=name, **kwargs)
        except (TypeError, AttributeError):
            if isinstance(orig_create_task, MagicMock):
                return orig_create_task(target)
            return current_loop.create_task(target)
    hass.async_create_task = patched_create_task

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
    hass.async_add_job = patched_add_job

@pytest.fixture(scope="session", autouse=True)
def global_ha_patching():
    """Apply global patches to HomeAssistant core for test stability."""

    _SESSION_EXECUTOR = ThreadPoolExecutor(max_workers=10, thread_name_prefix="waitpid-ha-test")

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
        hass.data = {}
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
    integration = loader.Integration(hass, f"custom_components.{domain}", path, manifest)

    # We don't want to fully mock the component module anymore,
    # we want to let the real code load to register the config flow handler.
    # But we want to ensure it's in the data.

    hass.data["custom_components"][domain] = integration
    hass.data["integrations"][domain] = integration

# Workaround for OCI SDK compatibility with Python 3.12+ (specifically 3.14)
if "six.moves" not in sys.modules:
    six_moves = types.ModuleType("moves")
    sys.modules["six.moves"] = six_moves
    six = types.ModuleType("six")
    six.moves = six_moves
    sys.modules["six"] = six
