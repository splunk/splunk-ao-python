"""Windows test-duration probe microbenchmarks (investigation branch).

Times, in isolation (outside pytest), the operations most likely to explain the
~1s-per-test silent overhead seen on Python 3.11+ Windows but not 3.10:

  1. socket.getaddrinfo() for the bogus host in GALILEO_CONSOLE_URL ("localtest")
  2. asyncio event-loop create/close churn (Windows ProactorEventLoop cost)
  3. GalileoPythonConfig.get() — replicates the autouse `set_validated_config`
     fixture that runs on EVERY test.

Everything is timestamped and flushed so output can be correlated with the rest
of the CI log.
"""

import asyncio
import contextlib
import datetime
import os
import socket
import sys
import time
from collections.abc import Callable


def _ts() -> str:
    return datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]


def log(msg: str) -> None:
    # Write straight to stdout (not print()) so ruff's T201 autofix can't strip it.
    sys.stdout.write(f"[BENCH {_ts()}] {msg}\n")
    sys.stdout.flush()


def bench(label: str, fn: Callable[[], object], n: int = 5) -> list[float]:
    samples = []
    last_exc = None
    for _ in range(n):
        t = time.perf_counter()
        try:
            fn()
        except Exception as e:
            last_exc = e
        samples.append(time.perf_counter() - t)
    summary = ", ".join(f"{x * 1000:.1f}ms" for x in samples)
    total = sum(samples) * 1000
    avg = total / len(samples)
    log(f"{label}: avg={avg:.1f}ms total={total:.1f}ms exc={type(last_exc).__name__ if last_exc else None}")
    log(f"    samples=[{summary}]")
    return samples


log(f"python {sys.version}")
log(f"platform {sys.platform}")
log(f"asyncio policy {type(asyncio.get_event_loop_policy()).__name__}")

# 1) Name resolution — the prime suspect. "localtest" is intentionally bogus.
log("--- getaddrinfo ---")
for host in ("localtest", "localhost", "127.0.0.1"):
    bench(f"getaddrinfo({host!r}, 8088)", lambda host=host: socket.getaddrinfo(host, 8088), n=5)

# 2) asyncio event-loop churn.
log("--- asyncio loop churn ---")


def _loop_cycle() -> None:
    loop = asyncio.new_event_loop()
    loop.close()


bench("asyncio new+close", _loop_cycle, n=50)

# 3) GalileoPythonConfig.get — the per-test autouse fixture, with a REAL network
#    attempt (no pytest mocks here). If this is ~1s and dominated by getaddrinfo,
#    that's the per-test cost.
log("--- GalileoPythonConfig.get ---")
os.environ.setdefault("GALILEO_CONSOLE_URL", "http://localtest:8088")
os.environ.setdefault("GALILEO_API_KEY", "api-1234567890")
try:
    from galileo.config import GalileoPythonConfig

    def _config_get() -> None:
        cfg = GalileoPythonConfig.get(console_url="http://localtest:8088", api_key="api-1234567890")
        with contextlib.suppress(Exception):
            cfg.reset()

    bench("GalileoPythonConfig.get+reset", _config_get, n=5)
except Exception as e:
    log(f"config import/get failed: {type(e).__name__}: {e}")

log("done")
