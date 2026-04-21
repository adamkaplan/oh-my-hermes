"""
omh_delegate — hardened wrapper around delegate_task.

v0 implements pure subagent-persists with no rescue branch.

Per .omh/research/ralplan-omh-delegate/round2-planner.md §3 and CONSENSUS.md.

Behavior:
  1. Discover project root via .omh/ walk-up from cwd (mirrors git's .git
     discovery), falling back to cwd. (Round 2 W4)
  2. Compute deterministic expected_output_path under
     .omh/research/{mode}/{phase}[-r{round}][-{slug}]-{ts}.md
  3. mkdir parents (inline in v0; A1/A2 extraction lands in v1).
  4. Write {id}.dispatched.json breadcrumb (atomic, append-only — no RMW).
  5. Inject brutal-prose <<<EXPECTED_OUTPUT_PATH>>> contract appended to goal.
  6. Call delegate_task(goal=augmented_goal, **passthrough). Do NOT parse return.
  7. Check Path(expected_output_path).is_file().
  8. Write {id}.completed.json breadcrumb (separate file, single-write).
  9. Return {ok, ok_strict, path, id, file_present, contract_satisfied,
            recovered_by_wrapper, raw}.

Out of scope for v0: rescue branch, classifier, batch dispatch, recovery CLI,
session_id capture, omh_io extraction, tools/delegate_tool.py registration.

AC-1: ok_strict = (ok is True). Callers that need a hard pass/fail should
      check ok_strict, not ok. v1.B may make ok tri-state ("degraded"),
      and Python truthiness would treat that as truthy. ok_strict is
      forward-compatible.

AC-2: cross-fs os.replace failure (FUSE/Docker volumes) is not handled in
      v0; see plugin README §"Known limitations" for the v2 deferral.
"""

import hashlib
import json
import logging
import os
import secrets
import stat
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_SCHEMA_VERSION = 1


# ---------------------------------------------------------------------------
# Helpers (inlined in v0; v1.A1/A2 will extract to omh_io)
# ---------------------------------------------------------------------------


def _discover_project_root(start: Path | None = None) -> Path:
    """Walk up from start (or cwd) looking for a .omh/ marker.

    Mirrors git's .git discovery. Returns the directory CONTAINING .omh/.
    Falls back to start (or cwd) if no .omh/ found.
    """
    cur = (start or Path.cwd()).resolve()
    for candidate in [cur, *cur.parents]:
        if (candidate / ".omh").is_dir():
            return candidate
    return cur


def _atomic_write_text(path: Path, content: str) -> None:
    """Write content to path atomically (tmp → fsync → os.replace).

    Mirrors omh_state._atomic_write. AC-2: cross-fs (e.g. .omh/ on a
    different filesystem from $TMPDIR) failures will surface as OSError
    from os.replace; v0 does not auto-detect or fall back.
    """
    tmp = path.with_suffix(path.suffix + f".tmp.{uuid.uuid4().hex}")
    try:
        fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
                     stat.S_IRUSR | stat.S_IWUSR)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass
        raise


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _now_compact() -> str:
    """UTC timestamp for filenames: YYYYMMDDTHHMMSSZ."""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


# ---------------------------------------------------------------------------
# Path / id computation
# ---------------------------------------------------------------------------


def _compute_expected_path(
    project_root: Path,
    mode: str,
    phase: str,
    round: int | None,
    slug: str | None,
    ts: str,
) -> Path:
    """.omh/research/{mode}/{phase}[-r{round}][-{slug}]-{ts}.md (absolute)."""
    parts = [phase]
    if round is not None:
        parts.append(f"r{round}")
    if slug:
        parts.append(slug)
    parts.append(ts)
    filename = "-".join(parts) + ".md"
    return (project_root / ".omh" / "research" / mode / filename).resolve()


def _compute_id(mode: str, phase: str, round: int | None, ts: str) -> str:
    """{mode}-{phase}[-r{round}]-{ts}-{rand4}."""
    parts = [mode, phase]
    if round is not None:
        parts.append(f"r{round}")
    parts.append(ts)
    parts.append(secrets.token_hex(2))  # 4 hex chars
    return "-".join(parts)


# ---------------------------------------------------------------------------
# Goal injection
# ---------------------------------------------------------------------------


_CONTRACT_TEMPLATE = """

---

<<<EXPECTED_OUTPUT_PATH>>>
{expected_path}
<<<END_EXPECTED_OUTPUT_PATH>>>

CRITICAL contract — your final action MUST be exactly:

  write_file('{expected_path}', <full content as markdown>)

And your return value MUST be exactly the string:

  {expected_path}

The file you write IS the deliverable. The path is the receipt. Do not
summarize or paraphrase the deliverable in your return value. Do not write
to any other path. Do not URL-encode, expand ~, or change the extension.
"""


def _inject_contract(goal: str, expected_path: Path) -> str:
    """Append the brutal-prose contract to the goal text (M4: appended)."""
    return goal.rstrip() + _CONTRACT_TEMPLATE.format(expected_path=str(expected_path))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def omh_delegate(
    *,
    role: str,
    goal: str,
    mode: str,
    phase: str,
    context: str = "",
    round: int | None = None,
    slug: str | None = None,
    delegate_fn: Any = None,
    project_root: Path | None = None,
    **passthrough,
) -> dict:
    """Hardened wrapper around delegate_task.

    Required:
      role, goal, mode, phase

    Optional:
      context     — passed through to delegate_task
      round       — int, included in path/id when set
      slug        — short string, included in path
      project_root — override for path discovery (default: walk up for .omh/)
      delegate_fn  — injection point for delegate_task (default: import)
      **passthrough — forwarded to delegate_task (toolsets, max_iterations, etc.)

    Returns:
      {ok, ok_strict, path, id, file_present, contract_satisfied,
       recovered_by_wrapper, raw}

    AC-1: callers needing hard pass/fail should check `ok_strict`, not `ok`.
    """
    # Resolve delegate_fn lazily so tests can monkeypatch.
    if delegate_fn is None:
        from tools.delegate_tool import delegate_task as delegate_fn  # type: ignore

    # 1. Discover project root.
    root = (project_root.resolve() if project_root else _discover_project_root())

    # 2. Compute paths and id.
    ts = _now_compact()
    expected_path = _compute_expected_path(root, mode, phase, round, slug, ts)
    dispatch_id = _compute_id(mode, phase, round, ts)

    # 3. mkdir parents for both research artifact dir and breadcrumb dir.
    expected_path.parent.mkdir(parents=True, exist_ok=True)
    breadcrumb_dir = (root / ".omh" / "state" / "dispatched").resolve()
    breadcrumb_dir.mkdir(parents=True, exist_ok=True)

    # 4. Write dispatched breadcrumb (atomic, append-only).
    goal_bytes = goal.encode("utf-8")
    dispatched = {
        "_meta": {
            "written_at": _now_iso(),
            "schema_version": _SCHEMA_VERSION,
            "kind": "dispatch",
        },
        "id": dispatch_id,
        "mode": mode,
        "phase": phase,
        "round": round,
        "slug": slug,
        "role": role,
        "dispatched_at": _now_iso(),
        "expected_output_path": str(expected_path),
        "goal_sha256": hashlib.sha256(goal_bytes).hexdigest(),
        "goal_bytes": len(goal_bytes),
        "context_bytes": len(context.encode("utf-8")),
    }
    dispatched_path = breadcrumb_dir / f"{dispatch_id}.dispatched.json"
    _atomic_write_text(dispatched_path, json.dumps(dispatched, indent=2))

    # 5. Inject contract.
    augmented_goal = _inject_contract(goal, expected_path)

    # 6. Dispatch (do NOT parse the return).
    raw_return: Any = None
    error: str | None = None
    try:
        raw_return = delegate_fn(goal=augmented_goal, context=context, **passthrough)
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        # Write completion breadcrumb with error, then re-raise.
        _write_completion_breadcrumb(
            breadcrumb_dir=breadcrumb_dir,
            dispatch_id=dispatch_id,
            file_present=False,
            contract_satisfied=False,
            recovered_by_wrapper=False,
            bytes_=0,
            raw_return=None,
            error=error,
        )
        _emit_warning(dispatch_id, expected_path, error="exception", detail=str(exc))
        raise

    # 7. Verify file exists.
    file_present = expected_path.is_file()
    bytes_ = expected_path.stat().st_size if file_present else 0

    # 8. Write completion breadcrumb (single write, append-only).
    _write_completion_breadcrumb(
        breadcrumb_dir=breadcrumb_dir,
        dispatch_id=dispatch_id,
        file_present=file_present,
        contract_satisfied=file_present,  # v0: identity. v1.B may differ.
        recovered_by_wrapper=False,        # always False in v0.
        bytes_=bytes_,
        raw_return=raw_return,
        error=None,
    )

    # 9. W5: stderr warning on any non-clean dispatch.
    if not file_present:
        _emit_warning(dispatch_id, expected_path, error="contract_violation",
                      detail="file not present at expected path after dispatch")

    ok = file_present
    return {
        "ok": ok,
        "ok_strict": (ok is True),  # AC-1
        "path": str(expected_path),
        "id": dispatch_id,
        "file_present": file_present,
        "contract_satisfied": file_present,
        "recovered_by_wrapper": False,
        "raw": raw_return,
    }


# ---------------------------------------------------------------------------
# Internal: completion breadcrumb writer
# ---------------------------------------------------------------------------


_RAW_RETURN_CAP_BYTES = 8192


def _summarize_raw_return(raw: Any) -> tuple[str, str]:
    """Return (raw_return_kind, serialized_raw_capped_at_8KB).

    Kind is 'string' | 'dict' | 'none' | 'other'. Serialized form is a
    string suitable for JSON storage; truncated with marker if over cap.
    """
    if raw is None:
        return ("none", "")
    if isinstance(raw, str):
        kind = "string"
        text = raw
    elif isinstance(raw, dict):
        kind = "dict"
        try:
            text = json.dumps(raw, indent=2, default=str)
        except Exception:
            text = repr(raw)
    else:
        kind = "other"
        try:
            text = json.dumps(raw, default=str)
        except Exception:
            text = repr(raw)
    if len(text.encode("utf-8")) > _RAW_RETURN_CAP_BYTES:
        text = text.encode("utf-8")[:_RAW_RETURN_CAP_BYTES].decode(
            "utf-8", errors="replace"
        ) + "\n...[truncated at 8KB]"
    return (kind, text)


def _write_completion_breadcrumb(
    *,
    breadcrumb_dir: Path,
    dispatch_id: str,
    file_present: bool,
    contract_satisfied: bool,
    recovered_by_wrapper: bool,
    bytes_: int,
    raw_return: Any,
    error: str | None,
) -> None:
    kind, serialized = _summarize_raw_return(raw_return)
    completion = {
        "_meta": {
            "written_at": _now_iso(),
            "schema_version": _SCHEMA_VERSION,
            "kind": "completed",
        },
        "id": dispatch_id,
        "completed_at": _now_iso(),
        "file_present": file_present,
        "contract_satisfied": contract_satisfied,
        "recovered_by_wrapper": recovered_by_wrapper,
        "bytes": bytes_,
        "raw_return_kind": kind,
        "raw_return": serialized,
        "error": error,
    }
    completion_path = breadcrumb_dir / f"{dispatch_id}.completed.json"
    _atomic_write_text(completion_path, json.dumps(completion, indent=2))


def _emit_warning(dispatch_id: str, expected_path: Path, *, error: str, detail: str) -> None:
    """W5: one-line stderr warning on any non-clean dispatch."""
    msg = (
        f"omh_delegate[{error}]: id={dispatch_id} expected={expected_path} "
        f"detail={detail!r}"
    )
    print(msg, file=sys.stderr, flush=True)
