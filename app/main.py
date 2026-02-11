from fastapi import FastAPI, Depends, Body
from sqlalchemy.orm import Session
from .db import engine, Base, get_db
from .models import Record
from .services.pubmed import search_pubmed, fetch_pubmed_details
import hashlib
from .services.summarizer import summarize_text

app = FastAPI(title="HerTrials API")

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)

@app.get("/")
def root():
    return {"status": "HerTrials backend running"}


@app.post("/ingest/pubmed")
def ingest_pubmed(
    topic: str = Body(...),
    db: Session = Depends(get_db)
):
    query = f'({topic}) AND (clinical trial[Publication Type]) AND (2018:3000[dp])'

    pmids = search_pubmed(query, max_results=5)
    details = fetch_pubmed_details(pmids)

    inserted = []
    for article in details:
        pmid = article["pmid"]
        existing = db.query(Record).filter(Record.external_id == pmid).first()
        if existing:
            continue

        text_hash = hashlib.sha256(
            (article["title"] + article["abstract"]).encode()
        ).hexdigest()

        record = Record(
            source="pubmed",
            external_id=pmid,
            title=article["title"],
            abstract=article["abstract"],
            year=article["year"],
            url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            raw_json=article,
            text_hash=text_hash,
            topic=topic
        )

        db.add(record)
        inserted.append(pmid)

    db.commit()

    return {"inserted": inserted}


@app.post("/summarize/{record_id}")
def summarize_record(record_id: str, db: Session = Depends(get_db)):
    record = db.query(Record).filter(Record.id == record_id).first()

    if not record:
        return {"error": "Record not found"}

    if not record.abstract:
        return {"error": "No abstract available"}

    if record.summary_scientific:
        return {
            "message": "Summary already exists",
            "summary": record.summary_scientific
        }

    summary = summarize_text(record.abstract)

    record.summary_scientific = summary
    db.commit()

    return {
        "record_id": record_id,
        "summary": summary
    }