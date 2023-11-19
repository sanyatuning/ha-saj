"""Tests for pysaj package."""

import pytest
from aioresponses import aioresponses
from pytest_homeassistant_custom_component.common import load_fixture
from syrupy import SnapshotAssertion

from custom_components.saj.pysaj import SAJ, Sensors

host = "192.168.0.9"
testdata_eth = [
    "status1.xml",
    "status2.xml",
    "status3.xml",
]
testdata_wifi = [
    (0, "15020J2012EN02905"),
    (1, "21030G1628XXYYYYY"),
    (2, "14020G1728EN19744"),
]


@pytest.fixture
def mocked():
    with aioresponses() as m:
        yield m


@pytest.mark.parametrize("name", testdata_eth)
async def test_eth(name, mocked, snapshot: SnapshotAssertion):
    wifi = False
    info_eth = load_fixture("info.xml")
    status_eth = load_fixture(name)
    mocked.get("http://192.168.0.9/equipment_data.xml", body=info_eth)
    mocked.get("http://192.168.0.9/real_time_data.xml", body=status_eth)

    sensors = Sensors(wifi)
    saj = SAJ(host, wifi)
    await saj.read(sensors)

    assert saj.serialnumber == "13020J2020EN09010"
    assert [s.name + ":" + str(s.value) for s in sensors] == snapshot


@pytest.mark.parametrize("index,serial", testdata_wifi)
async def test_wifi(index, serial, mocked, snapshot: SnapshotAssertion):
    wifi = True
    info_csv = load_fixture("info.csv")
    status_csv = load_fixture("status.csv")

    sensors = Sensors(wifi)
    saj = SAJ(host, wifi)

    info_line = info_csv.split("\n")[index]
    status_line = status_csv.split("\n")[index]

    mocked.get("http://admin:admin@192.168.0.9/info.php", body=info_line)
    mocked.get("http://admin:admin@192.168.0.9/status/status.php", body=status_line)
    await saj.read(sensors)

    enabled_count = len([s for s in sensors if s.enabled])
    if serial == "14020G1728EN19744":
        # invalid CSV
        assert enabled_count == 0
    else:
        assert enabled_count == 9
        assert [s.name + ":" + str(s.value) for s in sensors] == snapshot

    assert saj.serialnumber == serial
