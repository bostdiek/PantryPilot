from bs4 import BeautifulSoup

from src.services.ai.html_extractor import HTMLExtractionService


def test_clean_attributes_filters_unsafe_schemes():
    svc = HTMLExtractionService()

    html = '<div><a href="javascript:alert(1)">x</a>'
    html += '<a href="/relative/path">rel</a>'
    html += '<img src="data:image/png;base64,iVBORw0KGgo" alt="ok"/>'
    html += '<img src="file:///etc/passwd"/>'
    html += "</div>"

    soup = BeautifulSoup(html, "html.parser")

    svc._clean_attributes(soup)

    anchors = soup.find_all("a")
    # first anchor should have no href
    assert "href" not in anchors[0].attrs
    # second anchor keeps relative href
    assert anchors[1]["href"] == "/relative/path"

    imgs = soup.find_all("img")
    # data image should be preserved
    assert any("data:image" in (i.get("src") or "") for i in imgs)
    # file: src should be removed
    assert all(not (i.get("src") and i.get("src").startswith("file:")) for i in imgs)


def test_resolve_urls_makes_absolute_and_drops_unsafe():
    svc = HTMLExtractionService()

    html = '<div><a href="/rel/path">link</a>'
    html += '<a href="javascript:evil">bad</a>'
    html += '<img src="/images/pic.jpg"/>'
    html += '<img src="file:///etc/hosts"/>'
    html += "</div>"

    soup = BeautifulSoup(html, "html.parser")

    base = "https://example.com/some/page"
    svc._resolve_urls(soup, base)

    anchors = soup.find_all("a")
    assert anchors[0]["href"] == "https://example.com/rel/path"
    # the javascript link should have been removed
    assert "href" not in anchors[1].attrs

    imgs = soup.find_all("img")
    assert imgs[0]["src"] == "https://example.com/images/pic.jpg"
    # file: src should have been removed
    assert "src" not in imgs[1].attrs
