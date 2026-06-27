from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class ConnectionType(str, Enum):
    MECHANICAL_ATTACHMENT = "MECHANICAL_ATTACHMENT"
    POWER = "POWER"
    SIGNAL = "SIGNAL"
    FLUID = "FLUID"
    MOTION = "MOTION"
    THERMAL = "THERMAL"

class SourceType(str, Enum):
    CAD = "CAD"
    BOM = "BOM"
    MANUAL = "MANUAL"
    DATASHEET = "DATASHEET"
    WEB = "WEB"

class EvidenceReference(BaseModel):
    source_type: SourceType
    source_file: str
    page_number: Optional[int] = None
    paragraph: Optional[str] = None
    image_region: Optional[str] = None
    cad_assembly_path: Optional[str] = None
    confidence: float = 1.0

class ExplainabilityRecord(BaseModel):
    source: str
    target: str
    relationship: str
    why: List[str]

class ComponentNode(BaseModel):
    id: str
    name: str
    canonical_name: Optional[str] = None
    category: str
    aliases: List[str] = []
    fingerprint_hash: Optional[str] = None
    confidence: float = 0.0
    evidence: List[EvidenceReference] = []

class ConnectionEdge(BaseModel):
    id: str
    source_id: str
    target_id: str
    type: ConnectionType
    relation_name: str
    confidence: float = 0.0
    evidence: List[EvidenceReference] = []
    explanation: Optional[ExplainabilityRecord] = None

class Conflict(BaseModel):
    issue_type: str
    description: str
    involved_nodes: List[str]

class ValidationReport(BaseModel):
    missing_components: List[str] = []
    duplicate_components: List[str] = []
    orphan_components: List[str] = []
    unresolved_aliases: List[str] = []
    conflicts: List[Conflict] = []
