"""HEAD-check every source_url in a programs fixture.

Usage:
    uv run python scripts/verify_dataset_urls.py [--fixture PATH] [--timeout 10]
        [--max N] [--sleep 0.3] [--json out.json]

Reads the fixture, issues an HTTP HEAD (falling back to a small GET) for each
distinct URL, and prints a table of id / url / status / elapsed_ms.

Intentional design decisions:
    * stdlib only - no extra deps (urllib.request).
    * UTF-8 stdout forced on Windows consoles.
    * Retries once on transient error; if HEAD is 405/403, retries with GET.
    * A polite sleep between requests (default 0.3s) to avoid hammering sites.
    * Never writes back to the fixture - read-only.

Exit code:
    0  all reachable (<400)
    1  some unreachable (WARN)
    2  catastrophic (couldn't even parse fixture)
"""

from __future__ import annotations

import argparse
import io
import json
import ssl
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "programs_verified_20260411.json"

# Force stdout to UTF-8 on Windows so Korean characters don't crash cp949 consoles.
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True
    )

USER_AGENT = "Mozilla/5.0 (career-ops-kr verifier; +https://github.com/pollmap/career-ops-kr)"
# Permissive SSL context - many Korean gov sites have intermediate-cert quirks.
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE


@dataclass
class UrlProbe:
    id: str
    name: str
    url: str
    status: int = 0
    ok: bool = False
    elapsed_ms: int = 0
    error: str = ""
    method: str = ""
    note: str = field(default="")


def _probe_once(url: str, method: str, timeout: float) -> tuple[int, str]:
    req = urllib.request.Request(
        url,
        method=method,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as resp:
        return resp.status, ""


def probe_url(identifier: str, name: str, url: str, timeout: float) -> UrlProbe:
    probe = UrlProbe(id=identifier, name=name, url=url)
    started = time.monotonic()
    for method in ("HEAD", "GET"):
        try:
            status, _ = _probe_once(url, method, timeout)
            probe.status = status
            probe.method = method
            probe.ok = 200 <= status < 400
            break
        except urllib.error.HTTPError as exc:
            # Some sites return 405/403 on HEAD - fall through to GET.
            if exc.code in (405, 403, 400) and method == "HEAD":
                continue
            probe.status = exc.code
            probe.method = method
            probe.error = f"HTTPError {exc.code}"
            probe.ok = 200 <= exc.code < 400
            break
        except urllib.error.URLError as exc:
            probe.method = method
            probe.error = f"URLError: {exc.reason}"
            break
        except (TimeoutError, ssl.SSLError) as exc:
            probe.method = method
            probe.error = f"{type(exc).__name__}: {exc}"
            break
        except Exception as exc:
            probe.method = method
            probe.error = f"{type(exc).__name__}: {exc}"
            break
    probe.elapsed_ms = int((time.monotonic() - started) * 1000)
    return probe


def verify(fixture: Path, timeout: float, max_n: int, sleep: float, out_json: Path | None) -> int:
    text = fixture.read_text(encoding="utf-8")
    data = json.loads(text)
    programs = data["programs"]
    if max_n > 0:
        programs = programs[:max_n]

    print("# URL reachability probe")
    print(f"_file: {fixture.relative_to(REPO_ROOT)}_")
    print(f"_count: {len(programs)}_")
    print(f"_timeout: {timeout}s per request, sleep: {sleep}s between_\n")
    print("| id | method | status | ms | url |")
    print("|---|---|---|---|---|")

    probes: list[UrlProbe] = []
    failed: list[UrlProbe] = []
    for program in programs:
        probe = probe_url(program["id"], program.get("name", ""), program["source_url"], timeout)
        probes.append(probe)
        marker = "ok" if probe.ok else "FAIL"
        status_cell = str(probe.status) if probe.status else probe.error[:40]
        print(
            f"| {probe.id} | {probe.method} | {status_cell} | {probe.elapsed_ms} | "
            f"{probe.url} | {marker}"
        )
        if not probe.ok:
            failed.append(probe)
        time.sleep(sleep)

    print("\n---")
    print(f"**Total: {len(probes)}  ok: {len(probes) - len(failed)}  FAIL: {len(failed)}**")

    if out_json is not None:
        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_json.write_text(
            json.dumps([asdict(probe) for probe in probes], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        try:
            display = out_json.relative_to(REPO_ROOT)
        except ValueError:
            display = out_json
        print(f"_json written: {display}_")

    return 0 if not failed else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--max", type=int, default=0, help="limit how many URLs to probe (0 = all)")
    parser.add_argument("--sleep", type=float, default=0.3)
    parser.add_argument("--json", type=Path, default=None, dest="out_json")
    args = parser.parse_args(argv)
    try:
        return verify(args.fixture, args.timeout, args.max, args.sleep, args.out_json)
    except (json.JSONDecodeError, FileNotFoundError) as exc:
        print(f"FATAL: could not load fixture: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
