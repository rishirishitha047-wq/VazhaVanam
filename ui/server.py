"""VazhaVanam Web UI — FastAPI server + single-page HTML interface.

    python -m ui.server           starts on http://localhost:8000
    python -m ui.server --port N  custom port
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Make sure the project root is on the path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import json
import os

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from agent.app import run as agent_run
from agent import tools

app = FastAPI(title="VazhaVanam")

# Serve the static folder (HTML/CSS/JS)
UI_DIR = Path(__file__).parent / "static"
UI_DIR.mkdir(exist_ok=True)


@app.get("/", response_class=HTMLResponse)
def root():
    return (UI_DIR / "index.html").read_text(encoding="utf-8")


@app.post("/ask")
def ask(body: dict):
    """Run the agent on a question. Body: {text, lang}"""
    text = (body.get("text") or "").strip()
    lang = body.get("lang") or tools.language_of(text)
    if not text:
        return JSONResponse({"error": "No question provided."}, status_code=400)
    try:
        result = agent_run({"text": text, "lang": lang})
        return JSONResponse(result)
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@app.get("/health")
def health():
    return {"status": "ok", "model": os.environ.get("SHIP_MODEL", "us.amazon.nova-2-lite-v1:0")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--host", default="127.0.0.1")
    a = ap.parse_args()
    print(f"\nVazhaVanam UI: http://{a.host}:{a.port}\n")
    uvicorn.run("ui.server:app", host=a.host, port=a.port, reload=False)


if __name__ == "__main__":
    main()