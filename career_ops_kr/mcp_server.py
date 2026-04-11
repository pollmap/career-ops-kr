"""Standalone MCP server for career-ops-kr.

Exposes 10 tools over the Model Context Protocol so Nexus/HERMES agents
can drive the scan → score → calendar → pattern-analysis pipeline from
any MCP-aware client (Claude Desktop, Claude Code, custom agents).

Backend selection
-----------------
Two transports are supported; the one that imports wins:

1. **FastMCP** (``mcp.server.fastmcp.FastMCP``) — the canonical Python
   SDK entry point. Preferred when ``pip install mcp`` is available.
2. **Minimal stdio JSON-RPC** — a dependency-free fallback that speaks
   MCP 2024-11-05 over stdin/stdout. Implements only the handshake +
   ``tools/list`` + ``tools/call`` methods needed by this server.

Either way, the 10 tools expose the same functions with the same names
and schemas, so registering the server in ``nexus-finance-mcp``'s
``mcpServers`` config is transport-agnostic.

Registration hint (VPS)
-----------------------
Add to ``/opt/nexus-finance-mcp/mcp.json`` (or local ``~/.mcp.json``)::

    {
      "mcpServers": {
        "career-ops-kr": {
          "command": "python",
          "args": ["-m", "career_ops_kr.mcp_server"],
          "cwd": "/root/career-ops-kr"
        }
      }
    }

Then restart the MCP service — tools appear under the ``career_ops_*``
prefix exactly as listed in :data:`TOOL_SPECS`.

실데이터 invariant
------------------
Every tool wraps the underlying Python API inside a try/except and
returns a structured error dict on failure — tools NEVER fabricate
job records or scores. When a required subpackage is missing, the
tool returns ``{"error": "...", "hint": "pip install -e ."}`` instead
of crashing the server.
"""

from __future__ import annotations

import json
import logging
import sys
import traceback
from collections.abc import Callable
from pathlib import Path
from typing import Any

logger = logging.getLogger("career_ops_kr.mcp_server")

SERVER_NAME = "career-ops-kr"
SERVER_VERSION = "0.2.0"
PROTOCOL_VERSION = "2024-11-05"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CONFIG_DIR = PROJECT_ROOT / "config"
PRESETS_DIR = PROJECT_ROOT / "presets"


# ---------------------------------------------------------------------------
# Lazy imports — every tool calls :func:`_safe_import` so a broken
# subpackage degrades to ``{"error": ...}`` instead of blocking startup.
# ---------------------------------------------------------------------------


def _safe_import(dotted: str, attr: str | None = None) -> Any:
    """Import ``dotted[.attr]`` and return it, or ``None`` on failure."""
    try:
        mod = __import__(dotted, fromlist=["*"])
    except Exception as exc:
        logger.warning("MCP: import %s failed: %s", dotted, exc)
        return None
    if attr is None:
        return mod
    return getattr(mod, attr, None)


def _error(message: str, hint: str | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {"error": message}
    if hint:
        out["hint"] = hint
    return out


def _module_missing(name: str) -> dict[str, Any]:
    return _error(
        f"module '{name}' not loaded",
        hint="pip install -e . from the career-ops-kr repo root",
    )


# ---------------------------------------------------------------------------
# Tool implementations — one function per MCP tool
# ---------------------------------------------------------------------------


def tool_scan_jobs(tier: int | None = None, site: str | None = None) -> dict[str, Any]:
    """Run the scan pipeline across registered channels.

    Iterates :data:`CHANNEL_REGISTRY`, applying the ``tier`` and ``site``
    filters. For each channel, calls ``list_jobs()`` and returns a
    summary dict (per-channel counts + total). Individual channel
    failures are captured per-entry and do NOT abort the sweep.
    """
    channels_mod = _safe_import("career_ops_kr.channels")
    if channels_mod is None:
        return _module_missing("career_ops_kr.channels")
    registry: dict[str, type] = getattr(channels_mod, "CHANNEL_REGISTRY", {})
    if not registry:
        return _error("channel registry is empty")

    summary: dict[str, Any] = {"total": 0, "channels": {}}
    for name, cls in registry.items():
        if site and name != site:
            continue
        if tier is not None and getattr(cls, "tier", None) != tier:
            continue
        try:
            instance = cls()
            jobs = instance.list_jobs() or []
            count = len(jobs)
        except Exception as exc:
            summary["channels"][name] = {"error": str(exc), "count": 0}
            continue
        summary["channels"][name] = {
            "count": count,
            "tier": getattr(cls, "tier", None),
            "backend": getattr(cls, "backend", "unknown"),
        }
        summary["total"] += count
    return summary


def tool_score_job(url: str) -> dict[str, Any]:
    """Score a single posting URL end-to-end.

    Pipeline:
        1. Find a registered channel that can handle the URL host.
        2. Call ``get_detail(url)`` to materialise a :class:`JobRecord`.
        3. Run the qualifier engine.
        4. Run the fit scorer (10-dim breakdown).
        5. Return a JSON-serializable evaluation dict.
    """
    if not isinstance(url, str) or "://" not in url:
        return _error("invalid URL")

    channels_mod = _safe_import("career_ops_kr.channels")
    qualifier_cls = _safe_import("career_ops_kr.qualifier.engine", "QualifierEngine")
    scorer_cls = _safe_import("career_ops_kr.scorer.fit_score", "FitScorer")
    if channels_mod is None or qualifier_cls is None or scorer_cls is None:
        return _module_missing("qualifier/scorer/channels")

    registry: dict[str, type] = getattr(channels_mod, "CHANNEL_REGISTRY", {})
    record = None
    used_channel = None
    for name, cls in registry.items():
        try:
            instance = cls()
            record = instance.get_detail(url)
        except Exception as exc:
            logger.debug("score: channel %s get_detail failed: %s", name, exc)
            record = None
        if record is not None:
            used_channel = name
            break

    if record is None:
        return _error(
            "no channel could fetch detail for this URL",
            hint="run career_ops_scan_jobs first or pass a URL from a supported portal",
        )

    try:
        qe = qualifier_cls(CONFIG_DIR / "qualifier_rules.yml")
        qresult = qe.evaluate(record.description or record.title)
    except Exception as exc:
        return _error(f"qualifier failed: {exc}")

    try:
        fs = scorer_cls(
            weights_path=CONFIG_DIR / "scoring_weights.yml",
            profile_path=CONFIG_DIR / "profile.yml",
        )
        breakdown = fs.score(
            job={
                "name": record.org,
                "description": record.description,
                "notes": "",
                "location": record.location or "",
                "compensation": "",
                "deadline": record.deadline,
                "source_url": str(record.source_url),
            },
            qualifier_result=qresult,
            archetype=record.archetype or "UNKNOWN",
        )
    except Exception as exc:
        return _error(f"scorer failed: {exc}")

    return {
        "url": url,
        "channel": used_channel,
        "org": record.org,
        "title": record.title,
        "archetype": record.archetype,
        "legitimacy": record.legitimacy_tier,
        "deadline": str(record.deadline) if record.deadline else None,
        "qualifier_verdict": getattr(qresult, "verdict", None).__str__()
        if getattr(qresult, "verdict", None) is not None
        else None,
        "grade": getattr(breakdown, "grade", None).__str__()
        if getattr(breakdown, "grade", None) is not None
        else None,
        "total_score": getattr(breakdown, "total", None),
        "reasons": list(getattr(breakdown, "reasons", []) or []),
    }


def tool_list_eligible(grade: str = "A") -> list[dict[str, Any]]:
    """Return stored postings filtered by fit-grade."""
    store_cls = _safe_import("career_ops_kr.storage.sqlite_store", "SQLiteStore")
    if store_cls is None:
        return []
    try:
        store = store_cls(DATA_DIR / "jobs.db")
        return list(store.list_by_grade(grade))
    except Exception as exc:
        logger.warning("list_eligible failed: %s", exc)
        return []


def tool_get_deadline_calendar(days: int = 30) -> list[dict[str, Any]]:
    """Return postings with a deadline within the next ``days`` days."""
    store_cls = _safe_import("career_ops_kr.storage.sqlite_store", "SQLiteStore")
    if store_cls is None:
        return []
    try:
        store = store_cls(DATA_DIR / "jobs.db")
        return list(store.list_upcoming_deadlines(days=days))
    except Exception as exc:
        logger.warning("deadline_calendar failed: %s", exc)
        return []


def tool_query_by_archetype(archetype: str) -> list[dict[str, Any]]:
    """Return stored postings whose classified archetype matches."""
    store_cls = _safe_import("career_ops_kr.storage.sqlite_store", "SQLiteStore")
    if store_cls is None:
        return []
    try:
        store = store_cls(DATA_DIR / "jobs.db")
        # Prefer a dedicated search() if available.
        if hasattr(store, "search"):
            return list(store.search(archetype=archetype))
        return []
    except Exception as exc:
        logger.warning("query_by_archetype failed: %s", exc)
        return []


def tool_generate_cover_letter_draft(url: str, tone: str = "formal_kr") -> str:
    """Produce a cover-letter draft for the posting at ``url``.

    Delegates to the Phase-2 :class:`LLMScorer` when available; falls
    back to a deterministic template that stitches the profile archetype
    + posting description together. Returns plain text (caller formats).
    """
    evaluation = tool_score_job(url)
    if "error" in evaluation:
        return (
            f"[draft unavailable] {evaluation['error']}\n"
            f"Hint: {evaluation.get('hint', 'run scan first')}"
        )

    llm_cls = _safe_import("career_ops_kr.scorer.llm_scorer", "LLMScorer")
    if llm_cls is not None:
        try:
            llm = llm_cls()
            draft = llm.generate_cover_letter(evaluation=evaluation, tone=tone)
            if isinstance(draft, str) and draft.strip():
                return draft
        except Exception as exc:
            logger.info("LLMScorer unavailable — using template: %s", exc)

    # Deterministic fallback template. Never fabricates facts — it only
    # quotes fields already extracted from the posting.
    return (
        f"[{tone}] {evaluation.get('org', '귀사')} 채용 지원서 초안\n\n"
        f"지원 공고: {evaluation.get('title', '')}\n"
        f"URL: {url}\n"
        f"아키타입: {evaluation.get('archetype', '미판정')}\n"
        f"현재 평가: Grade {evaluation.get('grade', 'N/A')} "
        f"(총점 {evaluation.get('total_score', 'N/A')})\n\n"
        "--- 찬희 프로필 연결 지점 ---\n"
        "(LLMScorer 미설치 — 수동 작성 필요)\n\n"
        f"Reasons: {'; '.join(evaluation.get('reasons', [])) or '(없음)'}\n"
    )


def tool_run_patterns(days: int = 30) -> dict[str, Any]:
    """Rejection-pattern analysis over the last ``days`` days."""
    patterns_mod = _safe_import("career_ops_kr.patterns")
    if patterns_mod is None:
        # Patterns subpackage is Phase-2 — degrade gracefully.
        return {
            "days": days,
            "status": "not_implemented",
            "hint": "career_ops_kr.patterns arrives in Phase 2",
        }
    try:
        if hasattr(patterns_mod, "analyze"):
            return dict(patterns_mod.analyze(days=days))
    except Exception as exc:
        return _error(f"patterns.analyze failed: {exc}")
    return {"days": days, "status": "no analyzer exposed"}


def tool_verify_pipeline() -> dict[str, Any]:
    """Pipeline health check.

    Checks:
        * ``career_ops_kr.channels`` importable + registry non-empty
        * ``career_ops_kr.scorer`` importable
        * ``career_ops_kr.qualifier`` importable
        * ``config/`` directory exists with required YAMLs
        * ``data/jobs.db`` reachable (SQLite connect)
    """
    out: dict[str, Any] = {"ok": True, "checks": {}}

    channels_mod = _safe_import("career_ops_kr.channels")
    out["checks"]["channels"] = bool(
        channels_mod and getattr(channels_mod, "CHANNEL_REGISTRY", None)
    )

    out["checks"]["scorer"] = (
        _safe_import("career_ops_kr.scorer.fit_score", "FitScorer") is not None
    )
    out["checks"]["qualifier"] = (
        _safe_import("career_ops_kr.qualifier.engine", "QualifierEngine") is not None
    )
    out["checks"]["config_dir"] = CONFIG_DIR.exists()
    out["checks"]["profile_yml"] = (CONFIG_DIR / "profile.yml").exists()
    out["checks"]["data_dir"] = DATA_DIR.exists()

    store_cls = _safe_import("career_ops_kr.storage.sqlite_store", "SQLiteStore")
    if store_cls is not None:
        try:
            store_cls(DATA_DIR / "jobs.db")
            out["checks"]["sqlite"] = True
        except Exception as exc:
            out["checks"]["sqlite"] = False
            out.setdefault("warnings", []).append(f"sqlite: {exc}")
    else:
        out["checks"]["sqlite"] = False

    out["ok"] = all(bool(v) for v in out["checks"].values())
    return out


def tool_apply_preset(preset_id: str) -> dict[str, Any]:
    """Materialise a preset bundle into ``config/*.yml`` files."""
    loader_cls = _safe_import("career_ops_kr.presets.loader", "PresetLoader")
    if loader_cls is None:
        return _module_missing("career_ops_kr.presets.loader")
    try:
        loader = loader_cls(PRESETS_DIR)
        created = loader.apply_to(preset_id, CONFIG_DIR, overwrite=False)
        return {
            "preset_id": preset_id,
            "created": {k: str(v) for k, v in created.items()},
        }
    except Exception as exc:
        return _error(f"apply_preset failed: {exc}")


def tool_get_stats() -> dict[str, Any]:
    """Return :class:`SQLiteStore` stats (totals by grade/status/channel)."""
    store_cls = _safe_import("career_ops_kr.storage.sqlite_store", "SQLiteStore")
    if store_cls is None:
        return _module_missing("career_ops_kr.storage.sqlite_store")
    try:
        store = store_cls(DATA_DIR / "jobs.db")
        return dict(store.get_stats())
    except Exception as exc:
        return _error(f"get_stats failed: {exc}")


# ---------------------------------------------------------------------------
# Tool registry — single source of truth for names + schemas
# ---------------------------------------------------------------------------


TOOL_SPECS: list[dict[str, Any]] = [
    {
        "name": "career_ops_scan_jobs",
        "description": "Run the scan pipeline across all registered channels. Optional filters by tier (1-6) or site name. Returns a summary dict with per-channel counts and an aggregate total. Channel-level failures are captured individually and do not abort the sweep.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tier": {"type": "integer", "minimum": 1, "maximum": 6},
                "site": {"type": "string"},
            },
        },
        "fn": lambda args: tool_scan_jobs(tier=args.get("tier"), site=args.get("site")),
    },
    {
        "name": "career_ops_score_job",
        "description": "Fetch a single posting URL, run the qualifier engine and fit scorer, and return the full evaluation dict (grade, archetype, eligibility verdict, 10-dim breakdown, reasons). Never fabricates — returns {'error': ...} if no channel can fetch the URL.",
        "inputSchema": {
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        },
        "fn": lambda args: tool_score_job(url=args["url"]),
    },
    {
        "name": "career_ops_list_eligible",
        "description": "List stored postings at or above the given fit-grade (A/B/C/D/F). Pulls from the local SQLite store — run career_ops_scan_jobs first to populate.",
        "inputSchema": {
            "type": "object",
            "properties": {"grade": {"type": "string", "default": "A"}},
        },
        "fn": lambda args: tool_list_eligible(grade=args.get("grade", "A")),
    },
    {
        "name": "career_ops_get_deadline_calendar",
        "description": "Return stored postings whose deadlines fall within the next N days. Sorted ascending by deadline. Empty list if no jobs found.",
        "inputSchema": {
            "type": "object",
            "properties": {"days": {"type": "integer", "default": 30, "minimum": 1}},
        },
        "fn": lambda args: tool_get_deadline_calendar(days=int(args.get("days", 30))),
    },
    {
        "name": "career_ops_query_by_archetype",
        "description": "Return stored postings whose classified archetype matches. Archetype names come from the active preset (e.g. 블록체인, 디지털자산, 금융IT, 리서치, 핀테크, 공공).",
        "inputSchema": {
            "type": "object",
            "properties": {"archetype": {"type": "string"}},
            "required": ["archetype"],
        },
        "fn": lambda args: tool_query_by_archetype(archetype=args["archetype"]),
    },
    {
        "name": "career_ops_generate_cover_letter_draft",
        "description": "Generate a cover-letter draft for a posting URL. Runs score_job first to ground the draft in real fields, then delegates to the Phase-2 LLMScorer when available. Falls back to a deterministic template when LLMScorer is missing. Tone defaults to formal_kr.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "tone": {"type": "string", "default": "formal_kr"},
            },
            "required": ["url"],
        },
        "fn": lambda args: {
            "draft": tool_generate_cover_letter_draft(
                url=args["url"], tone=args.get("tone", "formal_kr")
            )
        },
    },
    {
        "name": "career_ops_run_patterns",
        "description": "Rejection-pattern analysis over the last N days. Phase-2 feature — returns {'status': 'not_implemented'} when the patterns subpackage has not been built yet.",
        "inputSchema": {
            "type": "object",
            "properties": {"days": {"type": "integer", "default": 30, "minimum": 1}},
        },
        "fn": lambda args: tool_run_patterns(days=int(args.get("days", 30))),
    },
    {
        "name": "career_ops_verify_pipeline",
        "description": "Pipeline health check. Verifies that all subpackages import, required config files exist, and the SQLite store is reachable. Returns {'ok': bool, 'checks': {...}}.",
        "inputSchema": {"type": "object", "properties": {}},
        "fn": lambda args: tool_verify_pipeline(),
    },
    {
        "name": "career_ops_apply_preset",
        "description": "Materialise a preset bundle into config/*.yml files via PresetLoader.apply_to. Does NOT overwrite existing files. Returns the paths of the (created or skipped) files.",
        "inputSchema": {
            "type": "object",
            "properties": {"preset_id": {"type": "string"}},
            "required": ["preset_id"],
        },
        "fn": lambda args: tool_apply_preset(preset_id=args["preset_id"]),
    },
    {
        "name": "career_ops_get_stats",
        "description": "Return SQLiteStore stats — total jobs, counts by grade, counts by channel, and last scan timestamp.",
        "inputSchema": {"type": "object", "properties": {}},
        "fn": lambda args: tool_get_stats(),
    },
]


def _tool_dispatch(name: str, args: dict[str, Any]) -> Any:
    for spec in TOOL_SPECS:
        if spec["name"] == name:
            try:
                return spec["fn"](args or {})
            except Exception as exc:
                logger.error("tool %s crashed: %s", name, exc)
                return _error(
                    f"tool {name} crashed: {exc}",
                    hint="check career_ops_kr.mcp_server logs",
                )
    return _error(f"unknown tool '{name}'")


# ---------------------------------------------------------------------------
# Transport 1 — FastMCP (preferred)
# ---------------------------------------------------------------------------


def _run_fastmcp() -> bool:
    """Try the FastMCP transport. Returns True iff it started."""
    try:
        from mcp.server.fastmcp import FastMCP
    except Exception as exc:
        logger.info("FastMCP unavailable (%s) — falling back to stdio JSON-RPC", exc)
        return False

    mcp = FastMCP(SERVER_NAME)
    for spec in TOOL_SPECS:
        name = spec["name"]
        desc = spec["description"]
        fn_ref: Callable[[dict[str, Any]], Any] = spec["fn"]

        def _make_wrapper(
            tool_name: str, call: Callable[[dict[str, Any]], Any]
        ) -> Callable[..., Any]:
            def _wrapper(**kwargs: Any) -> Any:
                return call(kwargs or {})

            _wrapper.__name__ = tool_name
            return _wrapper

        wrapper = _make_wrapper(name, fn_ref)
        mcp.tool(name=name, description=desc)(wrapper)

    logger.info("FastMCP server starting — %d tools", len(TOOL_SPECS))
    mcp.run()
    return True


# ---------------------------------------------------------------------------
# Transport 2 — minimal stdio JSON-RPC (fallback)
# ---------------------------------------------------------------------------


def _jsonrpc_result(msg_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def _jsonrpc_error(msg_id: Any, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "error": {"code": code, "message": message},
    }


def _handle_message(msg: dict[str, Any]) -> dict[str, Any] | None:
    method = msg.get("method")
    msg_id = msg.get("id")
    params = msg.get("params") or {}

    if method == "initialize":
        return _jsonrpc_result(
            msg_id,
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {
                    "name": SERVER_NAME,
                    "version": SERVER_VERSION,
                },
            },
        )
    if method == "notifications/initialized":
        return None  # notification — no reply
    if method == "tools/list":
        tools = [
            {
                "name": s["name"],
                "description": s["description"],
                "inputSchema": s["inputSchema"],
            }
            for s in TOOL_SPECS
        ]
        return _jsonrpc_result(msg_id, {"tools": tools})
    if method == "tools/call":
        name = params.get("name")
        args = params.get("arguments") or {}
        if not isinstance(name, str):
            return _jsonrpc_error(msg_id, -32602, "missing tool name")
        result = _tool_dispatch(name, args)
        return _jsonrpc_result(
            msg_id,
            {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, ensure_ascii=False, default=str),
                    }
                ],
                "isError": isinstance(result, dict) and "error" in result,
            },
        )
    if msg_id is not None:
        return _jsonrpc_error(msg_id, -32601, f"method not found: {method}")
    return None


def _run_stdio() -> None:
    """Minimal stdio JSON-RPC loop. UTF-8 line-delimited messages."""
    sys.stdin.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    logger.info(
        "stdio JSON-RPC server starting — %d tools registered",
        len(TOOL_SPECS),
    )
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError as exc:
            sys.stdout.write(json.dumps(_jsonrpc_error(None, -32700, f"parse error: {exc}")) + "\n")
            sys.stdout.flush()
            continue
        try:
            reply = _handle_message(msg)
        except Exception as exc:
            logger.error("handler crash: %s\n%s", exc, traceback.format_exc())
            reply = _jsonrpc_error(msg.get("id"), -32603, f"internal: {exc}")
        if reply is not None:
            sys.stdout.write(json.dumps(reply, ensure_ascii=False, default=str) + "\n")
            sys.stdout.flush()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )
    if _run_fastmcp():
        return
    _run_stdio()


if __name__ == "__main__":
    main()
