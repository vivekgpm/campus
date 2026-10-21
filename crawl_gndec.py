"""
Crawl a client-rendered (React/Vite) site into Markdown files for a RAG knowledge base.

Setup:
    pip install playwright requests
    playwright install chromium
Run:
    python crawl_gndec.py

Output (./kb):
    pages/*.md   one file per rendered page, with source URL + scrape date
    pdfs/*.pdf   every PDF linked from the site (parse these separately)
    api/*.json   JSON responses the site fetched (often the cleanest data)
    report.txt   pages that look empty/failed/skipped, to review by hand

Politeness: robots.txt is honoured (Disallow rules plus Crawl-delay), every
request waits out a throttle, and concurrent fetching is never used.
"""
import asyncio
import hashlib
import json
import re
import time
from datetime import date
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from playwright.async_api import async_playwright

BASE = "https://gndecb.ac.in/"
HOST = urlparse(BASE).netloc
MAX_PAGES = 300
USER_AGENT = "CampusBuddyRAGCrawler/1.0 (educational RAG demo; contact: placement@gndecb.ac.in)"
REQUEST_DELAY = 1.5  # seconds between requests; a robots.txt Crawl-delay overrides this if larger
OUT = Path("kb")
for sub in ("pages", "pdfs", "api"):
    (OUT / sub).mkdir(parents=True, exist_ok=True)

# Runs in the browser: converts headings/tables to Markdown, strips nav/footer.
EXTRACT_JS = """
() => {
  const links = [...document.querySelectorAll('a[href]')].map(a => a.href);
  document.querySelectorAll('nav, header, footer, script, style, noscript').forEach(e => e.remove());
  const root = document.querySelector('main') || document.body;
  root.querySelectorAll('h1,h2,h3,h4').forEach(h => {
    h.textContent = '\\n' + '#'.repeat(+h.tagName[1]) + ' ' + h.textContent.trim() + '\\n';
  });
  root.querySelectorAll('table').forEach(t => {
    const rows = [...t.querySelectorAll('tr')].map(r =>
      '| ' + [...r.children].map(c => c.innerText.trim().replace(/\\s+/g, ' ')).join(' | ') + ' |');
    if (rows.length > 1) {
      const cols = (rows[0].match(/[|]/g).length - 1);
      rows.splice(1, 0, '|' + ' --- |'.repeat(cols));
    }
    const pre = document.createElement('pre');
    pre.textContent = '\\n' + rows.join('\\n') + '\\n';
    t.replaceWith(pre);
  });
  return { title: document.title, links, text: root.innerText };
}
"""


def fname(url: str, ext: str) -> str:
    """Readable path slug + short URL hash, so two different URLs can never collide."""
    path = urlparse(url).path.strip("/") or "home"
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", path).strip("_")[:80] or "home"
    digest = hashlib.sha256(url.encode()).hexdigest()[:8]
    return f"{slug}_{digest}{ext}"


def clean(url: str) -> str:
    return urldefrag(url)[0].rstrip("/")


class Throttle:
    """Keeps at least `delay` seconds between requests (async and sync variants)."""

    def __init__(self, delay: float):
        self.delay = max(0.0, delay)
        self.last = 0.0

    def _due_in(self) -> float:
        return self.delay - (time.monotonic() - self.last)

    async def wait_async(self):
        gap = self._due_in()
        if gap > 0:
            await asyncio.sleep(gap)
        self.last = time.monotonic()

    def wait_sync(self):
        gap = self._due_in()
        if gap > 0:
            time.sleep(gap)
        self.last = time.monotonic()


def load_robots() -> RobotFileParser:
    """Fetch and parse /robots.txt. Falls back to allow-all when it is unreachable."""
    rp = RobotFileParser()
    url = urljoin(BASE, "/robots.txt")
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": USER_AGENT})
        head = r.text[:200].lower()
        if r.ok and "<html" not in head:
            rp.parse(r.text.splitlines())
            print(f"robots.txt loaded ({len(r.text.splitlines())} lines)")
            return rp
        print(f"robots.txt unusable (HTTP {r.status_code}); allowing all URLs")
    except Exception as e:
        print(f"robots.txt unreachable ({e}); allowing all URLs")
    rp.parse(["User-agent: *", "Allow: /"])
    return rp


def allowed(robots: RobotFileParser, url: str) -> bool:
    try:
        return robots.can_fetch(USER_AGENT, url)
    except Exception:
        return True


async def main():
    queue, queued, seen, pdfs, notes = [clean(BASE)], {clean(BASE)}, set(), set(), []
    api_hits = {}

    robots = load_robots()
    throttle = Throttle(REQUEST_DELAY)
    for agent in (USER_AGENT, "*"):
        d = robots.crawl_delay(agent)
        if d:
            throttle.delay = max(throttle.delay, float(d))
            break
    print(f"throttle: {throttle.delay}s between requests\n")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page()

        async def on_response(resp):
            try:
                if "json" in resp.headers.get("content-type", "") and resp.request.resource_type in ("fetch", "xhr"):
                    body = await resp.body()
                    if len(body) < 2_000_000:
                        api_hits[resp.url] = body
            except Exception:
                pass

        page.on("response", on_response)

        while queue and len(seen) < MAX_PAGES:
            url = queue.pop(0)
            if url in seen:
                continue
            if not allowed(robots, url):
                notes.append(f"SKIPPED (robots.txt) {url}")
                seen.add(url)
                continue

            await throttle.wait_async()
            try:
                await page.goto(url, wait_until="networkidle", timeout=45_000)
                # scroll to trigger lazy-loaded sections
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(800)
                data = await page.evaluate(EXTRACT_JS)
            except Exception as e:
                notes.append(f"FAILED {url}: {e}")
                continue
            finally:
                seen.add(url)

            for href in data["links"]:
                href = clean(href)
                p = urlparse(href)
                if p.scheme not in ("http", "https"):
                    continue
                if p.path.lower().endswith(".pdf"):
                    pdfs.add(href)
                elif p.netloc == HOST and href not in seen and href not in queued:
                    queued.add(href)
                    queue.append(href)

            text = re.sub(r"\n{3,}", "\n\n", data["text"]).strip()
            if len(text) < 300:
                notes.append(f"THIN ({len(text)} chars) {url}")
            (OUT / "pages" / fname(url, ".md")).write_text(
                f"---\nsource: {url}\ntitle: {data['title']}\nscraped: {date.today()}\n---\n\n{text}\n",
                encoding="utf-8",
            )
            print(f"[{len(seen)}] {url} ({len(text)} chars)")

        await browser.close()

    for url, body in api_hits.items():
        name = hashlib.sha256(url.encode()).hexdigest()[:10]
        (OUT / "api" / f"{name}.json").write_text(
            json.dumps({"source": url, "data": json.loads(body)}, indent=1), encoding="utf-8"
        )

    saved = 0
    for url in sorted(pdfs):
        if not allowed(robots, url):
            notes.append(f"SKIPPED (robots.txt) {url}")
            continue
        throttle.wait_sync()
        try:
            r = requests.get(url, timeout=60, headers={"User-Agent": USER_AGENT})
            if r.ok:
                (OUT / "pdfs" / fname(url, ".pdf")).write_bytes(r.content)
                saved += 1
            else:
                notes.append(f"PDF FAILED {url}: HTTP {r.status_code}")
        except Exception as e:
            notes.append(f"PDF FAILED {url}: {e}")

    (OUT / "report.txt").write_text("\n".join(notes) or "all pages OK", encoding="utf-8")
    print(f"\nDone: {len(seen)} pages, {len(api_hits)} API responses, "
          f"{saved}/{len(pdfs)} PDFs. See kb/report.txt")


asyncio.run(main())