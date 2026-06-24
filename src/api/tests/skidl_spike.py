"""
Phase 0 spike: Validate SKiDL ad-hoc Part construction + ERC before the full rewrite.
Run: python src/api/tests/skidl_spike.py
Expected output: ERC must catch the shorted OUTPUT pins (test_b).
"""
from skidl import Part, Net, Pin, ERC, SKIDL, TEMPLATE, reset

def test_valid_circuit():
    reset()
    # MCU: one OUTPUT pin
    mcu = Part(tool=SKIDL, name="MCU", footprint="", dest=TEMPLATE)
    mcu += Pin(num=1, name="GND", func=Pin.types.PWRIN)
    mcu += Pin(num=2, name="VCC", func=Pin.types.PWROUT)
    mcu += Pin(num=3, name="OUT", func=Pin.types.OUTPUT)
    u1 = mcu()
    # Sensor: one INPUT pin
    sensor = Part(tool=SKIDL, name="SENSOR", footprint="", dest=TEMPLATE)
    sensor += Pin(num=1, name="GND", func=Pin.types.PWRIN)
    sensor += Pin(num=2, name="VCC", func=Pin.types.PWRIN)
    sensor += Pin(num=3, name="IN",  func=Pin.types.INPUT)
    s1 = sensor()
    n_gnd = Net("GND")
    n_gnd += u1["GND"]
    n_gnd += s1["GND"]
    
    n_vcc = Net("+5V")
    n_vcc += u1["VCC"]
    n_vcc += s1["VCC"]
    
    n_sig = Net("SIG")
    n_sig += u1["OUT"]
    n_sig += s1["IN"]
    ERC()
    print("test_valid_circuit: DONE — check above for unexpected errors")

def test_shorted_outputs():
    reset()
    d1 = Part(tool=SKIDL, name="DRV1", footprint="", dest=TEMPLATE)
    d1 += Pin(num=1, name="OUT", func=Pin.types.OUTPUT)
    d2 = Part(tool=SKIDL, name="DRV2", footprint="", dest=TEMPLATE)
    d2 += Pin(num=1, name="OUT", func=Pin.types.OUTPUT)
    i1, i2 = d1(), d2()
    n_short = Net("SHORTED")
    n_short += i1["OUT"]
    n_short += i2["OUT"]
    ERC()
    print("test_shorted_outputs: ERC MUST report a multiple-driver error above")

if __name__ == "__main__":
    test_valid_circuit()
    test_shorted_outputs()
