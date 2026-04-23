"""Dynamic Typer commands generated from the backend provider catalog.

At first run the module fetches ``GET /providers/catalog/`` and caches
the result. On subsequent invocations it only re-fetches if the backend
hash differs from the cached one. Each operation becomes a nested Typer
subcommand whose path mirrors ``cli_path`` (e.g. ``kb gws gmail send``).

Parameters declared in the spec become ``typer.Option`` entries. File-type
params (``"type": "file"``) are uploaded first to ``/run-artifacts/upload/``
and replaced with the resulting ``file_id`` before the RPC call — no raw
bytes in the dispatcher payload.
"""

from __future__ import annotations

import json
import os
import pickle
import time
from pathlib import Path
from typing import Any, Callable

import typer

from ..client import get_client
from ..client.http import APIError
from ..output import emit_json


CACHE_DIR = Path(os.environ.get("KB_CACHE_DIR") or
                 Path.home() / ".kb-cache")
CATALOG_JSON = CACHE_DIR / "provider-catalog.json"
CATALOG_PICKLE = CACHE_DIR / "provider-catalog.pkl"

# How long to trust the local cache without re-checking the hash (seconds).
# Short default; refresh is cheap. Env override for tests.
_CACHE_MAX_AGE = int(os.environ.get("KB_CATALOG_TTL", "300"))


def install_provider_commands(root_app: typer.Typer) -> None:
    """Populate ``root_app`` with subcommands for every registered operation.

    Silent no-op if the backend is unreachable — we don't want a network
    failure to brick the whole ``kb`` CLI on startup.
    """
    try:
        catalog = _load_catalog()
    except APIError:
        return
    except Exception:
        return

    ops = catalog.get("operations") or []
    subapps: dict[tuple[str, ...], typer.Typer] = {(): root_app}

    for spec in ops:
        cli_path = tuple(spec.get("cli_path") or [])
        if len(cli_path) < 2:
            continue
        parent = _ensure_subapp_chain(subapps, cli_path[:-1], root_app)
        _attach_command(parent, cli_path[-1], spec)


# ---------------------------------------------------------------------------
# Catalog loading
# ---------------------------------------------------------------------------


def _load_catalog() -> dict:
    """Return catalog dict, refreshing from backend when stale."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    cached = _read_cached_catalog()
    if cached is not None and not _is_stale(cached):
        return cached

    client = get_client()
    remote_hash = None
    if cached is not None:
        try:
            remote_hash = client.get("providers/catalog/hash")["hash"]
        except Exception:
            return cached  # keep serving stale on transient errors
        if remote_hash == cached.get("hash"):
            _touch_cache()
            return cached

    fresh = client.get("providers/catalog")
    _write_cached_catalog(fresh)
    return fresh


def _read_cached_catalog() -> dict | None:
    if CATALOG_PICKLE.exists():
        try:
            with CATALOG_PICKLE.open("rb") as fh:
                return pickle.load(fh)
        except Exception:
            pass
    if CATALOG_JSON.exists():
        try:
            return json.loads(CATALOG_JSON.read_text())
        except Exception:
            return None
    return None


def _write_cached_catalog(catalog: dict) -> None:
    CATALOG_JSON.write_text(json.dumps(catalog, indent=2))
    try:
        with CATALOG_PICKLE.open("wb") as fh:
            pickle.dump(catalog, fh)
    except Exception:
        pass


def _is_stale(catalog: dict) -> bool:
    mtime = CATALOG_JSON.stat().st_mtime if CATALOG_JSON.exists() else 0
    return (time.time() - mtime) > _CACHE_MAX_AGE


def _touch_cache() -> None:
    if CATALOG_JSON.exists():
        os.utime(CATALOG_JSON, None)


# ---------------------------------------------------------------------------
# Typer plumbing
# ---------------------------------------------------------------------------


def _ensure_subapp_chain(cache: dict[tuple[str, ...], typer.Typer],
                         path: tuple[str, ...],
                         root: typer.Typer) -> typer.Typer:
    if path in cache:
        return cache[path]
    parent = _ensure_subapp_chain(cache, path[:-1], root)
    sub = typer.Typer(help=f"{path[-1]} operations")
    parent.add_typer(sub, name=path[-1])
    cache[path] = sub
    return sub


def _attach_command(app: typer.Typer, name: str, spec: dict) -> None:
    """Build a Typer command whose options mirror the spec's params_schema.

    Params tagged ``positional: true`` in the schema are emitted as
    ``typer.Argument(...)`` — callers pass them bare (``kb google doc get DOC_ID``).
    Everything else becomes a ``typer.Option(...)``. Positionals must come
    first in Typer's function signature, so we sort them ahead of options.
    """
    schema = spec.get("params_schema", {}) or {}
    properties: dict[str, dict] = schema.get("properties", {})
    required: set[str] = set(schema.get("required", []))

    def _callback(**kwargs):
        _execute(spec, kwargs)

    _callback.__name__ = f"{spec['provider']}_{spec['operation'].replace('.', '_')}"

    # Typer uses introspected signature; we build one via exec. Simpler and
    # stable across Typer versions than monkey-patching annotations.
    positional_code: list[str] = []
    option_code: list[str] = []
    for pname, pschema in properties.items():
        python_name = pname.replace("-", "_")
        help_text = (pschema.get("description") or "").replace('"', "'")
        if pschema.get("positional"):
            # Emit BOTH an optional positional Argument and a companion
            # --flag Option so agents can call either form. _execute merges
            # them (positional wins); the dispatcher still enforces required.
            positional_code.append(
                f'{python_name}: str = '
                f'typer.Argument(None, help="{help_text}")'
            )
            flag = pschema.get("cli_flag", f"--{pname.replace('_', '-')}")
            option_code.append(
                f'{python_name}_flag: str = typer.Option('
                f'None, "{flag}", help="{help_text} (alt to positional)")'
            )
            continue
        flag = pschema.get("cli_flag", f"--{pname.replace('_', '-')}")
        default_expr = _default_expr(pname, pschema, required)
        option_code.append(
            f'{python_name}: {_py_type(pschema)} = typer.Option('
            f'{default_expr}, "{flag}", help="{help_text}")'
        )

    # Alias knob — always available as option.
    option_code.append('alias: str = typer.Option("default", "--alias", help="Account alias")')
    params_code = positional_code + option_code

    help_text = (spec.get("help") or "").replace('"', "'")
    func_src = (
        f'def _cmd({", ".join(params_code)}):\n'
        f'    """{help_text}"""\n'
        f'    _execute(_SPEC, locals())\n'
    )
    namespace: dict[str, Any] = {"typer": typer, "_execute": _execute, "_SPEC": spec}
    exec(func_src, namespace)
    cmd_fn: Callable = namespace["_cmd"]
    app.command(name=name, help=help_text or None)(cmd_fn)


def _py_type(pschema: dict) -> str:
    t = pschema.get("type")
    if t == "integer":
        return "int"
    if t == "number":
        return "float"
    if t == "boolean":
        return "bool"
    if t == "array":
        return "list[str]"
    # string / object / file / missing → str (JSON-encoded for object)
    return "str"


def _default_expr(name: str, pschema: dict, required: set[str]) -> str:
    if name in required:
        return "..."
    if "default" in pschema:
        default = pschema["default"]
        return repr(default)
    if pschema.get("type") == "boolean":
        return "False"
    if pschema.get("type") == "array":
        return "None"
    return "None"


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


def _execute(spec: dict, kwargs: dict[str, Any]) -> None:
    alias = kwargs.pop("alias", "default")
    params = _coerce_params(spec, kwargs)

    client = get_client()
    try:
        response = client.post("providers/call", data={
            "provider": spec["provider"],
            "operation": spec["operation"],
            "params": params,
            "alias": alias,
        })
    except APIError as err:
        raise
    emit_json(response)


def _coerce_params(spec: dict, kwargs: dict[str, Any]) -> dict[str, Any]:
    schema = spec.get("params_schema", {}) or {}
    properties: dict[str, dict] = schema.get("properties", {})
    out: dict[str, Any] = {}
    for pname, pschema in properties.items():
        python_name = pname.replace("-", "_")
        # Positional + flag pair: prefer the positional value, fall back to
        # the ``_flag`` companion that carries ``--flag`` input.
        value = kwargs.get(python_name)
        if value is None and pschema.get("positional"):
            value = kwargs.get(f"{python_name}_flag")
        if value is None:
            continue
        if pschema.get("type") == "file" and isinstance(value, str):
            value = _upload_file(value)
        elif pschema.get("type") == "object" and isinstance(value, str):
            try:
                value = json.loads(value)
            except ValueError:
                pass
        elif pschema.get("type") == "array" and isinstance(value, list):
            inner = (pschema.get("items") or {}).get("type")
            if inner in ("array", "object"):
                if len(value) == 1 and isinstance(value[0], str):
                    # single JSON blob (e.g. --domain '[[...]]') — replace list with parsed content
                    try:
                        value = json.loads(value[0])
                    except ValueError:
                        pass
                else:
                    # repeated flags (e.g. --sorts '{...}' --sorts '{...}') — parse each element
                    parsed = []
                    for _item in value:
                        if isinstance(_item, str):
                            try:
                                parsed.append(json.loads(_item))
                            except ValueError:
                                parsed.append(_item)
                        else:
                            parsed.append(_item)
                    value = parsed
        out[pname] = value
    return out


def _upload_file(path: str) -> str:
    """Upload a local file to the artifact store, return its id as a string."""
    target = Path(path).expanduser()
    if not target.is_file():
        raise FileNotFoundError(f"file not found: {path}")
    client = get_client()
    payload = client.upload_file(str(target))
    return str(payload.get("id"))
