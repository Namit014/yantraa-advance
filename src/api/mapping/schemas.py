from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import warnings

# ============================================================
# SOURCE TYPE ENUM
# ============================================================
class SourceType(str, Enum):
    CAD = "CAD"
    BOM = "BOM"
    SCHEMATIC = "SCHEMATIC"
    MANUAL = "MANUAL"
    DATASHEET = "DATASHEET"
    KNOWLEDGE_BASE = "KNOWLEDGE_BASE"
    WEB = "WEB"
    IMAGE = "IMAGE"

class EvidenceReference(BaseModel):
    source_id: str
    source_type: SourceType
    source_file: str
    source_priority: float = 1.0
    source_confidence: float = 1.0
    page_number: Optional[int] = None
    paragraph: Optional[str] = None

# ============================================================
# PIN / PORT MODELS (New Architecture)
# ============================================================
class PinDirection(str, Enum):
    INPUT = "INPUT"
    OUTPUT = "OUTPUT"
    BIDIRECTIONAL = "BIDIRECTIONAL"
    POWER = "POWER"
    GROUND = "GROUND"
    NC = "NC"  # No Connect

class Pin(BaseModel):
    pin_id: str
    name: str
    direction: PinDirection
    protocol: Optional[str] = None  # e.g., PWM, UART_TX, GPIO
    voltage_min: Optional[float] = None
    voltage_max: Optional[float] = None
    current_limit: Optional[float] = None

class Port(BaseModel):
    port_id: str
    name: str
    type: str  # e.g., Power, Data, Motor
    pins: List[Pin] = []
    connector_type: Optional[str] = None  # e.g., JST-XH, M12

class Connector(BaseModel):
    connector_id: str
    type: str
    gender: str  # MALE, FEMALE
    pin_count: int

class Harness(BaseModel):
    harness_id: str
    length_mm: Optional[float] = None
    wire_gauge: Optional[str] = None
    connector_a: Connector
    connector_b: Connector

class ConnectionAudit(BaseModel):
    created_by: str  # Engine that created the edge
    evidence: List[str] = []
    validation_agents: List[str] = []  # Electrical, Mechanical, etc.
    compatibility_score: float = 0.0

class PinConnection(BaseModel):
    id: str
    source_component_id: str
    source_port_id: str
    source_pin_id: str
    target_component_id: str
    target_port_id: str
    target_pin_id: str
    harness: Optional[Harness] = None
    audit: ConnectionAudit

class ComponentNode(BaseModel):
    id: str
    name: str
    canonical_name: Optional[str] = None
    engineering_role: Optional[str] = None
    category: str
    subcategory: Optional[str] = None
    manufacturer: Optional[str] = None
    part_number: Optional[str] = None
    revision: Optional[str] = None

    # Engineering requirements
    power_requirements: Dict[str, Any] = {}
    mechanical_requirements: Dict[str, Any] = {}

    # Connectivity
    ports: List[Port] = []

    # Validation flags
    datasheet_verified: bool = False
    datasheet_source: Optional[str] = None

    # Confidence
    confidence: float = 0.0
    evidence: List[EvidenceReference] = []
    explainability: str = ""
    parent_assembly: Optional[str] = None

class GraphHealth(BaseModel):
    overall_accuracy: float = 100.0
    classification_accuracy: float = 100.0
    connection_accuracy: float = 100.0
    kinematic_accuracy: float = 100.0
    subsystem_accuracy: float = 100.0
    errors: List[str] = []
    warnings: List[str] = []

# ============================================================
# BACKWARD COMPATIBILITY LAYER
# Legacy types kept as deprecated aliases so old code never crashes.
# These map generic concepts to the Protocol-Family architecture.
# ============================================================

class ConnectionType(str, Enum):
    """
    DEPRECATED: Legacy connection classification enum.
    Kept as a backward compatibility layer only.
    All new code should use Protocol-Family routing via CompatibilityMatrixEngine.
    Generic 'SIGNAL' edges are automatically upgraded to UNKNOWN_SIGNAL_PROTOCOL.
    """
    # Legacy semantic verbs (used by ontology.py chain inference)
    POWERS = "powers"
    CONTROLS = "controls"
    DRIVES = "drives"
    TRANSMITS_MOTION_TO = "transmits_motion_to"
    PROVIDES_FEEDBACK_TO = "provides_feedback_to"
    COMMUNICATES_WITH = "communicates_with"
    SUPPORTS = "supports"
    MOUNTED_TO = "mounted_to"
    CONTAINS = "contains"
    BELONGS_TO = "belongs_to"

    # Deprecated generic types - map to UNKNOWN_*_PROTOCOL
    SIGNAL = "UNKNOWN_SIGNAL_PROTOCOL"   # Deprecated: was generic signal link
    POWER = "UNKNOWN_POWER_DOMAIN"       # Deprecated: was generic power link
    CONTROL = "UNKNOWN_CONTROL_PROTOCOL" # Deprecated: was generic control link
    MECHANICAL = "UNKNOWN_MECHANICAL_LINK"  # Deprecated: was generic mechanical link
    DATA = "UNKNOWN_DATA_PROTOCOL"       # Deprecated: was generic data link
    FEEDBACK = "UNKNOWN_FEEDBACK_PROTOCOL"  # Deprecated: was generic feedback link


# Protocol Family constants for routing
SIGNAL_PROTOCOLS = {"PWM", "UART", "UART_TX", "UART_RX", "SPI", "SPI_MOSI", "SPI_MISO", "I2C", "I2C_SDA", "I2C_SCL", "CAN", "CAN_H", "CAN_L", "RS485", "RS485_A", "RS485_B", "ETHERNET", "MODBUS_RTU", "ETHERCAT"}
POWER_PROTOCOLS = {"24V_POWER", "48V_POWER", "12V_POWER", "5V_POWER", "3V3_POWER", "24V_POWER_IN", "48V_POWER_IN", "12V_POWER_IN", "5V_POWER_IN", "3V3_POWER_IN"}
SAFETY_PROTOCOLS = {"STO", "ESTOP_CH1", "ESTOP_CH2", "SAFETY_RELAY_IN", "SAFETY_RELAY_OUT", "SAFETY_IO"}
MOTION_PROTOCOLS = {"ENCODER_A", "ENCODER_B", "ENCODER_Z", "STEP", "DIR", "PWM_OUT", "PWM_IN", "HALL_SENSOR", "RESOLVER_SIN", "RESOLVER_COS"}


class ConnectionEdge(BaseModel):
    """
    DEPRECATED: Legacy component-to-component connection model.
    Kept as a backward compatibility layer only.
    New code must use PinConnection with full Pin-level resolution.
    When loaded, these edges are automatically upgraded via ConnectionEdgeMigrator.
    """
    id: str
    source: str  # component id
    target: str  # component id
    type: ConnectionType = ConnectionType.SIGNAL
    confidence: float = 0.8
    explainability: str = ""
    evidence: List[EvidenceReference] = []

    @property
    def is_legacy(self) -> bool:
        return True


class ConnectionEdgeMigrator:
    """
    Upgrades legacy ConnectionEdge instances to protocol-aware routing.
    Prevents crashes from old SIGNAL/POWER/CONTROL edge types.
    """
    VERB_TO_DOMAIN = {
        "powers": "POWER_DOMAIN",
        "controls": "CONTROL_COMMAND",
        "drives": "MOTION_COMMAND",
        "transmits_motion_to": "MECHANICAL_TRANSMISSION",
        "provides_feedback_to": "FEEDBACK_SIGNAL",
        "communicates_with": "UNKNOWN_SIGNAL_PROTOCOL",
        "UNKNOWN_SIGNAL_PROTOCOL": "UNKNOWN_SIGNAL_PROTOCOL",
        "UNKNOWN_POWER_DOMAIN": "UNKNOWN_POWER_DOMAIN",
        "UNKNOWN_CONTROL_PROTOCOL": "UNKNOWN_CONTROL_PROTOCOL",
        "UNKNOWN_MECHANICAL_LINK": "UNKNOWN_MECHANICAL_LINK",
    }

    @classmethod
    def get_protocol_domain(cls, edge: ConnectionEdge) -> str:
        """Map legacy type to protocol domain string. Never raises KeyError."""
        return cls.VERB_TO_DOMAIN.get(edge.type.value, "UNKNOWN_SIGNAL_PROTOCOL")
