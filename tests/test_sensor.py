"""Tests for SAJ sensor."""
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.saj import pysaj
from custom_components.saj.const import DOMAIN
from custom_components.saj.coordinator import CannotConnect, SAJDataUpdateCoordinator
from custom_components.saj.sensor import (
    SAJSensor,
    async_setup_entry,
    async_setup_platform,
)

config = {
    "type": "wifi",
    "host": "192.168.0.22",
    "username": "",
    "password": "",
}


def saj():
    """Mock pysaj library."""

    async def mock_read(sensors):
        for sensor in sensors:
            sensor.enabled = sensor.name == "current_power" or sensor.name == "state"
            if sensor.name == "current_power":
                sensor.value = 1500
        return True

    mock = Mock()
    mock.read = mock_read
    mock.serialnumber = "123456789"
    mock.url = "http://admin:admin@192.168.0.12/info.php"
    return mock


@patch("custom_components.saj.coordinator._init_pysaj", return_value=saj())
async def test_connect(_, hass):
    """Test connect calls mocked read."""
    inverter = SAJDataUpdateCoordinator(hass, config)
    await inverter.connect()
    assert [s.key for s in inverter.get_enabled_sensors()] == ["p-ac", "state"]


@patch("custom_components.saj.coordinator._init_pysaj", return_value=saj())
async def test_cannot_connect(_, hass):
    """Test connect raises CannotConnect."""
    inverter = SAJDataUpdateCoordinator(hass, config)
    inverter._saj.read = AsyncMock()
    inverter._saj.read.return_value = False
    with pytest.raises(CannotConnect):
        await inverter.connect()


@patch("custom_components.saj.coordinator._init_pysaj", return_value=saj())
async def test_import(_, hass):
    """Test that we can import a config entry."""
    assert len(hass.config_entries.async_entries(DOMAIN)) == 0
    await async_setup_platform(hass, {"host": "192.168.0.22"}, Mock())
    await hass.async_block_till_done()
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert entry.data["type"] == "ethernet"


@patch("custom_components.saj.coordinator._init_pysaj", return_value=saj())
async def test_setup_entry(_, hass):
    """Test add entities on setup."""
    config_entry = MockConfigEntry()
    inverter = SAJDataUpdateCoordinator(hass, config)
    hass.data[DOMAIN] = {}
    hass.data[DOMAIN][config_entry.entry_id] = inverter
    add_fn = Mock()
    await async_setup_entry(hass, config_entry, add_fn)
    add_fn.assert_called()


@patch("custom_components.saj.coordinator._init_pysaj", return_value=saj())
async def test_available(_, hass: HomeAssistant):
    """Test available."""
    config_entry = MockConfigEntry()
    inverter = SAJDataUpdateCoordinator(hass, config)
    hass.data[DOMAIN] = {}
    hass.data[DOMAIN][config_entry.entry_id] = inverter
    add_fn = Mock()
    await async_setup_entry(hass, config_entry, add_fn)
    assert inverter.last_update_success
    inverter._saj.read = AsyncMock()
    inverter._saj.read.return_value = False
    await inverter.async_refresh()
    assert inverter.last_update_success is False


@patch("custom_components.saj.coordinator._init_pysaj", return_value=saj())
async def test_sensor(_, hass: HomeAssistant):
    """Test sensor class."""
    inverter = SAJDataUpdateCoordinator(hass, config)
    pysaj_sensor = pysaj.Sensor("p-ac", 11, 23, "", "current_power", "W")
    sensor = SAJSensor(inverter, pysaj_sensor)
    sensor.hass = hass
    assert sensor.name == "SAJ Inverter current_power"
    assert sensor.state is None
    assert sensor.available is False
    inverter.last_update_success = True
    assert sensor.available
    assert sensor.unit_of_measurement == "W"
    assert sensor.device_class == "power"
    assert sensor.unique_id == "123456789_current_power"
    assert sensor.device_info == {
        "identifiers": {(DOMAIN, "123456789")},
        "name": "SAJ Solar inverter",
        "manufacturer": "SAJ",
        "configuration_url": "http://admin:admin@192.168.0.12/",
    }


@patch("custom_components.saj.coordinator._init_pysaj", return_value=saj())
async def test_sensor_temp(_, hass: HomeAssistant):
    """Test sensor class."""
    config2 = config.copy()
    config2["name"] = "Second inverter"
    inverter = SAJDataUpdateCoordinator(hass, config2)
    pysaj_sensor = pysaj.Sensor("temp", 20, 32, "/10", "temperature", "°C")
    sensor = SAJSensor(inverter, pysaj_sensor)
    sensor.hass = hass
    assert sensor.name == "Second inverter temperature"
    assert sensor.unit_of_measurement == "°C"
    assert sensor.device_class == "temperature"


@patch("custom_components.saj.coordinator._init_pysaj", return_value=saj())
async def test_sensor_total_yield(_, hass: HomeAssistant):
    """Test sensor class."""
    inverter = SAJDataUpdateCoordinator(hass, config)
    pysaj_sensor = pysaj.Sensor(
        "e-total", 1, 1, "/100", "total_yield", "kWh", False, True
    )
    sensor = SAJSensor(inverter, pysaj_sensor)
    sensor.hass = hass
    assert sensor.name == "SAJ Inverter total_yield"
    assert sensor.unit_of_measurement == "kWh"
    assert sensor.device_class == "energy"
    assert sensor.state is None
    assert sensor.available is False

    pysaj_sensor.value = 0
    assert sensor.available is False
    assert sensor.state == 0

    pysaj_sensor.value = 42
    assert sensor.available
    assert sensor.state == 42
