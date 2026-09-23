import json
import math
from pathlib import Path
from typing import List

from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI()

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "*",
}

DATA = json.loads((Path(__file__).parent / "telemetry.json").read_text())


class Query(BaseModel):
    regions: List[str]
    threshold_ms: float


def percentile(values, p):
    s = sorted(values)
    k = (len(s) - 1) * p / 100
    lo, hi = math.floor(k), math.ceil(k)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def compute(q: Query):
    out = {}
    for r in q.regions:
        rows = [d for d in DATA if d["region"] == r]
        if not rows:
            continue
        lat = [d["latency_ms"] for d in rows]
        up = [d["uptime_pct"] for d in rows]
        out[r] = {
            "avg_latency": sum(lat) / len(lat),
            "p95_latency": percentile(lat, 95),
            "avg_uptime": sum(up) / len(up),
            "breaches": sum(1 for x in lat if x > q.threshold_ms),
        }
    return out


@app.options("/")
@app.options("/api")
def preflight():
    return Response(status_code=204, headers=CORS_HEADERS)


@app.post("/")
@app.post("/api")
def analyze(q: Query):
    res = compute(q)
    return JSONResponse(content={"regions": res, **res}, headers=CORS_HEADERS)