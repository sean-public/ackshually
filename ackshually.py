#!/usr/bin/env python3

"""
Wikipedia Citation Scraper and Fact Checker

This script fetches a random English Wikipedia article,
scrapes its contents, extracts inline citations,
and uses an LLM to fact-check the citations by scraping
the provided URL for each.
"""

import json
from typing import NamedTuple, Sequence
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, Tag
import trafilatura
from ollama import Client

import prompts


class Citation(NamedTuple):
    sentence: str
    url: str


class FactCheckResult(NamedTuple):
    reference_supports_citation: bool
    brief_explanation: str


def get_random_wikipedia_article() -> str:
    """Fetch a random English Wikipedia article URL."""
    url = "https://en.wikipedia.org/wiki/Special:Random"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.url


def scrape_wikipedia_article(url: str) -> tuple[str, Tag]:
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    title = soup.find(id="firstHeading")
    content = soup.find(id="mw-content-text")

    if not title or not content or not isinstance(content, Tag):
        raise ValueError("Failed to find expected elements in the Wikipedia page")

    return title.text, content


def extract_citations(content: Tag) -> list[Citation]:
    citations = []
    for paragraph in content.find_all("p"):
        sentence = ""
        for child in paragraph.children:
            if child.name == "sup" and "reference" in child.get("class", []):
                cite_link = child.find("a", href=True)
                if cite_link and isinstance(cite_link, Tag):
                    cite_id = cite_link["href"]
                    ref_item = content.find("li", id=cite_id[1:])
                    if ref_item and isinstance(ref_item, Tag):
                        cite_url = ref_item.find(
                            "a", class_="external", attrs={"href": True}
                        )
                        if cite_url and isinstance(cite_url, Tag):
                            href = cite_url.get("href")
                            if href and isinstance(href, str):
                                citations.append(Citation(sentence.strip(), href))
                sentence = ""  # Reset sentence after adding a citation
            else:
                if isinstance(child, Tag):
                    sentence += child.get_text()
                else:
                    sentence += str(child)
            if sentence.strip().endswith((".", "!", "?")):
                sentence = sentence.strip() + " "  # Keep space between sentences
    return citations


def scrape_citation_content(url: str) -> str:
    """Scrape the text content from the citation URL."""
    try:
        downloaded = trafilatura.fetch_url(url)
        text = trafilatura.extract(
            downloaded,
            include_links=False,
            include_images=False,
            include_comments=False,
            favor_recall=True,
        )
        return text or "Failed to extract content"
    except Exception as e:
        return f"Error scraping content: {e}"


def fact_check_citation(
    client: Client, citation: Citation, content: str
) -> FactCheckResult:
    """Use the LLM to fact-check the citation."""
    prompt = prompts.FACT_CHECK_TEMPLATE.format(citation=citation, content=content)
    response = client.generate(
        model="command-r-longctx:latest",  # Change this to any Ollama model you desire
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
    # Update this to point at your Ollama instance
    client = Client(host="http://ollama:11434")

    while True:
        try:
            article_url = get_random_wikipedia_article()
            title, content = scrape_wikipedia_article(article_url)
            citations = extract_citations(content)

            if citations:
                print(f"{title}\n{article_url}\n")
                break
        except requests.RequestException as e:
            print(f"Error fetching article: {e}")
            continue

    for i, citation in enumerate(citations, 1):
        print(f"Citation {i}: ...{citation.sentence[-90:]}")
        print(f"\t{citation.url}")

        citation_content = scrape_citation_content(citation.url)
        fact_check_result = fact_check_citation(client, citation, citation_content)

        print(f"\tSupported: {fact_check_result.reference_supports_citation}")
        print(f"\tExplanation: {fact_check_result.brief_explanation}\n")


if __name__ == "__main__":
    main()
