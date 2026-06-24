import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from schematic import step9_analyze_power

MOCK_PARTS_DB_INDEX = {
    "psu_24v": {
        "id": "psu_24v",
        "category": "power",
        "output_rails": [{"rail": "24V", "voltage": 24.0, "max_current_mA": 10000}]
    },
    "arduino_mega": {
        "id": "arduino_mega",
        "category": "microcontroller",
        "current_draw_mA": 70,
        "pins": [{"name": "VIN", "type": "power", "rail": "24V"}]
    },
    "a4988": {
        "id": "a4988",
        "category": "motor_driver",
        "current_draw_mA": 10,
        "pins": [{"name": "VMOT", "type": "power", "rail": "24V"}]
    }
}

def test_cnc_template_total_mA_matches_parts_db():
    resolved = [
        {"id": "PSU", "partId": "psu_24v"},
        {"id": "MCU", "partId": "arduino_mega"},
        {"id": "DRV1", "partId": "a4988"},
        {"id": "DRV2", "partId": "a4988"},
        {"id": "DRV3", "partId": "a4988"}
    ]
    rails = {
        "24V": {"voltage": 24.0, "max_current_mA": 10000}
    }
    pb, erc = step9_analyze_power(resolved, MOCK_PARTS_DB_INDEX, rails)
    
    # MCU (70) + 3x A4988 (10*3) = 100mA total
    assert pb.total_mA == 100
    # Margin against 10000mA is (10000 - 100)/10000 = 99%
    assert pb.margin_pct == 99
    assert len(erc) == 0

def test_overloaded_rail_produces_erc_error():
    resolved = [
        {"id": "MCU", "partId": "arduino_mega"},
        # Let's say we have 150 MCU clones drawing 70mA each -> 10500mA
    ] + [{"id": f"MCU_{i}", "partId": "arduino_mega"} for i in range(150)]
    
    rails = {
        "24V": {"voltage": 24.0, "max_current_mA": 10000}
    }
    pb, erc = step9_analyze_power(resolved, MOCK_PARTS_DB_INDEX, rails)
    
    # Total draw > 10000mA
    assert pb.total_mA > 10000
    assert pb.margin_pct == 0
    assert len(erc) > 0
    assert any("overloaded" in e["message"] for e in erc)
