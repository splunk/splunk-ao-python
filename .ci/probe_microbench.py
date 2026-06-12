"""Windows test-duration probe microbenchmarks (investigation branch).

Times, in isolation (outside pytest), the operations involved in per-test config
validation, to explain the ~19x slower fixture *setup* on Python 3.11 Windows.

  1. socket.getaddrinfo() for the bogus host in GALILEO_CONSOLE_URL ("localtest")
  2. asyncio event-loop create/close churn
  3. cross-thread dispatch latency: run_coroutine_threadsafe round-trip onto a
     background run_forever loop — this is exactly what galileo_core's async_run /
     EventLoopThreadPool does for every validation request. THE key measurement.
  4. GalileoPythonConfig.get() — the per-test autouse fixture (real, unmocked).

Set PROBE_EVENT_LOOP=selector to force the WindowsSelectorEventLoopPolicy so the
default Proactor loop can be A/B'd against it. Everything is timestamped/flushed.
"""

import asyncio
import contextlib
import datetime
import os
import socket
import sys
import threading
import time
from collections.abc import Callable

# Force the selector loop BEFORE any asyncio object is created, if requested.
_FORCED = "default(Proactor on win32)"
if (
    os.environ.get("PROBE_EVENT_LOOP") == "selector"
    and sys.platform == "win32"
    and hasattr(asyncio, "WindowsSelectorEventLoopPolicy")
):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    _FORCED = "forced WindowsSelectorEventLoopPolicy"

# Make `galileo` importable (installed with --no-root; pytest uses pythonpath=src).
_src = os.path.join(os.getcwd(), "src")
if os.path.isdir(_src):
    sys.path.insert(0, _src)


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
log(f"event loop policy: {type(asyncio.get_event_loop_policy()).__name__} ({_FORCED})")

# 1) Name resolution — the prime suspect. "localtest" is intentionally bogus.
log("--- getaddrinfo ---")
for host in ("localtest", "localhost", "127.0.0.1"):
    bench(f"getaddrinfo({host!r}, 8088)", lambda host=host: socket.getaddrinfo(host, 8088), n=5)

# 2) asyncio event-loop churn (create + close).
log("--- asyncio loop churn ---")


def _loop_cycle() -> None:
    loop = asyncio.new_event_loop()
    loop.close()


bench("asyncio new+close", _loop_cycle, n=50)

# 3) Cross-thread dispatch latency. A background thread runs run_forever(); we
#    submit coroutines from the main thread via run_coroutine_threadsafe and
#    block on the result — the exact shape of galileo_core's async_run. This
#    isolates the per-call wakeup cost of the event loop, which is what differs
#    between the Proactor and Selector loops on Windows.
log("--- cross-thread dispatch (run_coroutine_threadsafe round-trip) ---")
_bg_loop = asyncio.new_event_loop()
log(f"background loop type: {type(_bg_loop).__name__}")
_bg_thread = threading.Thread(target=_bg_loop.run_forever, daemon=True)
_bg_thread.start()


async def _noop() -> int:
    return 1


def _dispatch_noop() -> None:
    asyncio.run_coroutine_threadsafe(_noop(), _bg_loop).result()


bench("dispatch noop (pure wakeup, no I/O)", _dispatch_noop, n=50)


async def _yield_chain() -> None:
    for _ in range(20):
        await asyncio.sleep(0)


def _dispatch_yield() -> None:
    asyncio.run_coroutine_threadsafe(_yield_chain(), _bg_loop).result()


bench("dispatch 20x await sleep(0) (ready-callback iterations)", _dispatch_yield, n=50)


async def _tiny_sleeps() -> None:
    # 1ms requested x10. On Windows the ~15.6ms timer tick rounds each up.
    for _ in range(10):
        await asyncio.sleep(0.001)


def _dispatch_tiny() -> None:
    asyncio.run_coroutine_threadsafe(_tiny_sleeps(), _bg_loop).result()


bench("dispatch 10x await sleep(0.001) (timer granularity)", _dispatch_tiny, n=20)

_bg_loop.call_soon_threadsafe(_bg_loop.stop)

# 4) GalileoPythonConfig.get — the per-test autouse fixture, REAL (no mocks).
log("--- GalileoPythonConfig.get (unmocked: hits real localtest resolution) ---")
os.environ.setdefault("GALILEO_CONSOLE_URL", "http://localtest:8088")
os.environ.setdefault("GALILEO_API_KEY", "api-1234567890")
try:
    from galileo.config import GalileoPythonConfig

    def _config_get() -> None:
        cfg = GalileoPythonConfig.get(console_url="http://localtest:8088", api_key="api-1234567890")
        with contextlib.suppress(Exception):
            cfg.reset()

    bench("GalileoPythonConfig.get+reset", _config_get, n=2)
except Exception as e:
    log(f"config import/get failed: {type(e).__name__}: {e}")

log("done")
