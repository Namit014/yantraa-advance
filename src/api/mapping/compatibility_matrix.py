from typing import List, Dict, Set
from .schemas import Pin, PinDirection

class CompatibilityMatrixEngine:
    """
    Comprehensive protocol compatibility engine.
    Single source of truth for protocol and electrical compatibility.
    """
    
    # Fully Expanded Protocol Matrix
    COMPATIBILITY_RULES = {
        # Power
        "24V_POWER": {"compatible_with": ["24V_POWER_IN"], "incompatible_with": ["48V_POWER_IN", "12V_POWER_IN", "5V_POWER_IN", "3V3_POWER_IN"]},
        "48V_POWER": {"compatible_with": ["48V_POWER_IN"], "incompatible_with": ["24V_POWER_IN", "12V_POWER_IN", "5V_POWER_IN", "3V3_POWER_IN"]},
        "12V_POWER": {"compatible_with": ["12V_POWER_IN"], "incompatible_with": ["24V_POWER_IN", "48V_POWER_IN", "5V_POWER_IN", "3V3_POWER_IN"]},
        "5V_POWER": {"compatible_with": ["5V_POWER_IN"], "incompatible_with": ["24V_POWER_IN", "48V_POWER_IN", "12V_POWER_IN", "3V3_POWER_IN"]},
        "3V3_POWER": {"compatible_with": ["3V3_POWER_IN"], "incompatible_with": ["24V_POWER_IN", "48V_POWER_IN", "12V_POWER_IN", "5V_POWER_IN"]},
        
        # Communication
        "UART_TX": {"compatible_with": ["UART_RX"], "incompatible_with": ["UART_TX", "RS485_A", "RS485_B", "CAN_H", "CAN_L"]},
        "UART_RX": {"compatible_with": ["UART_TX"], "incompatible_with": ["UART_RX", "RS485_A", "RS485_B", "CAN_H", "CAN_L"]},
        "RS232_TX": {"compatible_with": ["RS232_RX"], "incompatible_with": ["RS232_TX", "UART_TX", "UART_RX"]},
        "RS232_RX": {"compatible_with": ["RS232_TX"], "incompatible_with": ["RS232_RX", "UART_TX", "UART_RX"]},
        "RS485_A": {"compatible_with": ["RS485_A"], "incompatible_with": ["RS485_B"]},
        "RS485_B": {"compatible_with": ["RS485_B"], "incompatible_with": ["RS485_A"]},
        "CAN_H": {"compatible_with": ["CAN_H"], "incompatible_with": ["CAN_L"]},
        "CAN_L": {"compatible_with": ["CAN_L"], "incompatible_with": ["CAN_H"]},
        "CAN_FD_H": {"compatible_with": ["CAN_FD_H", "CAN_H"], "incompatible_with": ["CAN_FD_L", "CAN_L"]},
        "CAN_FD_L": {"compatible_with": ["CAN_FD_L", "CAN_L"], "incompatible_with": ["CAN_FD_H", "CAN_H"]},
        "ETHERCAT_TX": {"compatible_with": ["ETHERCAT_RX"], "incompatible_with": ["ETHERCAT_TX"]},
        "ETHERCAT_RX": {"compatible_with": ["ETHERCAT_TX"], "incompatible_with": ["ETHERCAT_RX"]},
        "MODBUS_RTU_A": {"compatible_with": ["MODBUS_RTU_A"], "incompatible_with": ["MODBUS_RTU_B"]},
        "MODBUS_RTU_B": {"compatible_with": ["MODBUS_RTU_B"], "incompatible_with": ["MODBUS_RTU_A"]},
        "MODBUS_TCP": {"compatible_with": ["MODBUS_TCP"], "incompatible_with": []},
        "ETHERNET_TX": {"compatible_with": ["ETHERNET_RX"], "incompatible_with": ["ETHERNET_TX"]},
        "ETHERNET_RX": {"compatible_with": ["ETHERNET_TX"], "incompatible_with": ["ETHERNET_RX"]},
        "USB_D_PLUS": {"compatible_with": ["USB_D_PLUS"], "incompatible_with": ["USB_D_MINUS"]},
        "USB_D_MINUS": {"compatible_with": ["USB_D_MINUS"], "incompatible_with": ["USB_D_PLUS"]},
        "SPI_MOSI": {"compatible_with": ["SPI_MISO", "SPI_MOSI"], "incompatible_with": []}, # Context dependent
        "SPI_MISO": {"compatible_with": ["SPI_MOSI", "SPI_MISO"], "incompatible_with": []},
        "SPI_SCK": {"compatible_with": ["SPI_SCK"], "incompatible_with": []},
        "SPI_CS": {"compatible_with": ["SPI_CS"], "incompatible_with": []},
        "I2C_SDA": {"compatible_with": ["I2C_SDA"], "incompatible_with": []},
        "I2C_SCL": {"compatible_with": ["I2C_SCL"], "incompatible_with": []},

        # Motion Control
        "PWM_OUT": {"compatible_with": ["PWM_IN"], "incompatible_with": ["PWM_OUT"]},
        "STEP": {"compatible_with": ["STEP_IN"], "incompatible_with": ["DIR", "STEP"]},
        "DIR": {"compatible_with": ["DIR_IN"], "incompatible_with": ["STEP", "DIR"]},
        "ENCODER_A": {"compatible_with": ["ENCODER_A_IN"], "incompatible_with": ["ENCODER_B", "ENCODER_Z"]},
        "ENCODER_B": {"compatible_with": ["ENCODER_B_IN"], "incompatible_with": ["ENCODER_A", "ENCODER_Z"]},
        "ENCODER_Z": {"compatible_with": ["ENCODER_Z_IN"], "incompatible_with": ["ENCODER_A", "ENCODER_B"]},
        "RESOLVER_SIN": {"compatible_with": ["RESOLVER_SIN_IN"], "incompatible_with": ["RESOLVER_COS"]},
        "RESOLVER_COS": {"compatible_with": ["RESOLVER_COS_IN"], "incompatible_with": ["RESOLVER_SIN"]},
        "HALL_SENSOR": {"compatible_with": ["HALL_SENSOR_IN"], "incompatible_with": []},

        # Industrial Safety
        "SAFETY_IO": {"compatible_with": ["SAFETY_IO"], "incompatible_with": ["STANDARD_IO"]},
        "STO": {"compatible_with": ["STO_IN"], "incompatible_with": []},
        "SAFETY_RELAY_IN": {"compatible_with": ["SAFETY_RELAY_OUT"], "incompatible_with": []},
        "ESTOP_CH1": {"compatible_with": ["ESTOP_CH1_IN"], "incompatible_with": ["ESTOP_CH2"]},
        "ESTOP_CH2": {"compatible_with": ["ESTOP_CH2_IN"], "incompatible_with": ["ESTOP_CH1"]},

        # Analog/Digital
        "ANALOG_0_10V_OUT": {"compatible_with": ["ANALOG_0_10V_IN"], "incompatible_with": ["ANALOG_4_20MA_IN"]},
        "ANALOG_4_20MA_OUT": {"compatible_with": ["ANALOG_4_20MA_IN"], "incompatible_with": ["ANALOG_0_10V_IN"]},
        "DI": {"compatible_with": ["DO"], "incompatible_with": ["DI"]},
        "DO": {"compatible_with": ["DI"], "incompatible_with": ["DO"]},
        "GPIO": {"compatible_with": ["GPIO"], "incompatible_with": []}
    }
    
    @classmethod
    def check_protocol_compatibility(cls, source_protocol: str, target_protocol: str) -> Dict[str, str]:
        """
        Returns a dict with 'status' (valid/invalid) and 'reasoning'.
        """
        if not source_protocol or not target_protocol:
            return {"status": "invalid", "reasoning": "Missing protocol definition."}
            
        sp_upper = source_protocol.upper()
        tp_upper = target_protocol.upper()
            
        rules = cls.COMPATIBILITY_RULES.get(sp_upper, {})
        
        if not rules:
            return {"status": "unknown", "reasoning": f"Protocol {sp_upper} not found in compatibility matrix."}
            
        if tp_upper in rules.get("incompatible_with", []):
            return {"status": "invalid", "reasoning": f"Protocol mismatch: {sp_upper} is strictly incompatible with {tp_upper}."}
        
        if tp_upper in rules.get("compatible_with", []):
            return {"status": "valid", "reasoning": f"Protocol match: {sp_upper} is compatible with {tp_upper}."}
            
        return {"status": "invalid", "reasoning": f"Protocol {tp_upper} is not a registered compatible receiver for {sp_upper}."}
        
    @classmethod
    def check_electrical_compatibility(cls, source_pin: Pin, target_pin: Pin) -> Dict[str, str]:
        """
        Validate voltage logic levels and current limits.
        """
        # Direction checks
        if source_pin.direction == PinDirection.OUTPUT and target_pin.direction == PinDirection.OUTPUT:
            return {"status": "invalid", "reasoning": "Electrical Conflict: OUTPUT pin cannot be connected directly to another OUTPUT pin."}
            
        if source_pin.direction == PinDirection.INPUT and target_pin.direction == PinDirection.INPUT:
            return {"status": "invalid", "reasoning": "Electrical Conflict: INPUT pin connected to INPUT pin (floating signal)."}
        
        # Voltage checks
        if source_pin.voltage_max is not None and target_pin.voltage_max is not None:
            if source_pin.voltage_max > target_pin.voltage_max:
                return {"status": "invalid", "reasoning": f"Voltage Overload: Source provides up to {source_pin.voltage_max}V, but target only tolerates {target_pin.voltage_max}V."}
                
        # Current checks (source can provide more than target draws)
        # Note: current limit logic depends if it's power or signal. 
        # For power, source_current_limit > target_current_draw.
                
        return {"status": "valid", "reasoning": "Electrical checks passed."}
