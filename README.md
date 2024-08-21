# ackshually: Wikipedia Citation Scraper and Fact Checker

`ackshually` is a Python script that fetches random English Wikipedia articles, scrapes their inline citations, and then fact-checks them using an LLM by scraping the provided URLs for each citation. It helps verify if the given reference content supports the citation.

## Installation and Running

To run this script, you need to have [Poetry](https://python-poetry.org/) installed.
You'll also require an instance of [Ollama](https://ollama.io) running somewhere for the LLM functionality.

## Usage

1. Make sure you have a running Ollama server accessible from your machine.
2. Install the project dependencies with `poetry install`.
3. Run the script with `poetry run ./ackshually.py`.
4. The script will fetch a random Wikipedia article, scrape citations, and for each citation:
   - Scrape the content of the referenced URL.
   - Use the LLM to determine if the reference supports the citation and explain its decision.

## Example output

```
San Francisco Hep B Free
https://en.wikipedia.org/wiki/San_Francisco_Hep_B_Free

Citation 1: ...enient, free or low-cost testing opportunities at partnering health facilities and events.
	https://www.tuscaloosanews.com/article/20100503/News/606116438
	Supported: False
	Explanation: The reference content is inaccessible, therefore the citation cannot be verified.

Citation 2: ...enient, free or low-cost testing opportunities at partnering health facilities and events.
	https://medicalxpress.com/news/2012-06-hepatitis-liver-cancer-asian-americans.html
	Supported: True
	Explanation: The reference text supports the citation, as it contains information about the 'San Francisco Hep B Free' program and its aims.

Citation 3: ...l liver cancers among APIs. San Francisco has the highest liver cancer rate in the nation.
	https://www.tuscaloosanews.com/article/20100503/News/606116438
	Supported: False
	Explanation: The reference text could not be accessed to verify the citation.

Citation 4: ...It is estimated that one in ten people in the API community have an undiagnosed infection.
	https://globalnation.inquirer.net/81127/fil-ams-at-high-risk-of-hepatitis-b-free-testing-in-sf-bay-area
	Supported: False
	Explanation: The reference focuses on Hepatitis B risk among Filipino-Americans in the Bay Area, California, and doesn't mention APIs as the highest-risk group or San Francisco's statistics.

Citation 5: ...AsianWeek Foundation. Assemblywoman Ma served as spokesperson
	https://sanfrancisco.cbslocal.com/2014/05/16/viral-hepatitis-testing-offered-for-liver-destroying-disease/
	Supported: True
	Explanation: The reference content mentions Fiona Ma's role as a spokesperson for the San Francisco Hep B Free campaign, supporting the citation.
```

## What model is best to use?

I use [Command-R](https://ollama.com/library/command-r) on Ollama by running `ollama pull command-r` ahead of time. This works well on GPUs with ≥24GB and the model is excellent at following instructions, finding citations, RAG, and emitting JSON. There are many others to choose from, just update the `model` sent to `client.generate()` by hand.
