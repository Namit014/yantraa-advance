from .schemas import PinConnection

class ConnectionAuditEngine:
    """
    Ensures every connection has a full audit trail.
    """
    
    @classmethod
    def print_audit(cls, connection: PinConnection) -> str:
        audit = connection.audit
        return (
            f"Connection ID: {connection.id}\n"
            f"Created By: {audit.created_by}\n"
            f"Evidence: {', '.join(audit.evidence)}\n"
            f"Validation Agents: {', '.join(audit.validation_agents)}\n"
            f"Score: {audit.compatibility_score}\n"
        )
