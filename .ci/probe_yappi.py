"""Thread-aware profile of the per-test config validation (investigation branch).

cProfile only sees the calling thread, but galileo_core runs the 3 validation
requests on a background EventLoopThread — so we use yappi (wall-clock, all
threads, builtins) to attribute where the ~12x-more timer-quantized waits on
Python 3.11 Windows actually accrue.

Reproduces the *mocked* path (respx), i.e. the real test conditions (~685 ms on
3.11), NOT the unmocked DNS path. Profiles N config.get()+reset() cycles.
"""

import contextlib
import datetime
import os
import sys
from unittest.mock import patch
from uuid import uuid4

_src = os.path.join(os.getcwd(), "src")
if os.path.isdir(_src):
    sys.path.insert(0, _src)

os.environ.setdefault("GALILEO_CONSOLE_URL", "http://localtest:8088")
os.environ.setdefault("GALILEO_API_KEY", "api-1234567890")


def _ts() -> str:
    return datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]


def log(msg: str) -> None:
    sys.stdout.write(f"[YAPPI {_ts()}] {msg}\n")
    sys.stdout.flush()


import respx  # noqa: E402
import yappi  # noqa: E402

from galileo.config import GalileoPythonConfig  # noqa: E402

_USER = {"id": str(uuid4()), "email": "user@example.com", "role": "user"}
_N = 10
_ok = 0
_last_exc = None


def _one_cycle() -> None:
    global _ok, _last_exc
    try:
        cfg = GalileoPythonConfig.get(console_url="http://localtest:8088", api_key="api-1234567890")
        with contextlib.suppress(Exception):
            cfg.reset()
        _ok += 1
    except Exception as e:
        _last_exc = e


log(f"python {sys.version.split()[0]} platform {sys.platform}")

with (
    patch("galileo_core.schemas.base_config.jwt_decode", return_value={"exp": float("inf")}),
    respx.mock(assert_all_called=False) as router,
):
    router.get(url__regex=r".*/healthcheck.*").respond(200, json={"status": "ok"})
    router.post(url__regex=r".*/login/api_key.*").respond(200, json={"access_token": "secret_jwt_token"})
    router.get(url__regex=r".*/current_user.*").respond(200, json=_USER)

    _one_cycle()  # warmup: also spins up the (one-time) EventLoopThreadPool
    log(f"warmup ok={_ok} exc={type(_last_exc).__name__ if _last_exc else None}")

    yappi.set_clock_type("wall")
    yappi.start(builtins=True)
    for _ in range(_N):
        _one_cycle()
    yappi.stop()

log(f"profiled {_N} cycles, ok={_ok}/{_N + 1}, last_exc={type(_last_exc).__name__ if _last_exc else None}")

# Per-thread wall time (which thread holds the cost).
log("================ THREAD STATS ================")
yappi.get_thread_stats().print_all()

# Top functions by total wall time across ALL threads. ncall reveals how many
# times each is hit per run — the 3.10 vs 3.11 delta should show as ncall.
log("================ TOP 50 FUNCTIONS BY ttot (all threads, builtins) ================")
stats = yappi.get_func_stats()
stats.sort("ttot", "desc")
for i, s in enumerate(stats):
    if i >= 50:
        break
    sys.stdout.write(f"  ttot={s.ttot * 1000:9.1f}ms tsub={s.tsub * 1000:9.1f}ms ncall={s.ncall:>8} {s.full_name}\n")
sys.stdout.flush()

# Explicitly surface the usual Windows-wait suspects regardless of rank.
log("================ WAIT/SLEEP/POLL SUSPECTS ================")
_needles = ("sleep", "select", "GetQueuedCompletionStatus", "_run_once", "getaddrinfo", "poll", "wait", "Overlapped")
for s in stats:
    if any(n.lower() in s.full_name.lower() for n in _needles):
        sys.stdout.write(f"  ttot={s.ttot * 1000:9.1f}ms ncall={s.ncall:>8} avg={s.tavg * 1000:7.3f}ms {s.full_name}\n")
sys.stdout.flush()
log("done")
