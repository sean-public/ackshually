#!/usr/bin/env python3

"""
Wikipedia Citation Scraper and Fact Checker

This script fetches a random English Wikipedia article,
scrapes its contents, extracts inline citations,
and uses an LLM to fact-check the citations by scraping
the provided URL for each.
"""

import json
import os
import re
from typing import NamedTuple, Sequence
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, Tag
from trafilatura import fetch_url, extract
from readability import Document
from ollama import Client

import prompts

OLLAMA_MODEL = "command-r-longctx:latest"  # Change this to your desired Ollama model
UA_STRING = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"


class Citation(NamedTuple):
    sentence: str
    url: str


class FactCheckResult(NamedTuple):
    reference_supports_citation: bool
    brief_explanation: str


def get_random_wikipedia_article() -> str:
    """Fetch a random English Wikipedia article URL."""
    url = "https://en.wikipedia.org/wiki/Special:Random"
    response = requests.get(url, timeout=10, headers={"User-Agent": UA_STRING})
    response.raise_for_status()
    return response.url


def scrape_wikipedia_article(url: str) -> tuple[str, Tag]:
    response = requests.get(url, timeout=10, headers={"User-Agent": UA_STRING})
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    title = soup.find(id="firstHeading")
    content = soup.find(id="mw-content-text")

    if not title or not content or not isinstance(content, Tag):
        raise ValueError("Failed to find expected elements in the Wikipedia page")

    return title.text, content


def extract_sentences(content: Tag) -> list[str]:
    sentences = []
    for paragraph in content.find_all("p"):
        sentence = ""
        for child in paragraph.children:
            if isinstance(child, Tag):
                sentence += child.get_text()
            else:
                sentence += str(child).strip() + " "
        sentences.append(sentence)
    return sentences


def extract_citations_from_sentences(
    content: Tag, sentences: list[str]
) -> list[Citation]:
    citations = []
    for sentence in sentences:
        citation_matches = re.findall(r"\[(\d+)\]", sentence)
        for cite_num in citation_matches:
            ref_item = content.find("li", id=f"cite_note-{cite_num}")
            if ref_item:
                cite_url = ref_item.find("a", class_="external")
                if cite_url and cite_url.has_attr("href"):
                    href = cite_url["href"]
                    citations.append(Citation(sentence.strip(), href))
    return citations


def extract_citations(content: Tag) -> list[Citation]:
    sentences = extract_sentences(content)
    return extract_citations_from_sentences(content, sentences)


def scrape_citation_content(url: str, min_length: int = 200) -> str | None:
    """Scrape the text content from the citation URL, falling back to readability-lxml if needed."""
    try:
        # Try trafilatura first
        downloaded = fetch_url(url)
        if not downloaded:
            return None
        text = extract(
            downloaded,
            include_links=False,
            include_images=False,
            include_comments=False,
            favor_recall=True,
        )
        if text and len(text) >= min_length:
            return text

        # If trafilatura fails or returns too little content, use readability-lxml
        print("!! Failed, falling back")
        print(downloaded)
        doc = Document(downloaded)
        text = doc.summary()

        # Strip HTML tags from the `readability` output
        soup = BeautifulSoup(text, "lxml")
        clean_text = soup.get_text(separator=" ", strip=True)

        return clean_text if len(clean_text) >= min_length else None

    except Exception as e:
        print(f"Error scraping content from {url}: {e}")
        return None


def fact_check_citation(llm: Client, citation: Citation, content: str) -> FactCheckResult:
    """Use the LLM to fact-check the citation."""
    prompt = prompts.FACT_CHECK_TEMPLATE.format(citation=citation, content=content)
    response = llm.generate(
        model=OLLAMA_MODEL,
        prompt=prompt,
        format="json",
    )
    try:
        result = json.loads(response["response"])
        # Filter the keys to fit the NamedTuple in case the LLM returned more fields
        return FactCheckResult(**{k: result[k] for k in FactCheckResult._fields})
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Badly formatted LLM Response: {e}\n", response["response"])
        return FactCheckResult(False, f"Failed to parse LLM response: {e}")


def main() -> None:
    llm = Client(os.environ.get("OLLAMA_HOST", "http://sffpc:11434"))
    citations = []

    while True:
        try:
            article_url = get_random_wikipedia_article()
            title, content = scrape_wikipedia_article(article_url)
            citations = extract_citations(content)

            if citations:
                print(f"{title}\n{article_url}\n")
                break
            else:
                print(f"No citations in {title}, moving on...")
        except requests.RequestException as e:
            print(f"Error fetching article: {e}")
            break

    for i, citation in enumerate(citations, 1):
        print(f"Citation {i}: ...{citation.sentence[-90:]}")
        print(f"\t{citation.url}")

        citation_content = scrape_citation_content(citation.url)
        if citation_content:
            fact_check_result = fact_check_citation(llm, citation, citation_content)
            print(f"\tSupported: {fact_check_result.reference_supports_citation}")
            print(f"\tExplanation: {fact_check_result.brief_explanation}\n")
        else:
            print(f"\tFailed to extract content from the citation URL\n")


if __name__ == "__main__":
    main()
