#!/usr/bin/env python3
"""غرفة أخبار السالفة — يجمع الأخبار العاجلة من مصادر عربية وأجنبية كل دقيقة.

يكتب breaking.json على فرع live-data (commit واحد يتبدّل كل مرة، حتى ما يكبر المستودع).
صفحة البث live/index.html تقرا هذا الملف.

تشغيل محلي لمرة وحدة:  python3 scripts/breaking.py --once --out /tmp/breaking.json
"""
import json, os, re, subprocess, sys, time, html, hashlib, urllib.request, urllib.parse
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"

def gnews(q, lang="ar"):
    if lang == "ar":
        return "https://news.google.com/rss/search?" + urllib.parse.urlencode({"q": q, "hl": "ar", "gl": "IQ", "ceid": "IQ:ar"})
    return "https://news.google.com/rss/search?" + urllib.parse.urlencode({"q": q, "hl": "en-US", "gl": "US", "ceid": "US:en"})

# (اسم المصدر بالعربي, الرابط, اللغة)
FEEDS = [
    ("الجزيرة", "https://www.aljazeera.net/aljazeerarss/a7c186be-1baa-4bd4-9d80-a84db769f779/73d0e1b4-532f-45ef-b135-bfdff8b8cab9", "ar"),
    ("بي بي سي عربي", "https://feeds.bbci.co.uk/arabic/rss.xml", "ar"),
    ("فرانس 24", "https://www.france24.com/ar/rss", "ar"),
    ("دويتشه فيله", "https://rss.dw.com/rdf/rss-ar-all", "ar"),
    ("آر تي عربي", "https://arabic.rt.com/rss/", "ar"),
    ("سكاي نيوز عربية", "https://www.skynewsarabia.com/web/rss", "ar"),
    ("سي إن إن بالعربية", "https://arabic.cnn.com/api/v1/rss/rss.xml", "ar"),
    ("الأناضول", "https://www.aa.com.tr/ar/rss/default?cat=guncel", "ar"),
    ("اندبندنت عربية", "https://www.independentarabia.com/rss.xml", "ar"),
    # أخبار العراق من كل الوكالات العراقية (شفق، السومرية، روداو، واع…) عبر أخبار Google
    ("*", gnews("العراق when:1d"), "ar"),
    ("*", gnews("عاجل العراق when:1d"), "ar"),
    ("*", gnews("بغداد OR البصرة OR أربيل OR الموصل when:1d"), "ar"),
    # أجنبية (تنترجم للعربي)
    ("بي بي سي", "https://feeds.bbci.co.uk/news/world/rss.xml", "en"),
    ("الجزيرة الإنجليزية", "https://www.aljazeera.com/xml/rss/all.xml", "en"),
    ("الغارديان", "https://www.theguardian.com/world/rss", "en"),
    ("نيويورك تايمز", "https://rss.nytimes.com/services/xml/rss/nyt/World.xml", "en"),
    ("سكاي نيوز", "https://feeds.skynews.com/feeds/rss/world.xml", "en"),
    ("*", gnews("site:reuters.com world when:1d", "en"), "en"),
    ("*", gnews("site:apnews.com world when:1d", "en"), "en"),
    ("*", gnews("Iraq when:1d", "en"), "en"),
]

SRC_AR = {  # أسماء المصادر اللي تجي من أخبار Google
    "Reuters": "رويترز", "AP News": "أسوشيتد برس", "Associated Press": "أسوشيتد برس", "BBC": "بي بي سي",
    "CNN": "سي إن إن", "Al Jazeera English": "الجزيرة الإنجليزية", "The Guardian": "الغارديان",
    "The New York Times": "نيويورك تايمز", "Bloomberg": "بلومبرغ", "AFP": "فرانس برس", "France 24": "فرانس 24",
    "Kurdistan24": "كردستان 24", "Rudaw": "روداو", "Shafaq News": "شفق نيوز", "The National": "ذا ناشيونال",
    "Al-Monitor": "المونيتور", "Washington Post": "واشنطن بوست", "The Washington Post": "واشنطن بوست",
    "Financial Times": "فايننشال تايمز", "Axios": "أكسيوس", "Politico": "بوليتيكو", "Fox News": "فوكس نيوز",
}

URGENT = re.compile(r"عاجل|breaking|urgent|عاجـل", re.I)
CATS = [
    ("iq", re.compile(r"العراق|عراقي|بغداد|البصرة|أربيل|اربيل|الموصل|كربلاء|النجف|كركوك|الأنبار|كردستان|السليمانية|ديالى|ذي قار|السوداني|الزيدي|الحشد|Iraq|Baghdad|Kurdistan|Erbil|Basra|Mosul", re.I)),
    ("sec", re.compile(r"قصف|هجوم|صاروخ|صواريخ|مسيرة|مسيّرة|انفجار|اشتباك|غارة|قتلى|قتيل|جرحى|اغتيال|عسكري|strike|attack|missile|drone|killed|explosion|troops", re.I)),
    ("eco", re.compile(r"نفط|برميل|الدولار|دينار|اقتصاد|أسعار|البورصة|أوبك|موازنة|oil|OPEC|dollar|economy|stocks|inflation|prices", re.I)),
    ("sport", re.compile(r"منتخب|مباراة|الدوري|كأس|فيفا|هدف|football|match|league|FIFA|goal", re.I)),
    ("tech", re.compile(r"ذكاء اصطناعي|تكنولوجيا|آبل|غوغل|جوجل|مايكروسوفت|ميتا|إنفيديا|AI |Apple|Google|Microsoft|Nvidia|OpenAI", re.I)),
]

def tag(el):
    return el.tag.rsplit("}", 1)[-1].lower()

def child(el, *names):
    for c in el:
        if tag(c) in names:
            return c
    return None

def text(el):
    return html.unescape(re.sub(r"<[^>]+>", "", (el.text or "") if el is not None else "")).strip()

def parse_ts(s):
    s = (s or "").strip()
    if not s:
        return None
    try:
        d = parsedate_to_datetime(s)
    except Exception:
        try:
            d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except Exception:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc)

def fetch(url, timeout=12):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/rss+xml,application/xml,text/xml,*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def parse_feed(name, url, lang):
    raw = fetch(url)
    root = ET.fromstring(raw)
    out = []
    for it in root.iter():
        if tag(it) not in ("item", "entry"):
            continue
        t = text(child(it, "title"))
        if not t:
            continue
        ln = child(it, "link")
        link = (ln.get("href") if ln is not None and ln.get("href") else text(ln)) if ln is not None else ""
        ts = parse_ts(text(child(it, "pubdate", "published", "updated", "date")))
        src = name
        se = child(it, "source")
        if name == "*":
            sname = text(se) if se is not None else ""
            m = re.match(r"^(.*)\s+[-–]\s+([^-–]{2,60})$", t)
            if m:
                t, tail = m.group(1).strip(), m.group(2).strip()
                sname = sname or tail
            src = SRC_AR.get(sname, sname) or "أخبار"
        out.append({"t": t, "link": link, "ts": ts, "src": src, "lang": lang})
    return out

AI_URL = "https://salfa-bdaqiqa.vercel.app/api/ai"
_last_ai = [0.0]

def translate_ai(titles):
    """ترجمة دفعة عناوين عبر المساعد الذكي بموقع السالفة (Gemini)."""
    prompt = ("ترجم هذه العناوين الإخبارية الإنجليزية إلى عربية فصحى مختصرة بأسلوب شريط الأخبار العاجلة. "
              "لا تضف أي شرح. رجّع فقط JSON array من نصوص بنفس الترتيب والعدد.\n" + json.dumps(titles, ensure_ascii=False))
    body = json.dumps({"task": "chat", "messages": [{"role": "user", "content": prompt}], "context": []}).encode()
    req = urllib.request.Request(AI_URL, data=body, headers={"Content-Type": "application/json", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=40) as r:
        txt = json.loads(r.read()).get("text", "")
    m = re.search(r"\[[\s\S]*\]", txt)
    arr = json.loads(m.group(0)) if m else []
    return [str(x).strip() for x in arr] if len(arr) == len(titles) else []

def translate(items, cache, status=None):
    todo = [i for i in items if i["lang"] == "en" and i["t"] not in cache]
    ok = bad = 0
    if todo and time.time() - _last_ai[0] > 420:
        _last_ai[0] = time.time()
        batch = [i["t"] for i in todo[:12]]
        try:
            res = translate_ai(batch)
            for a, b in zip(batch, res):
                if b:
                    cache[a] = b; ok += 1
            todo = [i for i in todo if i["t"] not in cache]
        except Exception as e:
            if status is not None:
                status["ترجمة_ذكاء_خطأ"] = type(e).__name__ + ": " + str(e)[:80]
    for i in todo[:15]:  # محاولة احتياطية
        try:
            q = urllib.parse.urlencode({"client": "gtx", "sl": "en", "tl": "ar", "dt": "t", "q": i["t"]})
            data = json.loads(fetch("https://translate.googleapis.com/translate_a/single?" + q, timeout=8))
            cache[i["t"]] = "".join(seg[0] for seg in data[0] if seg and seg[0]).strip()
            ok += 1
        except Exception as e:
            bad += 1
            if status is not None:
                status["ترجمة_خطأ"] = type(e).__name__ + ": " + str(e)[:80]
            if "429" in str(e):
                break
    if status is not None:
        status["ترجمة"] = f"{ok} نجحت / {bad} فشلت / {len(todo)} بالانتظار"
    for i in items:
        if i["lang"] == "en":
            if i["t"] in cache:
                i["orig"], i["t"] = i["t"], cache[i["t"]]
                i["tr"] = True
            else:
                i["skip"] = True  # ما نعرض إنكليزي بدون ترجمة

def norm_tokens(s):
    s = re.sub(r"[ً-ْـ]", "", s)
    s = re.sub(r"[إأآا]", "ا", s)
    s = re.sub(r"[^\w\s]", " ", s.lower())
    return {w for w in s.split() if len(w) > 2}

def clean_title(t):
    t = re.sub(r"^[\s#/|:\-–]*(عاجل|عاجـل|breaking)\s*[:|\-–/|]*\s*", "", t, flags=re.I)
    t = re.sub(r"^[\s/|:\-–]+", "", t)
    t = re.sub(r"\s*[|\-–]\s*(فيديو|صور|video|watch)\s*$", "", t, flags=re.I)
    return re.sub(r"\s+", " ", t).strip()

def collect(cache, status):
    now = datetime.now(timezone.utc)
    items = []
    with ThreadPoolExecutor(8) as ex:
        futs = {ex.submit(parse_feed, *f): f for f in FEEDS}
        for fu, f in futs.items():
            key = f[0] if f[0] != "*" else f[1].split("q=")[-1][:40]
            try:
                got = fu.result()
                status[key] = len(got)
                items += got
            except Exception as e:
                status[key] = "خطأ: " + type(e).__name__
    fresh = []
    for i in items:
        if not i["ts"] or i["ts"] < now - timedelta(hours=8) or i["ts"] > now + timedelta(minutes=10):
            continue
        i["urgent"] = bool(URGENT.search(i["t"]))
        i["t"] = clean_title(i["t"])
        if len(i["t"]) < 12:
            continue
        fresh.append(i)
    translate(fresh, cache, status)
    fresh = [i for i in fresh if not i.get("skip")]
    fresh.sort(key=lambda i: i["ts"], reverse=True)
    kept = []
    for i in fresh:
        tk = norm_tokens(i["t"])
        dup = None
        for k in kept:
            inter = len(tk & k["_tk"])
            if tk and k["_tk"] and inter / max(1, min(len(tk), len(k["_tk"]))) >= 0.7:
                dup = k
                break
        if dup:
            if i["src"] not in dup["also"] and i["src"] != dup["src"]:
                dup["also"].append(i["src"])
            dup["urgent"] = dup["urgent"] or i["urgent"]
            continue
        if sum(1 for k in kept if k["src"] == i["src"]) >= 10:
            continue
        i["_tk"], i["also"] = tk, []
        kept.append(i)
        if len(kept) >= 90:
            break
    out = []
    for i in kept:
        cat = next((c for c, rx in CATS if rx.search(i["t"] + " " + i.get("orig", ""))), "world")
        out.append({
            "id": hashlib.md5((i["orig"] if i.get("orig") else i["t"]).encode()).hexdigest()[:10],
            "t": i["t"], "src": i["src"], "also": i["also"][:4], "link": i["link"],
            "ts": i["ts"].strftime("%Y-%m-%dT%H:%M:%SZ"), "urgent": i["urgent"], "cat": cat,
            **({"tr": True} if i.get("tr") else {}),
        })
    # سقف للترجمات المخزونة
    if len(cache) > 600:
        for k in list(cache)[: len(cache) - 600]:
            cache.pop(k, None)
    return out

def publish(path, repo_dir):
    """يدفع breaking.json لفرع live-data كـ commit وحيد (force) حتى ما يتراكم تاريخ."""
    env = dict(os.environ, GIT_AUTHOR_NAME="Salfa News Bot", GIT_AUTHOR_EMAIL="bot@users.noreply.github.com",
               GIT_COMMITTER_NAME="Salfa News Bot", GIT_COMMITTER_EMAIL="bot@users.noreply.github.com")
    blob = subprocess.check_output(["git", "-C", repo_dir, "hash-object", "-w", path], env=env).decode().strip()
    tree_in = f"100644 blob {blob}\tbreaking.json\n"
    tree = subprocess.check_output(["git", "-C", repo_dir, "mktree"], input=tree_in.encode(), env=env).decode().strip()
    commit = subprocess.check_output(["git", "-C", repo_dir, "commit-tree", tree, "-m", "live news"], env=env).decode().strip()
    subprocess.run(["git", "-C", repo_dir, "push", "-q", "-f", "origin", f"{commit}:refs/heads/live-data"], check=True, env=env)

def main():
    once = "--once" in sys.argv
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "/tmp/breaking.json"
    duration = int(os.environ.get("DURATION", "0"))
    interval = int(os.environ.get("INTERVAL", "60"))
    repo_dir = os.environ.get("REPO_DIR", ".")
    cache, last_ids, t0 = {}, None, time.time()
    while True:
        status = {}
        try:
            items = collect(cache, status)
            ids = [i["id"] for i in items[:40]]
            doc = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "count": len(items),
                   "items": items, "sources": status}
            with open(out, "w", encoding="utf-8") as f:
                json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))
            print(time.strftime("%H:%M:%S"), len(items), "items", "| new" if ids != last_ids else "| same", flush=True)
            if not once and (ids != last_ids or int(time.time() - t0) % 600 < interval):
                publish(out, repo_dir)
                last_ids = ids
        except Exception as e:
            print("cycle error:", repr(e), flush=True)
        if once or time.time() - t0 + interval > duration:
            break
        time.sleep(interval)

if __name__ == "__main__":
    main()
