import requests
import xml.etree.ElementTree as ET
from typing import List, Dict

BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

def search_pubmed(query: str, max_results: int = 10) -> List[str]:
    url = BASE_URL + "esearch.fcgi"
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "retmode": "json"
    }

    response = requests.get(url, params=params)
    data = response.json()
    return data.get("esearchresult", {}).get("idlist", [])


def fetch_pubmed_details(pmids: List[str]) -> List[Dict]:
    url = BASE_URL + "efetch.fcgi"
    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml"
    }

    response = requests.get(url, params=params)
    root = ET.fromstring(response.content)

    records = []

    for article in root.findall(".//PubmedArticle"):
        pmid = article.findtext(".//PMID")
        title = article.findtext(".//ArticleTitle")

        abstract_parts = article.findall(".//AbstractText")
        abstract = " ".join([part.text for part in abstract_parts if part.text])

        year = article.findtext(".//PubDate/Year")

        records.append({
            "pmid": pmid,
            "title": title,
            "abstract": abstract,
            "year": int(year) if year and year.isdigit() else None
        })

    return records
