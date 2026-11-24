#!/usr/bin/env python3
"""CargoFeed aggregator — fetch RSS/Atom sources, merge with last-good data, render static index.

Stdlib only. Runs locally and in GitHub Actions (cron). Failure-tolerant:
a source that fails keeps its last-fetched items until they age out.
"""
import json, re, sys, html, time, urllib.request, urllib.parse, pathlib, datetime, email.utils
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parent
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"}
TIMEOUT = 30
MAX_PER_SOURCE = 10
MAX_AGE_DAYS = 21
MAX_TOTAL = 90
NOW = datetime.datetime.now(datetime.timezone.utc)

def localname(tag):
    return tag.rsplit("}", 1)[-1].lower()

def text_of(elem, names):
    for child in elem.iter():
        if localname(child.tag) in names and child.text:
            return child.text.strip()
    return ""

def link_of(item):
    for child in item.iter():
        if localname(child.tag) == "link":
            href = child.attrib.get("href")
            if href:
                return href.strip()
            if child.text and child.text.strip().startswith("http"):
                return child.text.strip()
    return ""

def media_of(item):
    thumb = ""
    for child in item.iter():
        ln = localname(child.tag)
        if ln == "thumbnail" and child.attrib.get("url", "").startswith("http"):
            thumb = child.attrib["url"]
            break
        if ln in ("content", "enclosure"):
            u = child.attrib.get("url", "")
            t = child.attrib.get("type", "")
            m = child.attrib.get("medium", "")
            if u.startswith("http") and (t.startswith("image") or m == "image"):
                return u
    return thumb

TAG_RE = re.compile(r"<[^>]+>")

def clean(t, n=240):
    t = TAG_RE.sub(" ", t or "")
    t = html.unescape(t)
    t = re.sub(r"\[[^\]]{0,40}\]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    if len(t) > n:
        t = t[:n].rsplit(" ", 1)[0] + "…"
    return t

def norm_link(l):
    try:
        p = urllib.parse.urlsplit(l)
        q = [x for x in p.query.split("&") if x and not x.startswith("utm_")]
        return urllib.parse.urlunsplit((p.scheme, p.netloc.lower(), p.path.rstrip("/"), "&".join(q), ""))
    except Exception:
        return l

def parse_dt(s):
    if not s:
        return None
    try:
        return email.utils.parsedate_to_datetime(s)
    except Exception:
        pass
    try:
        return datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None

def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read()

def parse_feed(xml_bytes):
    root = ET.fromstring(xml_bytes)
    items = []
    for elem in root.iter():
        if localname(elem.tag) not in ("item", "entry"):
            continue
        title = clean(text_of(elem, ("title",)), 200)
        link = link_of(elem)
        dt = parse_dt(text_of(elem, ("pubdate", "published", "updated", "date")))
        desc = clean(text_of(elem, ("description", "summary", "content", "encoded")))
        img = media_of(elem)
        if title and link:
            items.append({"title": title, "link": link, "date": dt.isoformat() if dt else None,
                          "desc": desc, "img": img})
    return items

def load_sources():
    sources = []
    for line in (ROOT / "feeds.txt").read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 2:
            sources.append({"name": parts[0], "url": parts[1],
                            "cats": [c.strip() for c in (parts[2] if len(parts) > 2 else "misc").split(",") if c.strip()],
                            "color": parts[3] if len(parts) > 3 else "#1e3a8a",
                            "max_age": int(parts[4]) if len(parts) > 4 and parts[4].isdigit() else MAX_AGE_DAYS})
    return sources

def rel_time(iso):
    if not iso:
        return ""
    try:
        dt = datetime.datetime.fromisoformat(iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        s = (NOW - dt).total_seconds()
        if s < 3600: return f"{max(1, int(s//60))} min ago"
        if s < 86400: return f"{int(s//3600)} hr ago"
        return f"{int(s//86400)} day{'s' if int(s//86400) != 1 else ''} ago"
    except Exception:
        return ""

def main():
    old = {}
    fj = ROOT / "feed.json"
    if fj.exists():
        try:
            for it in json.loads(fj.read_text()).get("items", []):
                old[norm_link(it["link"])] = it
        except Exception:
            pass

    status, fresh = {}, []
    for src in load_sources():
        try:
            raw = fetch(src["url"])
            got = parse_feed(raw)[:MAX_PER_SOURCE]
            status[src["name"]] = {"ok": True, "fetched": len(got)}
            for it in got:
                it["source"] = src["name"]
                it["color"] = src["color"]
                it["cats"] = src["cats"]
                fresh.append(it)
        except Exception as e:
            status[src["name"]] = {"ok": False, "error": str(e)[:120]}
        time.sleep(1.2)

    merged = {}
    for it in fresh:
        merged[norm_link(it["link"])] = it
    # keep last-good items for sources that failed
    for lk, it in old.items():
        if lk not in merged:
            src_ok = next((s for s in status.values() if s.get("ok")), None)
            it_stale = it.get("source")
            if it_stale and not status.get(it_stale, {}).get("ok"):
                merged[lk] = it
    merged.update({})  # noop, clarity

    items = list(merged.values())
    age_by_source = {s["name"]: s["max_age"] for s in load_sources()}
    def dt_of(it):
        try:
            return datetime.datetime.fromisoformat(it.get("date") or "")
        except Exception:
            return datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
    def fresh_enough(it):
        d = dt_of(it)
        if d is None or d.year < 2000:
            return True
        tol = age_by_source.get(it.get("source"), MAX_AGE_DAYS)
        return d >= NOW - datetime.timedelta(days=tol)
    items = [it for it in items if fresh_enough(it)]
    items.sort(key=dt_of, reverse=True)
    items = items[:MAX_TOTAL]

    doc = {"generated_at": NOW.isoformat(), "status": status, "item_count": len(items), "items": items}
    fj.write_text(json.dumps(doc, indent=1, ensure_ascii=False))

    render(doc)
    ok = sum(1 for s in status.values() if s.get("ok"))
    print(f"OK {ok}/{len(status)} sources, {len(items)} items")
    for name, s in status.items():
        print(f"  {'✓' if s.get('ok') else '✗'} {name}: {s.get('fetched', s.get('error', ''))}")

CARD = """<article class="feed-item bg-white rounded-lg shadow-sm overflow-hidden flex flex-col sm:flex-row hover:shadow-md transition {extra}" data-cats="{cats}" data-search="{search}">
{media}
<div class="p-6 sm:w-2/3 flex flex-col justify-between">
<div>
<span class="text-xs font-bold uppercase tracking-wide" style="color:{color}">{source}</span>
<h2 class="text-xl font-bold mt-1 mb-2 leading-snug"><a href="{link}" target="_blank" rel="noopener ugc" class="hover:text-orange-600 transition">{title}</a></h2>
<p class="text-gray-600 text-sm mb-4">{desc}</p>
</div>
<div class="flex items-center justify-between mt-4">
<span class="text-xs text-gray-500">{when} &bull; via {source}</span>
<a href="{link}" target="_blank" rel="noopener ugc" class="theme-accent text-white px-4 py-2 rounded text-sm font-semibold theme-accent-hover transition">Read More</a>
</div>
</div>
</article>"""

AD_BLOCK = """<div class="w-full h-24 ad-space my-4 feed-item" data-cats="ad">
<span>In-Feed Horizontal Ad</span>
<span class="text-xs text-gray-400 mt-1">(Responsive: 100% width)</span>
</div>"""

def esc(s):
    return html.escape(s or "", quote=True)

def render(doc):
    items = doc["items"]
    cards = []
    for i, it in enumerate(items):
        media = ""
        if it.get("img"):
            media = f'<div class="sm:w-1/3 h-48 sm:h-auto bg-gray-200"><img src="{esc(it["img"])}" alt="" loading="lazy" class="w-full h-full object-cover" onerror="this.parentElement.innerHTML=\'&lt;div class=&quot;w-full h-full img-placeholder flex items-center justify-center&quot;&gt;[Image unavailable]&lt;/div&gt;\'"></div>'
        else:
            initials = "".join(w[0] for w in it["source"].split()[:2]).upper()
            media = f'<div class="sm:w-1/3 h-48 sm:h-auto img-placeholder flex-col gap-1"><span class="text-3xl font-black" style="color:{esc(it.get("color","#9ca3af"))}">{esc(initials)}</span><span class="text-xs">CargoFeed</span></div>'
        extra = "hidden-extra" if i >= 12 else ""
        cards.append(CARD.format(
            extra=extra, cats=",".join(it.get("cats", [])), color=esc(it.get("color", "#1e3a8a")),
            source=esc(it["source"]), link=esc(it["link"]), title=esc(it["title"]),
            desc=esc(it.get("desc", "")), when=esc(rel_time(it.get("date"))),
            media=media, search=esc((it["title"] + " " + it.get("desc", "") + " " + it["source"]).lower()),
        ))
        if i == 5:
            cards.append(AD_BLOCK)

    items_jsonld = json.dumps([{"@type": "ListItem", "position": i + 1,
        "name": it["title"], "url": it["link"]} for i, it in enumerate(items[:30])], ensure_ascii=False)

    tpl = (ROOT / "template.html").read_text()
    out = (tpl.replace("<!--FEED_ITEMS-->", "\n".join(cards) or "<p class='text-gray-500 p-8'>Feed sources are warming up — check back shortly.</p>")
              .replace("<!--UPDATED-->", NOW.strftime("%Y-%m-%d %H:%M UTC"))
              .replace("<!--ITEM_COUNT-->", str(len(items)))
              .replace("<!--JSONLD_ITEMS-->", items_jsonld))
    (ROOT / "index.html").write_text(out)

if __name__ == "__main__":
    main()
