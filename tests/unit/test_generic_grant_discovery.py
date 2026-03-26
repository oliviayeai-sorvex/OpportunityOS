from services.generic_grant_discovery import GenericGrantDiscovery


def test_extract_candidate_links_prefers_deep_grant_paths() -> None:
    html = """
    <html><body>
      <a href="/grants-and-funding">Grants Listing</a>
      <a href="/grants-and-funding/energy-performance-services-grant-round-1">Energy Performance Services Grant Round 1</a>
      <a href="/about-us">About</a>
      <a href="https://external.example.com/funding-opportunity">External Funding Opportunity</a>
      <a href="/media/news-item">News</a>
    </body></html>
    """
    d = GenericGrantDiscovery()
    links = d.extract_candidate_links("https://www.nsw.gov.au/grants-and-funding", html)
    assert links
    top_url, top_text = links[0]
    assert "energy-performance-services-grant-round-1" in top_url
    assert "Grant Round 1" in top_text


def test_site_detection_known_vs_unknown() -> None:
    d = GenericGrantDiscovery()
    known = d.detect_site("https://www.nsw.gov.au/grants-and-funding")
    unknown = d.detect_site("https://example.com/funding")
    assert known["type"] == "KNOWN"
    assert known["parser"] == "nsw_parser"
    assert unknown["type"] == "UNKNOWN"


def test_validation_requires_title_and_amount_or_deadline() -> None:
    d = GenericGrantDiscovery()
    assert d._is_valid_structured({"title": "My Grant", "amount": "AUD 100,000", "deadline": None}) is True
    assert d._is_valid_structured({"title": "My Grant", "amount": None, "deadline": "2026-12-31"}) is True
    assert d._is_valid_structured({"title": "My Grant", "amount": None, "deadline": None}) is False


def test_extract_relevant_sections_focuses_on_criteria_snippets() -> None:
    d = GenericGrantDiscovery()
    text = (
        "Welcome to the grants portal with general navigation and media links. "
        "Eligibility: Applicants must be based in NSW and have fewer than 20 employees. "
        "Funding available up to AUD 50,000. "
        "Contact and privacy information follow."
    )
    extracted = d.extract_relevant_sections(text)
    assert "Eligibility:" in extracted
    assert "fewer than 20 employees" in extracted
    assert "Funding available" in extracted


def test_page_type_detection_by_link_count() -> None:
    html = "<html><body>" + "".join([f'<a href="/grants/{i}">Grant {i}</a>' for i in range(40)]) + "</body></html>"
    d = GenericGrantDiscovery()
    links = [(f"https://example.com/grants/{i}", f"Grant {i}") for i in range(40)]
    page_type, signals = d._detect_page_type(html=html, links=links)
    assert page_type == "LISTING"
    assert signals["listing_score"] > 0


def test_candidate_link_filter_and_pattern_boost() -> None:
    html = """
    <html><body>
      <a href="/about">About</a>
      <a href="/grants/alpha">Alpha Grant</a>
      <a href="/grants/beta">Beta Grant</a>
      <a href="/news/updates">News</a>
    </body></html>
    """
    d = GenericGrantDiscovery()
    links = d.extract_candidate_links("https://example.com/grants", html)
    assert links
    assert any("grants/alpha" in url for url, _ in links)


def test_canonical_url_removes_tracking_params() -> None:
    d = GenericGrantDiscovery()
    raw = "https://example.com/grants/item/?utm_source=x&gclid=123&page=2"
    canonical = d._canonical_url(raw)
    assert "utm_source" not in canonical
    assert "gclid" not in canonical
    assert "page=2" in canonical


def test_dedupe_link_records_uses_canonicalized_urls() -> None:
    d = GenericGrantDiscovery()
    links = [
        ("https://example.com/grants/item?utm_source=a", "Item"),
        ("https://example.com/grants/item?utm_source=b", "Item"),
        ("https://example.com/grants/item?page=2", "Item"),
    ]
    deduped = d._dedupe_link_records(links)
    assert len(deduped) == 2
