"""API HTTP de consultation (lecture seule).

L'API n'expose JAMAIS d'endpoint d'exécution directe : les commandes
entrent par le bus (`command.requested`) et passent par le Verification
Engine. Ici on ne fait que consulter.

Dépendance optionnelle : pip install 'jabfy-bus[api]'
"""

from __future__ import annotations

from typing import Any

from jabfy_bus.audit.log import AuditLog
from jabfy_bus.core.bus import UniversalJsonBus
from jabfy_bus.core.registry import EntityRegistry


def _require_fastapi() -> Any:
    try:
        import fastapi
    except ImportError as exc:
        raise RuntimeError(
            "FastAPI is required for the API: pip install 'jabfy-bus[api]'"
        ) from exc
    return fastapi


def create_app(
    bus: UniversalJsonBus,
    registry: EntityRegistry,
    audit: AuditLog | None = None,
    allowed_origins: list[str] | None = None,
) -> Any:
    """Construit l'application FastAPI branchée sur le bus."""
    fastapi = _require_fastapi()
    from fastapi.middleware.cors import CORSMiddleware  # noqa: PLC0415 - optionnel

    app = fastapi.FastAPI(title="JABFY Universal JSON Bus", version="1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins or [],
        allow_methods=["GET"],
        allow_headers=["Content-Type"],
        allow_credentials=False,
    )

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {"status": "ok", "entities": len(registry)}

    @app.get("/entities")
    def entities(domain: str | None = None) -> list[dict[str, Any]]:
        return [
            {
                "id": r.entity_id,
                "domain": r.domain,
                "class": r.entity_class,
                "name": r.name,
                "location": r.location,
                "last_value": r.last_value,
                "last_seen": r.last_seen,
                "capabilities": sorted(r.capabilities),
                "seen_count": r.seen_count,
            }
            for r in registry.list(domain=domain)
        ]

    @app.get("/entities/{entity_id}")
    def entity(entity_id: str) -> dict[str, Any]:
        record = registry.get(entity_id)
        if record is None:
            raise fastapi.HTTPException(status_code=404, detail=f"unknown entity '{entity_id}'")
        return {
            "id": record.entity_id,
            "domain": record.domain,
            "class": record.entity_class,
            "last_value": record.last_value,
            "last_seen": record.last_seen,
            "last_message": record.last_message.to_dict() if record.last_message else None,
        }

    @app.get("/bus/history")
    def history(pattern: str = "*", limit: int = 50) -> list[dict[str, Any]]:
        return [m.to_dict() for m in bus.history(pattern=pattern, limit=limit)]

    @app.get("/audit")
    def audit_records(limit: int = 50) -> list[dict[str, Any]]:
        if audit is None:
            return []
        return [r.to_dict() for r in audit.records()[-limit:]]

    @app.get("/audit/verify")
    def audit_verify() -> dict[str, Any]:
        if audit is None:
            return {"verified": None, "records": 0}
        return {"verified": audit.verify(), "records": len(audit)}

    return app
