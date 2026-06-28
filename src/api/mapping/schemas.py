from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

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

class PinDirection(str, Enum):
    INPUT = "INPUT"
    OUTPUT = "OUTPUT"
    BIDIRECTIONAL = "BIDIRECTIONAL"
    POWER = "POWER"
    GROUND = "GROUND"
    NC = "NC" # No Connect

class Pin(BaseModel):
    pin_id: str
    name: str
    direction: PinDirection
    protocol: Optional[str] = None # e.g., PWM, UART_TX, GPIO
    voltage_min: Optional[float] = None
    voltage_max: Optional[float] = None
    current_limit: Optional[float] = None

class Port(BaseModel):
    port_id: str
    name: str
    type: str # e.g., Power, Data, Motor
    pins: List[Pin] = []
    connector_type: Optional[str] = None # e.g., JST-XH, M12

class Connector(BaseModel):
    connector_id: str
    type: str
    gender: str # MALE, FEMALE
    pin_count: int

class Harness(BaseModel):
    harness_id: str
    length_mm: Optional[float] = None
    wire_gauge: Optional[str] = None
    connector_a: Connector
    connector_b: Connector

class ConnectionAudit(BaseModel):
    created_by: str # Engine that created the edge
    evidence: List[str] = []
    validation_agents: List[str] = [] # Electrical, Mechanical, etc.
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
    errors: List[str] = []
    warnings: List[str] = []
