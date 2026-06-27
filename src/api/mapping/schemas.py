from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class ConnectionType(str, Enum):
    MECHANICAL = "MECHANICAL"
    POWER = "POWER"
    SIGNAL = "SIGNAL"
    MOTION = "MOTION"
    THERMAL = "THERMAL"
    PNEUMATIC = "PNEUMATIC"
    HYDRAULIC = "HYDRAULIC"
    COMMUNICATION = "COMMUNICATION"
    SAFETY = "SAFETY"

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
    canonical_name: Optional[str] = None
    category: str
    aliases: List[str] = []
    fingerprint_hash: Optional[str] = None
    confidence: float = 0.0
    evidence: List[EvidenceReference] = []
    parent_id: Optional[str] = None
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
    score: int = 100
    errors: List[str] = []
    warnings: List[str] = []
