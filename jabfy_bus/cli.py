"""CLI du bus JABFY.

    jabfy-bus demo --steps 10        # scénario motion -> light en simulation
    jabfy-bus validate message.json  # valide un message contre le schéma v1.0
    jabfy-bus audit-verify audit.jsonl
    jabfy-bus serve --config config.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from jabfy_bus import __version__
from jabfy_bus.audit.log import verify_file
from jabfy_bus.core.errors import InvalidMessage
from jabfy_bus.core.message import BusMessage
from jabfy_bus.logging_utils import setup_logging


def cmd_demo(args: argparse.Namespace) -> int:
    from jabfy_bus.simulation.scenarios import run_motion_light_demo  # noqa: PLC0415

    stack = run_motion_light_demo(steps=args.steps, audit_path=args.audit)
    lamp = stack.lamp
    print(f"ticks           : {stack.lab.ticks}")
    print(f"entities        : {len(stack.registry)}")
    print(f"decisions       : {len(stack.engine.decisions)}")
    print(f"executed        : {stack.executor.executed}")
    print(f"lamp state      : {'ON' if lamp.state else 'OFF'}")
    print(f"audit records   : {len(stack.audit)}")
    print(f"audit verified  : {stack.audit.verify()}")
    return 0 if lamp.state else 1


def cmd_validate(args: argparse.Namespace) -> int:
    try:
        data = json.loads(Path(args.file).read_text(encoding="utf-8"))
        BusMessage.from_dict(data)
    except (ValueError, TypeError, KeyError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 1
    except InvalidMessage as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 1
    print("OK: message conforms to bus schema v1.0")
    return 0


def cmd_audit_verify(args: argparse.Namespace) -> int:
    ok = verify_file(args.file)
    print("audit chain: " + ("VALID" if ok else "BROKEN"))
    return 0 if ok else 1


def cmd_serve(args: argparse.Namespace) -> int:
    try:
        import uvicorn  # noqa: PLC0415 - dépendance optionnelle
    except ImportError:
        print("uvicorn required: pip install 'jabfy-bus[api]'", file=sys.stderr)
        return 1
    from jabfy_bus.api.app import create_app  # noqa: PLC0415
    from jabfy_bus.api.ws import register_ws_routes  # noqa: PLC0415
    from jabfy_bus.audit.log import AuditLog  # noqa: PLC0415
    from jabfy_bus.config import DEFAULT_ALLOWED_ORIGINS, load_config  # noqa: PLC0415
    from jabfy_bus.core.bus import UniversalJsonBus  # noqa: PLC0415
    from jabfy_bus.core.registry import EntityRegistry  # noqa: PLC0415

    config = load_config(args.config) if args.config else None
    bus = UniversalJsonBus(history_size=config.history_size if config else 500)
    registry = EntityRegistry()
    registry.attach(bus)
    audit = AuditLog(config.audit_path if config else None)
    audit.attach(bus)

    allowed_origins = config.allowed_origins if config else list(DEFAULT_ALLOWED_ORIGINS)
    app = create_app(bus, registry, audit, allowed_origins=allowed_origins)
    register_ws_routes(app, bus, allowed_origins=allowed_origins)
    host = (
        config.api_host
        if config
        else os.getenv("JABFY_BUS_HOST", "127.0.0.1")
    )
    port = config.api_port if config else int(os.getenv("JABFY_BUS_PORT", "8080"))
    uvicorn.run(app, host=host, port=port)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="jabfy-bus", description="JABFY Universal JSON Bus")
    parser.add_argument("--version", action="version", version=f"jabfy-bus {__version__}")
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument("--log-json", action="store_true", help="logs au format JSON lines")

    sub = parser.add_subparsers(dest="command", required=True)

    demo = sub.add_parser("demo", help="scénario motion -> light en simulation")
    demo.add_argument("--steps", type=int, default=10)
    demo.add_argument("--audit", default=None, help="chemin du journal d'audit JSONL")
    demo.set_defaults(func=cmd_demo)

    validate = sub.add_parser("validate", help="valide un message JSON contre le schéma v1.0")
    validate.add_argument("file")
    validate.set_defaults(func=cmd_validate)

    audit_verify = sub.add_parser("audit-verify", help="vérifie l'intégrité d'un journal d'audit")
    audit_verify.add_argument("file")
    audit_verify.set_defaults(func=cmd_audit_verify)

    serve = sub.add_parser("serve", help="lance l'API HTTP/WebSocket")
    serve.add_argument("--config", default=None)
    serve.set_defaults(func=cmd_serve)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    setup_logging(args.log_level, json_format=args.log_json)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
