from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class ConnectionType(str, Enum):
    POWERS = "powers"
    CONTROLS = "controls"
    DRIVES = "drives"
    SUPPORTS = "supports"
    MOUNTED_TO = "mounted_to"
    COMMUNICATES_WITH = "communicates_with"
    PROVIDES_FEEDBACK_TO = "provides_feedback_to"
    TRANSMITS_MOTION_TO = "transmits_motion_to"
    CONTAINS = "contains"
    BELONGS_TO = "belongs_to"

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
    image_region: Optional[str] = None

class ComponentNode(BaseModel):
    id: str
    name: str
    engineering_name: str
    engineering_role: str
    category: str
    canonical_name: Optional[str] = None
    aliases: List[str] = []
    fingerprint_hash: Optional[str] = None
    confidence: float = 0.0
    evidence: List[EvidenceReference] = []
    parent_assembly: Optional[str] = None
    explainability: str = ""

class ConnectionEdge(BaseModel):
    id: str
    source: str
    target: str
    type: ConnectionType
    confidence: float = 0.0
    evidence: List[EvidenceReference] = []
    explainability: str = ""

class Conflict(BaseModel):
    issue_type: str
    description: str
    involved_nodes: List[str]

class GraphHealth(BaseModel):
    overall_accuracy: float = 100.0
    classification_accuracy: float = 100.0
    connection_accuracy: float = 100.0
    kinematic_accuracy: float = 100.0
    subsystem_accuracy: float = 100.0
    errors: List[str] = []
    warnings: List[str] = []
