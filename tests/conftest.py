"""conftest for oraclecloud tests."""

import sys
import types

import pytest
import homeassistant.util.executor
from concurrent.futures import ThreadPoolExecutor

import homeassistant.helpers.frame
homeassistant.helpers.frame.report = lambda *args, **kwargs: None

from homeassistant.core import HomeAssistant

def patched_async_add_executor_job(self, target, *args):
    """Ensure we use a fresh executor for tests."""
    if not hasattr(self, "_test_executor") or getattr(self._test_executor, "_shutdown", False):
        self._test_executor = ThreadPoolExecutor(max_workers=10)
    return self.loop.run_in_executor(self._test_executor, target, *args)

HomeAssistant.async_add_executor_job = patched_async_add_executor_job
import homeassistant.core as ha
from contextvars import ContextVar

# Workaround for homeassistant.core._cv_hass removal in newer versions
if not hasattr(ha, "_cv_hass"):
    ha._cv_hass = ContextVar("hass")

# Workaround for HomeAssistant constructor changes in newer versions
# Some test plugins call HomeAssistant() without arguments which fails on newer Core.
def patched_hass_new(cls, *args, **kwargs):
    """Patch __new__ to handle missing config_dir."""
    if not args and 'config_dir' not in kwargs:
        return object.__new__(cls)
    return object.__new__(cls)

original_hass_init = HomeAssistant.__init__
def patched_hass_init(self, config_dir: str = "config") -> None:
    """Patch __init__ to handle missing config_dir and initialize data."""
    original_hass_init(self, config_dir)
    if "components" not in self.data:
        self.data["components"] = {}
    if "integrations" not in self.data:
        self.data["integrations"] = {}

HomeAssistant.__new__ = patched_hass_new
HomeAssistant.__init__ = patched_hass_init

# Workaround for OCI SDK compatibility with Python 3.12+ (specifically 3.14)
# The OCI SDK's vendored urllib3 tries to import six.moves which fails on newer Python.
prefix = "oci._vendor.urllib3.packages.six"
if f"{prefix}.moves" not in sys.modules:
    # Ensure parent hierarchy exists as packages
    parts = prefix.split(".")
    for i in range(1, len(parts) + 1):
        parent = ".".join(parts[:i])
        if parent not in sys.modules:
            m = types.ModuleType(parent)
            m.__path__ = []  # Make it a package
            sys.modules[parent] = m
        else:
            m = sys.modules[parent]
            if not hasattr(m, "__path__"):
                m.__path__ = []

    mock_six = sys.modules[prefix]
    mock_moves = types.ModuleType("six.moves")

    # Add common moves used by urllib3/requests
    import http.client as http_client
    import http.cookies as http_cookies
    import urllib.parse as urllib_parse
    import urllib.request as urllib_request

    mock_moves.http_client = http_client
    mock_moves.http_cookies = http_cookies
    mock_moves.urllib_parse = urllib_parse
    mock_moves.urllib_request = urllib_request

    # Inject into sys.modules
    sys.modules[f"{prefix}.moves"] = mock_moves
    mock_six.moves = mock_moves
    sys.modules[f"{prefix}.moves.http_client"] = http_client
    sys.modules[f"{prefix}.moves.http_cookies"] = http_cookies
    sys.modules[f"{prefix}.moves.urllib_parse"] = urllib_parse
    sys.modules[f"{prefix}.moves.urllib_request"] = urllib_request

# Workaround for pytest-homeassistant-custom-component missing asyncio_legacy on Python 3.14
# This specific plugin version seems to have broken imports on newer Python.
try:
    import pytest_homeassistant_custom_component.plugins  # noqa: F401
except ImportError:
    # If the plugin is already failing to import, we need to mock its internal parts
    # before pytest tries to load it as a plugin.
    # Note: conftest.py might be loaded after the plugin if it's an entry point plugin.
    pass

if "pytest_homeassistant_custom_component.asyncio_legacy" not in sys.modules:
    mock_asyncio_legacy = types.ModuleType("asyncio_legacy")
    mock_asyncio_legacy.legacy_coroutine = lambda x: x  # Dummy decorator
    sys.modules["pytest_homeassistant_custom_component.asyncio_legacy"] = mock_asyncio_legacy


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    import asyncio
    # On Windows, asyncio needs socket.socketpair() which might be blocked by pytest-socket
    try:
        import pytest_socket
        pytest_socket.enable_socket()
    except (ImportError, AttributeError):
        pass
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()
