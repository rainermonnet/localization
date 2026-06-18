import os
import json
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.auth.linkedin import get_authorization_url, generate_state, exchange_code_for_token, get_linkedin_profile
from app.sources.crunchbase import search_executives as crunchbase_search
from app.sources.apollo import search_executives as apollo_search
from app.filters.executive import parse_keywords, merge_and_deduplicate, generate_outreach, OUTREACH_TEMPLATES

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = FastAPI(title="Executive Finder")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SECRET_KEY", "dev-secret-change-me"),
)
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    # Serve the standalone HTML app directly
    html_path = os.path.join(BASE_DIR, "ExecutiveFinder.html")
    if os.path.exists(html_path):
        return FileResponse(html_path)
    profile = request.session.get("profile")
    return templates.TemplateResponse("index.html", {"request": request, "profile": profile})


@app.post("/api/search")
async def api_search(request: Request):
    """Proxy endpoint – solves CORS by making server-side Apollo.io calls."""
    body = await request.json()
    keywords = body.get("keywords", [])
    titles = body.get("titles") or None
    location = body.get("location") or None
    apollo_key = body.get("apollo_key", "")

    # Temporarily set the API key from the request
    if apollo_key:
        os.environ["APOLLO_API_KEY"] = apollo_key

    results = await apollo_search(keywords, titles, location, limit=25)
    return JSONResponse({"results": results, "count": len(results)})



@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    profile = request.session.get("profile")
    return templates.TemplateResponse("index.html", {"request": request, "profile": profile})


@app.get("/auth/login")
async def linkedin_login(request: Request):
    state = generate_state()
    request.session["oauth_state"] = state
    return RedirectResponse(get_authorization_url(state))


@app.get("/auth/callback")
async def linkedin_callback(request: Request, code: str = "", state: str = "", error: str = ""):
    if error:
        raise HTTPException(status_code=400, detail=f"LinkedIn OAuth Fehler: {error}")

    if state != request.session.get("oauth_state"):
        raise HTTPException(status_code=400, detail="Ungültiger OAuth State")

    token_data = await exchange_code_for_token(code)
    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="Kein Access Token erhalten")

    profile = await get_linkedin_profile(access_token)
    request.session["profile"] = profile
    request.session["access_token"] = access_token
    return RedirectResponse("/dashboard")


@app.get("/auth/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/")


@app.get("/guest")
async def guest_login(request: Request):
    """Direkt als Gast einsteigen – kein LinkedIn-Account erforderlich."""
    request.session["profile"] = {"name": "Gast", "guest": True}
    return RedirectResponse("/dashboard")


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    profile = request.session.get("profile")
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "profile": profile,
        "outreach_templates": list(OUTREACH_TEMPLATES.keys()),
    })


@app.post("/search", response_class=HTMLResponse)
async def search(
    request: Request,
    keywords_raw: str = Form(...),
    titles_raw: str = Form(""),
    location: str = Form(""),
    sources: list[str] = Form(default=["crunchbase", "apollo"]),
    limit: int = Form(25),
):
    profile = request.session.get("profile")
    keywords = parse_keywords(keywords_raw)
    titles = [t.strip() for t in titles_raw.split(",") if t.strip()] if titles_raw else []
    loc = location.strip() or None

    results_cb, results_ap = [], []

    if "crunchbase" in sources:
        results_cb = await crunchbase_search(keywords, titles or None, loc, limit)

    if "apollo" in sources:
        results_ap = await apollo_search(keywords, titles or None, loc, limit)

    merged = merge_and_deduplicate(results_cb, results_ap)

    request.session["last_results"] = merged
    request.session["last_keywords"] = keywords

    return templates.TemplateResponse("results.html", {
        "request": request,
        "profile": profile,
        "results": merged,
        "keywords": keywords,
        "outreach_templates": list(OUTREACH_TEMPLATES.keys()),
        "count": len(merged),
    })


@app.post("/outreach", response_class=HTMLResponse)
async def outreach(
    request: Request,
    person_json: str = Form(...),
    template_key: str = Form("collaboration"),
    keyword: str = Form(""),
):
    person = json.loads(person_json)
    kw = keyword or (request.session.get("last_keywords") or ["Ihrem Fachgebiet"])[0]
    text = generate_outreach(person, kw, template_key)
    profile = request.session.get("profile")
    return templates.TemplateResponse("outreach.html", {
        "request": request,
        "profile": profile,
        "person": person,
        "outreach_text": text,
        "template_key": template_key,
        "keyword": kw,
        "outreach_templates": list(OUTREACH_TEMPLATES.keys()),
    })
