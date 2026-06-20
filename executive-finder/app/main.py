import os
import json
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.sources.apollo import search_executives as apollo_search, raw_apollo_request
from app.filters.executive import OUTREACH_TEMPLATES

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = FastAPI(title="Executive Finder")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SECRET_KEY", "dev-secret-change-me"),
)
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


@app.get("/")
async def index():
    html_path = os.path.join(BASE_DIR, "ExecutiveFinder.html")
    return FileResponse(html_path)


@app.post("/api/search")
async def api_search(request: Request):
    body = await request.json()
    keywords = body.get("keywords", [])
    titles = body.get("titles") or None
    location = body.get("location") or None
    apollo_key = body.get("apollo_key", "").strip()

    if not apollo_key:
        return JSONResponse({"error": "Kein API-Key", "results": [], "count": 0}, status_code=400)

    status, results, error_msg = await raw_apollo_request(apollo_key, keywords, titles, location)

    if status != 200:
        return JSONResponse({"error": error_msg, "results": [], "count": 0}, status_code=status)

    return JSONResponse({"results": results, "count": len(results)})
