from fastapi import FastAPI, Depends, Body, Form, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import JSONResponse

from sqlalchemy.orm import Session
import hashlib

from .db import engine, Base, get_db
from .models import Record
from .services.pubmed import search_pubmed, fetch_pubmed_details
from .services.summarizer import summarize_text

app = FastAPI(title="HerTrials API")

# Static + templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

ALLOWED_MODES = {"scientific", "layman", "children"}


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/records", response_class=HTMLResponse)
def view_records(request: Request, db: Session = Depends(get_db)):
    records = db.query(Record).order_by(Record.created_at.desc()).all()
    return templates.TemplateResponse("records.html", {"request": request, "records": records})


# ✅ IMPORTANT: GET /search to render the page (no Method Not Allowed)
@app.get("/search", response_class=HTMLResponse)
def search_page(request: Request, db: Session = Depends(get_db)):
    records = (
        db.query(Record)
        .order_by(Record.created_at.desc())
        .limit(5)
        .all()
    )
    return templates.TemplateResponse(
        "search.html",
        {
            "request": request,
            "records": records,
            "query": "",
        },
    )


# POST /search = form submission
@app.post("/search", response_class=HTMLResponse)
def search_submit(
    request: Request,
    query: str = Form(...),
    db: Session = Depends(get_db),
):
    ingest_pubmed(topic=query, db=db)

    records = (
        db.query(Record)
        .order_by(Record.created_at.desc())
        .limit(5)
        .all()
    )

    return templates.TemplateResponse(
        "search.html",
        {
            "request": request,
            "records": records,
            "query": query,
        },
    )
@app.get("/search", response_class=HTMLResponse)
def search_page(request: Request, db: Session = Depends(get_db)):
    # Option A: page vide
    return templates.TemplateResponse(
        "search.html",
        {"request": request, "records": [], "last_query": ""}
    )

@app.get("/search_last", response_class=HTMLResponse)
def search_last(request: Request, db: Session = Depends(get_db)):
    records = (
        db.query(Record)
        .order_by(Record.created_at.desc())
        .limit(5)
        .all()
    )

    return templates.TemplateResponse(
        "search.html",
        {
            "request": request,
            "records": records,
            "query": "Latest results",
        },
    )


# Endpoint API (optionnel) + function used by POST /search
@app.post("/ingest/pubmed")
def ingest_pubmed(
    topic: str = Body(...),
    db: Session = Depends(get_db),
):
    query = f"({topic}) AND (clinical trial[Publication Type]) AND (2018:3000[dp])"

    pmids = search_pubmed(query, max_results=5)
    details = fetch_pubmed_details(pmids)

    inserted = []
    for article in details:
        pmid = article["pmid"]

        existing = db.query(Record).filter(Record.external_id == pmid).first()
        if existing:
            continue

        abstract = article.get("abstract") or ""
        title = article.get("title") or ""

        text_hash = hashlib.sha256((title + abstract).encode("utf-8")).hexdigest()

        record = Record(
            source="pubmed",
            external_id=pmid,
            title=title,
            abstract=abstract,
            year=article.get("year"),
            url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            raw_json=article,
            text_hash=text_hash,
            topic=topic,
        )

        db.add(record)
        inserted.append(pmid)

    db.commit()
    return {"inserted": inserted}


@app.post("/summarize/{record_id}/{mode}")
def summarize_record(
    record_id: str,
    mode: str,
    db: Session = Depends(get_db),
):
    mode = mode.lower().strip()
    if mode not in ALLOWED_MODES:
        raise HTTPException(status_code=400, detail=f"Invalid mode. Use one of: {sorted(ALLOWED_MODES)}")

    record = db.query(Record).filter(Record.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    if not record.abstract or len(record.abstract.strip()) < 50:
        return JSONResponse({"error": "No abstract available"}, status_code=200)

    summary = summarize_text(record.abstract, mode=mode)

    if mode == "scientific":
        record.summary_scientific = summary
    elif mode == "layman":
        record.summary_layman = summary
    else:  # children
        record.summary_children = summary

    db.commit()
    return RedirectResponse(url="/search_last", status_code=303)
