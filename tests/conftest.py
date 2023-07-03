"""Fixtures for testing."""
from unittest.mock import Mock, patch

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture(name="inverter", scope="module")
def remote_fixture():
    """Patch the SAJDataUpdateCoordinator."""

    with patch(
        "custom_components.saj.coordinator.SAJDataUpdateCoordinator"
    ) as inverter_class:
        inverter = Mock()

        async def mock_connect():
            if inverter.error:
                err = inverter.error
                inverter.error = None
                raise err

        inverter.connect = mock_connect
        inverter.get_enabled_sensors = lambda: ["a", "b"]
        inverter.name = "mock inverter name"
        inverter.serialnumber = "mock_serial_123"
        inverter_class.return_value = inverter
        yield inverter
