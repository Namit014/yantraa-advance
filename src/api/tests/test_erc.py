import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from netlist_to_skidl import run_erc_on_netlist
from schematic import step6_validate_pin_compatibility

# Mock parts_db for testing
MOCK_PARTS_DB = [
    {
        "id": "MCU1",
        "category": "microcontroller",
        "logic_voltage": 3.3,
        "pins": [
            {"name": "GND", "type": "ground", "skidl_type": "PWRIN"},
            {"name": "VCC", "type": "power", "skidl_type": "PWRIN"},
            {"name": "OUT1", "type": "digital_out", "skidl_type": "OUTPUT", "logic_V": 3.3},
            {"name": "IN1", "type": "digital_in", "skidl_type": "INPUT", "logic_V": 3.3}
        ]
    },
    {
        "id": "SENSOR1",
        "category": "sensor",
        "pins": [
            {"name": "GND", "type": "ground", "skidl_type": "PWRIN"},
            {"name": "VCC", "type": "power", "skidl_type": "PWRIN"},
            {"name": "SIG_IN", "type": "digital_in", "skidl_type": "INPUT", "logic_V": 5.0}
        ]
    },
    {
        "id": "DRV1",
        "category": "driver",
        "electrical_constraints": [
            {"rule": "must_connect", "pin": "RESET", "target_rail": "VDD", "severity": "error"}
        ],
        "pins": [
            {"name": "OUT", "type": "motor_out", "skidl_type": "OUTPUT"},
            {"name": "RESET", "type": "digital_in", "skidl_type": "INPUT"}
        ]
    },
    {
        "id": "PSU1",
        "category": "power",
        "output_rails": [{"rail": "VDD", "voltage": 5.0, "max_current_mA": 1000}],
        "pins": [
            {"name": "VDD", "type": "power", "skidl_type": "PWROUT", "rail": "VDD"}
        ]
    }
]
PDB_INDEX = {p["id"]: p for p in MOCK_PARTS_DB}

def test_a_valid_circuit_zero_errors():
    netlist = {
        "components": [
            {"id": "U1", "partId": "MCU1", "designator": "U1"},
            {"id": "U2", "partId": "SENSOR1", "designator": "U2"},
            {"id": "U3", "partId": "PSU1", "designator": "U3"}
        ],
        "nets": [
            {"name": "VDD", "members": [
                {"componentId": "U3", "pinName": "VDD"},
                {"componentId": "U1", "pinName": "VCC"},
                {"componentId": "U2", "pinName": "VCC"}
            ]},
            {"name": "SIG", "members": [
                {"componentId": "U1", "pinName": "OUT1"},
                {"componentId": "U2", "pinName": "SIG_IN"}
            ]}
        ]
    }
    issues = run_erc_on_netlist(netlist, MOCK_PARTS_DB)
    errors = [i for i in issues if i["severity"] == "error"]
    assert len(errors) == 0

def test_b_shorted_outputs_produces_error():
    netlist = {
        "components": [
            {"id": "D1", "partId": "DRV1", "designator": "D1"},
            {"id": "D2", "partId": "DRV1", "designator": "D2"}
        ],
        "nets": [
            {"name": "SHORTED", "members": [
                {"componentId": "D1", "pinName": "OUT"},
                {"componentId": "D2", "pinName": "OUT"}
            ]}
        ]
    }
    issues = run_erc_on_netlist(netlist, MOCK_PARTS_DB)
    errors = [i for i in issues if i["severity"] == "error"]
    assert len(errors) > 0

def test_c_floating_input_produces_warning():
    resolved = [
        {"id": "U2", "partId": "SENSOR1", "designator": "U2"}
    ]
    issues = step6_validate_pin_compatibility(resolved, {}, PDB_INDEX, {})
    warnings = [i for i in issues if i["severity"] == "warning" and "required input" in i["message"]]
    assert len(warnings) > 0

def test_d_constraint_violation_reset_unconnected():
    resolved = [
        {"id": "D1", "partId": "DRV1", "designator": "D1"}
    ]
    issues = step6_validate_pin_compatibility(resolved, {}, PDB_INDEX, {})
    errors = [i for i in issues if i["severity"] == "error" and "constraint not satisfied" in i["message"]]
    assert len(errors) > 0

def test_e_voltage_mismatch_3v3_mcu_5v_sensor():
    resolved = [
        {"id": "U1", "partId": "MCU1", "designator": "U1"},
        {"id": "U2", "partId": "SENSOR1", "designator": "U2"}
    ]
    issues = step6_validate_pin_compatibility(resolved, {}, PDB_INDEX, {})
    warnings = [i for i in issues if i["severity"] == "warning" and "expects 5.0V logic" in i["message"]]
    assert len(warnings) > 0
