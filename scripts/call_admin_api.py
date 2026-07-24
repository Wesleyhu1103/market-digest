#!/usr/bin/env python3
"""Call the deployed admin API with retries and honest failure output.

Used by GitHub workflows so pipeline runs never talk to Postgres directly:
the only credential is the same bearer the admin page uses.

  call_admin_api.py --path /api/admin-proposals [--method GET|POST]
      [--body '{"action":"process"}'] [--bearer-env FEEDBACK_ADMIN_SECRET]
      [--origin https://...] [--retries 3] [--timeout 60] [--out FILE]

Origin resolution: --origin, else ADMIN_API_ORIGIN env var, else vercelOrigin
from docs/site-config.json. Network errors and 5xx retry with exponential
backoff; 4xx fails immediately (auth and shape errors do not heal on retry),
with a pointed hint on 401/403. Exits 0 only on a 2xx response.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def resolve_origin(cli: str | None) -> str:
    if cli:
        return cli.rstrip("/")
    env = os.environ.get("ADMIN_API_ORIGIN")
    if env:
        return env.rstrip("/")
    cfg = json.loads((ROOT / "docs" / "site-config.json").read_text())
    return str(cfg["vercelOrigin"]).rstrip("/")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--path", required=True)
    p.add_argument("--method", default=None, help="default: POST when --body given, else GET")
    p.add_argument("--body", default=None)
    p.add_argument("--bearer-env", default="FEEDBACK_ADMIN_SECRET")
    p.add_argument("--origin", default=None)
    p.add_argument("--retries", type=int, default=3)
    p.add_argument("--timeout", type=int, default=60)
    p.add_argument("--backoff-base", type=int, default=2, help=argparse.SUPPRESS)
    p.add_argument("--out", default=None, help="write the response body to this file")
    args = p.parse_args()

    token = os.environ.get(args.bearer_env, "")
    if not token:
        print(f"{args.bearer_env} is not set in the environment", file=sys.stderr)
        return 2

    method = args.method or ("POST" if args.body else "GET")
    url = resolve_origin(args.origin) + args.path
    data = args.body.encode() if args.body else None
    headers = {"Authorization": f"Bearer {token}"}
    if data:
        headers["Content-Type"] = "application/json"

    last = "no attempt made"
    for attempt in range(1, args.retries + 1):
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=args.timeout) as res:
                body = res.read().decode()
                if args.out:
                    Path(args.out).write_text(body)
                print(f"{method} {args.path} -> {res.status} ({len(body)} bytes)")
                return 0
        except urllib.error.HTTPError as e:
            try:
                snippet = e.read().decode()[:300]
            except Exception:
                snippet = ""
            last = f"HTTP {e.code}: {snippet}"
            if e.code < 500:
                print(f"{method} {url} -> {last}", file=sys.stderr)
                if e.code in (401, 403):
                    print(
                        f"Auth rejected: check that the {args.bearer_env} GitHub Actions "
                        "secret matches the Vercel env var of the same name.",
                        file=sys.stderr,
                    )
                return 1
        except (OSError, urllib.error.URLError) as e:
            last = str(e)
        if attempt < args.retries:
            delay = args.backoff_base**attempt
            print(f"attempt {attempt}/{args.retries} failed ({last}); retrying in {delay}s", file=sys.stderr)
            time.sleep(delay)

    print(f"{method} {url} failed after {args.retries} attempt(s): {last}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
