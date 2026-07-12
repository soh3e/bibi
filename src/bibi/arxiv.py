"""Fetch bibliography data from arXiv, given a URL or bare id.

The id-parsing regex and the result-to-dict field mapping are ported from
papis (papis/arxiv.py, papis/downloaders/arxiv.py).
"""

from __future__ import annotations

import re
from typing import Any

ARXIV_ABS_URL = "https://arxiv.org/abs"

# NOTE: sometimes an id is embedded in javascript too, so this regex is broad.
_ARXIVID_FORBIDDEN_CHARACTERS = r'"\(\)\s%!$^\'<>@,;:#?&'
_ARXIVID_URL_REGEX = re.compile(
    r"arxiv(.org|.com)?"
    r"(/abs|/pdf)?"
    r"\s*(=|:|/|\()\s*"
    r"(\"|')?"
    fr"(?P<arxivid>[^{_ARXIVID_FORBIDDEN_CHARACTERS}]+)"
    r'("|\'|\))?',
    re.I,
)

# Bare arXiv identifiers: new-style "2301.00001"/"2301.00001v2", or
# old-style "hep-th/9901001".
_BARE_ARXIVID_REGEX = re.compile(
    r"^(\d{4}\.\d{4,5}(v\d+)?|[a-z-]+(\.[A-Z]{2})?/\d{7}(v\d+)?)$",
    re.I,
)


def find_arxivid_in_text(text: str) -> str | None:
    """Find an arXiv identifier embedded in an arXiv URL/string, if any."""
    for match in _ARXIVID_URL_REGEX.finditer(text):
        arxivid = match.group("arxivid")
        if arxivid.endswith(".pdf"):
            arxivid = arxivid[:-4]
        return arxivid

    return None


def parse_arxiv_input(raw: str) -> str | None:
    """Turn a pasted arXiv URL or bare id into an arXiv id.

    :returns: an arXiv id, or *None* if *raw* doesn't look like one at all.
        This does not check that the id actually exists on arXiv -- that is
        left to :func:`fetch_entry`, which will simply come back empty.
    """
    raw = raw.strip()
    if not raw:
        return None

    arxivid = find_arxivid_in_text(raw)
    if arxivid:
        return arxivid

    if _BARE_ARXIVID_REGEX.match(raw):
        return raw

    return None


def result_to_dict(result: Any) -> dict[str, Any]:
    """Flatten an ``arxiv.Result`` into a plain bibliography dict."""
    data: dict[str, Any] = {
        "title": result.title,
        "authors": [author.name for author in result.authors],
        "year": result.published.year,
        "month": result.published.month,
        "abstract": result.summary.replace("\n", " "),
        "arxiv_id": result.get_short_id(),
        "primary_category": result.primary_category,
        "url": str(result.entry_id),
        "pdf_url": str(result.pdf_url),
        "type": "article",
    }

    if result.doi:
        data["doi"] = result.doi
    if result.journal_ref:
        data["journal_ref"] = result.journal_ref

    if result.comment:
        comment = result.comment.lower()
        if "thesis" in comment:
            if "phd" in comment:
                data["type"] = "phdthesis"
            elif "master" in comment:
                data["type"] = "mastersthesis"
            else:
                data["type"] = "thesis"

    return data


def fetch_entry(arxiv_id: str) -> dict[str, Any] | None:
    """Query the arXiv API for *arxiv_id* and return a bibliography dict.

    :returns: *None* if no entry is found for *arxiv_id*.
    """
    import arxiv

    client = arxiv.Client()
    try:
        results = list(client.results(arxiv.Search(id_list=[arxiv_id])))
    except arxiv.ArxivError:
        return None

    if not results:
        return None

    return result_to_dict(results[0])
