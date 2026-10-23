"""Structural and factual checks for the portfolio site. Run: python3 -m unittest discover -s tests -v"""
import re
import subprocess
import unittest
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PAGES = [
    "index.html",
    "oon-decision-tree.html",
    "expedited-loophole.html",
    "port-troubleshooting.html",
    "prior-auth-intake.html",
    "ai-clinical-review.html",
]

REQUIRED_TEXT = {
    "index.html": [
        "Asia Le", "I'm a nurse with experience in oncology and utilization management", "I want to move into product management", "30%", "fewer review delays", "reviewers using the new decision tree",
        "50%", "faster record retrieval", "CMS", "asiaqle@gmail.com", "linkedin.com/in/asiaqle",
        "Sunrise EHR", "eClinicalWorks", "Other work", "EMR lead for a CMS audit", "Initiative Award",
    ],
    "oon-decision-tree.html": [
        "50 reviewers in our 80-person department", "30%", "100%", "compliance on expedited and Part B requests", "Part B",
        "training", "compliance", "authorization", "three months",
    ],
    "expedited-loophole.html": [
        "90%", "Staff noticed", "endoscopy", "physical therapy", "cataract", "letter", "attest",
        "contact center", "same day",
    ],
    "port-troubleshooting.html": [
        "skill gap", "2–3", "check-off", "simulation", "75-minute", "confidence", "INS", "ONS",
    ],
    "prior-auth-intake.html": [
        "late", "fax", "portal", "wrong member", "receipt-to-intake lag", "overturn rate", "CMS",
    ],
    "ai-clinical-review.html": [
        "concept", "nurse", "medical director", "NCD", "LCD", "MCG", "overturn rate", "never denies",
        "Shadow mode", "isn't built",
    ],
}

FORBIDDEN_TEXT = [
    "80-person team", "100% reduction", "100% fewer",
    "already past their deadline", "has already passed", "clearer and smaller",
    "biggest declines", "not a knowledge gap",
    "Salesforce", "SharePoint", "OneNote", "password", "CityMD", "Getting 50 reviewers to one decision path", "Closing the expedited loophole", "The port nobody taught them to fix", "Fixing prior auth intake at the source", "person rollout", "Chosen by senior leadership", "Also shipped", "product manager in the making", "Now I fix the workflows", "Product portfolio", "databases that disagreed", "daily case report", "cut unnecessary expedited requests by", "873890",
    "didn't always agree", "databases that didn't agree",
]

PALETTE = {
    "--linen": "#ECE8E1", "--sand": "#D8CBB2", "--clay": "#CFC9C3", "--harbor": "#3F5F86",
    "--sky": "#6F9FC8", "--ink": "#1F3048", "--ink-2": "#4A5A6E", "--rule": "#C9C2B6", "--on-harbor": "#D9DFE8",
}

TOPBAR = {
    "index.html": "001 // Health tech product", "oon-decision-tree.html": "Case 01",
    "expedited-loophole.html": "Case 02", "port-troubleshooting.html": "Case 03",
    "prior-auth-intake.html": "Recommendation", "ai-clinical-review.html": "Concept",
}

INNER_PAGES = ["oon-decision-tree.html", "expedited-loophole.html", "port-troubleshooting.html",
               "prior-auth-intake.html", "ai-clinical-review.html"]

# Labels the approved redesign spec lists for the diagrams (2026-10-22). Other diagram words must come from the page.
APPROVED_DIAGRAM_LABELS = [
    "Network status", "Line of business", "Enrollment date", "Within 90 days?", "Established patient?",
    "Continuity of care", "In-network within 30 mi?", "Decision", "YES", "NO",
    "Same-day decision avoids the letter", "Providers learn “expedited” = fast",
    "Routine requests marked expedited", "Reviewers overloaded",
    "Current state", "The gap", "Desired state", "Senior nurses", "Check-off checklist", "New nurses",
    "Escalation policy", "Did we fix it?", "Leading indicators", "Guardrails", "Efficiency and adoption",
    "The model drafts", "The nurse decides",
]


def _words(text):
    return {w.strip(".,?:;“”\"'()").lower() for w in text.split()} - {""}


DIAGRAM_WHITELIST = set().union(*(_words(label) for label in APPROVED_DIAGRAM_LABELS))

CASE_TITLES = {
    "oon-decision-tree.html": "A decision tree for out-of-network reviews",
    "expedited-loophole.html": "Fixing a workaround in expedited reviews",
    "port-troubleshooting.html": "Teaching new nurses to troubleshoot implanted ports",
    "prior-auth-intake.html": "Moving prior authorization requests off fax",
    "ai-clinical-review.html": "AI-assisted clinical review",
}

STATUS = {
    "oon-decision-tree.html": "Shipped",
    "expedited-loophole.html": "Shipped",
    "port-troubleshooting.html": "Proposal",
    "prior-auth-intake.html": "Recommendation",
    "ai-clinical-review.html": "Concept",
}


@dataclass
class PageInfo:
    has_doctype: bool = False
    lang: str = ""
    has_viewport: bool = False
    title: str = ""
    description: str = ""
    og_title: str = ""
    og_description: str = ""
    stylesheets: list = field(default_factory=list)
    scripts: int = 0
    h1_count: int = 0
    hrefs: list = field(default_factory=list)
    img_alts: list = field(default_factory=list)
    text: str = ""
    status_texts: list = field(default_factory=list)


class _Parser(HTMLParser):
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}

    def __init__(self, info):
        super().__init__(convert_charrefs=True)
        self.info = info
        self.in_title = False
        self.skip = 0
        self.status_depth = None
        self.depth = 0
        self.status_buf = []
        self.chunks = []

    def handle_decl(self, decl):
        if decl.lower().startswith("doctype html"):
            self.info.has_doctype = True

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag not in self.VOID:
            self.depth += 1
        if tag == "html":
            self.info.lang = a.get("lang", "")
        elif tag == "meta":
            name, prop = a.get("name", ""), a.get("property", "")
            if name == "viewport":
                self.info.has_viewport = True
            elif name == "description":
                self.info.description = a.get("content", "")
            elif prop == "og:title":
                self.info.og_title = a.get("content", "")
            elif prop == "og:description":
                self.info.og_description = a.get("content", "")
        elif tag == "link" and "stylesheet" in a.get("rel", ""):
            self.info.stylesheets.append(a.get("href", ""))
        elif tag == "script":
            self.info.scripts += 1
            self.skip += 1
        elif tag == "style":
            self.skip += 1
        elif tag == "title":
            self.in_title = True
        elif tag == "h1":
            self.info.h1_count += 1
        elif tag == "img":
            self.info.img_alts.append(a.get("alt", ""))
        if "href" in a and tag in ("a", "link"):
            if tag == "a":
                self.info.hrefs.append(a["href"])
        if "status" in a.get("class", "").split() and self.status_depth is None:
            self.status_depth = self.depth
            self.status_buf = []

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip -= 1
        elif tag == "title":
            self.in_title = False
        if self.status_depth is not None and self.depth == self.status_depth:
            self.info.status_texts.append(" ".join("".join(self.status_buf).split()))
            self.status_depth = None
        if tag not in self.VOID:
            self.depth -= 1

    def handle_data(self, data):
        if self.in_title:
            self.info.title += data
            return
        if self.skip:
            return
        self.chunks.append(data)
        if self.status_depth is not None:
            self.status_buf.append(data)


def parse(page):
    info = PageInfo()
    p = _Parser(info)
    p.feed((ROOT / page).read_text(encoding="utf-8"))
    info.text = " ".join(" ".join(p.chunks).split())
    return info


class SiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pages = {page: parse(page) for page in PAGES}

    def test_page_head(self):
        for page, info in self.pages.items():
            with self.subTest(page=page):
                self.assertTrue(info.has_doctype, "missing <!doctype html>")
                self.assertEqual(info.lang, "en")
                self.assertTrue(info.has_viewport, "missing viewport meta")
                self.assertTrue(info.title.strip(), "empty <title>")
                self.assertTrue(info.description.strip(), "missing meta description")
                self.assertTrue(info.og_title.strip(), "missing og:title")
                self.assertTrue(info.og_description.strip(), "missing og:description")
                self.assertIn("styles.css", info.stylesheets)

    def test_no_scripts(self):
        for page, info in self.pages.items():
            with self.subTest(page=page):
                self.assertEqual(info.scripts, 0)

    def test_external_styles_only_google_fonts(self):
        for page, info in self.pages.items():
            for href in info.stylesheets:
                if href != "styles.css":
                    with self.subTest(page=page, href=href):
                        self.assertTrue(href.startswith("https://fonts.googleapis.com/"))

    def test_one_h1(self):
        for page, info in self.pages.items():
            with self.subTest(page=page):
                self.assertEqual(info.h1_count, 1)

    def test_internal_links_resolve(self):
        for page, info in self.pages.items():
            for href in info.hrefs:
                if href.startswith(("http", "mailto:", "#")):
                    continue
                target = href.split("#")[0]
                with self.subTest(page=page, href=href):
                    self.assertTrue((ROOT / target).is_file(), f"{href} does not exist")

    def test_no_root_relative_links(self):
        for page, info in self.pages.items():
            for href in info.hrefs + info.stylesheets:
                with self.subTest(page=page, href=href):
                    self.assertFalse(href.startswith("/"))

    def test_images_have_alt(self):
        for page, info in self.pages.items():
            for alt in info.img_alts:
                with self.subTest(page=page):
                    self.assertTrue(alt.strip())

    def test_required_facts(self):
        for page, facts in REQUIRED_TEXT.items():
            for fact in facts:
                with self.subTest(page=page, fact=fact):
                    self.assertIn(fact, self.pages[page].text)

    def test_forbidden_phrases(self):
        for page, info in self.pages.items():
            for phrase in FORBIDDEN_TEXT:
                with self.subTest(page=page, phrase=phrase):
                    self.assertNotIn(phrase, info.text)

    def test_status_labels(self):
        for page, label in STATUS.items():
            with self.subTest(page=page):
                self.assertIn(label, self.pages[page].status_texts)

    def test_css_has_dark_mode(self):
        css = (ROOT / "styles.css").read_text(encoding="utf-8")
        self.assertIn(":root", css)
        self.assertRegex(css, r"prefers-color-scheme:\s*dark")

    def test_css_has_overflow_guards(self):
        css = (ROOT / "styles.css").read_text(encoding="utf-8")
        block = re.search(r"\.table-wrap\s*\{([^}]*)\}", css)
        self.assertIsNotNone(block, ".table-wrap rule missing")
        self.assertRegex(block.group(1), r"overflow-x:\s*auto")
        self.assertRegex(css, r"overflow-wrap:\s*(anywhere|break-word)")

    def test_resume_pdf_present(self):
        pdf = ROOT / "assets" / "Asia_Le_Resume.pdf"
        self.assertTrue(pdf.is_file(), "assets/Asia_Le_Resume.pdf missing")
        self.assertEqual(pdf.read_bytes()[:4], b"%PDF")

    def test_resume_pdf_text(self):
        script = ("ObjC.import('PDFKit'); var d = $.PDFDocument.alloc.initWithURL("
                  "$.NSURL.fileURLWithPath('%s')); d.string.js" % (ROOT / "assets" / "Asia_Le_Resume.pdf"))
        text = " ".join(subprocess.run(["osascript", "-l", "JavaScript", "-e", script],
                                       capture_output=True, text=True, check=True).stdout.split())
        self.assertNotIn("873890", text)
        self.assertNotIn("License #", text)
        self.assertIn("50 reviewers across an 80- person department".replace("80- ", "80-"), text.replace("80- ", "80-"))
        self.assertIn("about 90% fewer unnecessary expedited requests", text)
        self.assertNotIn("denials", text)

    def test_no_old_resume_in_history(self):
        commits = subprocess.run(["git", "log", "--all", "--format=%H", "--", "assets/Asia_Le_Resume.pdf"],
                                 cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
        tmp = ROOT / ".superpowers" / "history-check.pdf"
        tmp.parent.mkdir(exist_ok=True)
        for commit in commits:
            blob = subprocess.run(["git", "show", commit + ":assets/Asia_Le_Resume.pdf"], cwd=ROOT,
                                  capture_output=True, check=False).stdout
            if not blob:
                continue
            tmp.write_bytes(blob)
            script = ("ObjC.import('PDFKit'); $.PDFDocument.alloc.initWithURL("
                      "$.NSURL.fileURLWithPath('%s')).string.js" % tmp)
            text = subprocess.run(["osascript", "-l", "JavaScript", "-e", script],
                                  capture_output=True, text=True, check=True).stdout
            with self.subTest(commit=commit[:7]):
                self.assertNotIn("873890", text)

    def test_homepage_links_resume(self):
        self.assertIn("assets/Asia_Le_Resume.pdf", self.pages["index.html"].hrefs)

    def test_private_files_not_tracked(self):
        tracked = subprocess.run(["git", "ls-files", "docs", "source", ".superpowers"], cwd=ROOT,
                                 capture_output=True, text=True, check=True).stdout
        self.assertEqual(tracked.strip(), "")

    def test_no_word_files_tracked(self):
        tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
        bad = [f for f in tracked.splitlines() if f.endswith(".docx") or "/~$" in f or f.startswith("~$")]
        self.assertEqual(bad, [])

    def test_private_files_not_in_history(self):
        history = subprocess.run(["git", "log", "--all", "--name-only", "--format="], cwd=ROOT,
                                 capture_output=True, text=True, check=True).stdout
        self.assertNotIn("docs/superpowers", history)

    @staticmethod
    def _tokens(block):
        return dict(re.findall(r"(--[a-z0-9-]+):\s*(#[0-9a-fA-F]{6})", block))

    @staticmethod
    def _contrast(a, b):
        def lum(hex_color):
            rgb = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
            lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
            return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]
        hi, lo = sorted([lum(a), lum(b)], reverse=True)
        return (hi + 0.05) / (lo + 0.05)

    def _css_blocks(self):
        css = (ROOT / "styles.css").read_text(encoding="utf-8")
        light = css.split("@media")[0]
        dark = re.search(r"prefers-color-scheme:\s*dark\)\s*\{(.*?)\}\s*\}", css, re.S)
        return light, (dark.group(1) if dark else "")

    def test_palette_tokens(self):
        light = self._tokens(self._css_blocks()[0])
        for name, value in PALETTE.items():
            with self.subTest(token=name):
                self.assertEqual(light.get(name, "").lower(), value.lower())

    def test_contrast_pairs(self):
        light, dark = self._css_blocks()
        lt, dk = self._tokens(light), self._tokens(dark)
        pairs = [("light ink-2 on linen", lt.get("--ink-2"), lt.get("--linen")),
                 ("light ink on linen", lt.get("--ink"), lt.get("--linen")),
                 ("on-harbor on harbor", lt.get("--on-harbor"), lt.get("--harbor")),
                 ("dark text on bg", dk.get("--text"), dk.get("--bg")),
                 ("dark text-2 on bg", dk.get("--text-2"), dk.get("--bg")),
                 ("dark accent on bg", dk.get("--accent"), dk.get("--bg")),
                 ("light text-2 on bg", lt.get("--text-2"), lt.get("--bg")),
                 ("light accent on bg", lt.get("--accent"), lt.get("--bg")),
                 ("light shipped pill", lt.get("--bg"), lt.get("--accent")),
                 ("dark shipped pill", dk.get("--bg"), dk.get("--accent")),
                 ("light band-muted on band", lt.get("--band-muted"), lt.get("--band")),
                 ("dark band-muted on band", dk.get("--band-muted"), dk.get("--band"))]
        for label, fg, bg in pairs:
            with self.subTest(pair=label):
                self.assertTrue(fg and bg, "token missing")
                self.assertGreaterEqual(self._contrast(fg, bg), 4.5)

    def test_fonts_loaded(self):
        for page, info in self.pages.items():
            fonts = [h for h in info.stylesheets if h.startswith("https://fonts.googleapis.com/")]
            with self.subTest(page=page):
                self.assertTrue(any(all(f in h for f in ("Playfair+Display", "Archivo", "Public+Sans")) for h in fonts))
                self.assertFalse(any("Fraunces" in h for h in fonts))

    def test_font_roles(self):
        css = (ROOT / "styles.css").read_text(encoding="utf-8")
        self.assertRegex(css, r'--serif:\s*"Playfair Display"')
        self.assertRegex(css, r'--sans:\s*"Public Sans"')
        self.assertRegex(css, r'--label:\s*"Archivo"')
        meta = re.search(r"\.meta, \.eyebrow, \.case-num\s*\{([^}]*)\}", css)
        self.assertIsNotNone(meta)
        self.assertIn("var(--label)", meta.group(1))
        self.assertRegex(meta.group(1), r"font-stretch:\s*125%")

    def test_topbar(self):
        for page in PAGES:
            html = (ROOT / page).read_text(encoding="utf-8")
            m = re.search(r'class="topbar"[^>]*>(.*?)</div>', html, re.S)
            with self.subTest(page=page):
                self.assertIsNotNone(m, "no .topbar")
                text = " ".join(re.sub(r"<[^>]+>", " ", m.group(1)).split())
                self.assertIn("Portfolio of Asia Le, RN · 2026", text)
                self.assertIn(TOPBAR[page], text)

    def test_home_structure(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        hero = re.search(r'<section class="hero"[^>]*>(.*?)</section>', html, re.S)
        self.assertIsNotNone(hero, "no .hero section")
        self.assertIn("<h1", hero.group(1))
        self.assertEqual(html.count('class="band"'), 1)
        band = re.search(r'class="band"[^>]*>(.*?)</section>', html, re.S).group(1)
        self.assertEqual(len(re.findall(r'class="stat"', band)), 4)
        self.assertLessEqual(len(re.findall(r'class="bloom"', html)), 3)
        self.assertEqual(re.findall(r'class="sec-num"[^>]*>([^<]+)<', html), ["001", "002", "003", "004"])

    @staticmethod
    def _diagrams(html):
        return re.findall(r'<svg[^>]*class="diagram"[^>]*>.*?</svg>', html, re.S)

    def test_one_diagram_per_inner_page(self):
        for page in INNER_PAGES:
            html = (ROOT / page).read_text(encoding="utf-8")
            svgs = self._diagrams(html)
            with self.subTest(page=page):
                self.assertEqual(len(svgs), 1)
                self.assertIn('role="img"', svgs[0])
                label = re.search(r'aria-label="([^"]*)"', svgs[0])
                self.assertTrue(label and label.group(1).strip())

    def test_diagram_labels_from_page(self):
        for page in INNER_PAGES:
            html = (ROOT / page).read_text(encoding="utf-8")
            svgs = self._diagrams(html)
            outside = re.sub(r"<svg.*?</svg>", " ", html, flags=re.S)
            outside = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", outside, flags=re.S)
            page_words = _words(re.sub(r"<[^>]+>", " ", outside).replace("&amp;", "&"))
            for svg in svgs:
                texts = re.findall(r"<(?:text|tspan)[^>]*>([^<]+)<", svg)
                for word in _words(" ".join(texts)):
                    with self.subTest(page=page, word=word):
                        self.assertTrue(word in page_words or word in DIAGRAM_WHITELIST, word)

    def test_svg_no_hardcoded_colors(self):
        for page in INNER_PAGES:
            for svg in self._diagrams((ROOT / page).read_text(encoding="utf-8")):
                with self.subTest(page=page):
                    self.assertNotRegex(svg, r'(fill|stroke)="#')

    def test_inner_pages_at_most_one_bloom(self):
        for page in INNER_PAGES:
            html = (ROOT / page).read_text(encoding="utf-8")
            with self.subTest(page=page):
                self.assertLessEqual(len(re.findall(r'class="bloom"', html)), 1)

    def test_ai_diagram_keeps_nurse_judgment(self):
        svg = self._diagrams((ROOT / "ai-clinical-review.html").read_text(encoding="utf-8"))[0]
        texts = " ".join(re.findall(r"<text[^>]*>([^<]+)<", svg))
        self.assertNotIn("MODEL DRAFTS", texts)
        for phrase in ("Decides whether", "Confirms the", "Edits, signs off"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, texts)
        self.assertIn("rules-based automation", re.search(r'aria-label="([^"]*)"', svg).group(1))

    def test_expedited_label_has_no_added_cause(self):
        svg = self._diagrams((ROOT / "expedited-loophole.html").read_text(encoding="utf-8"))[0]
        self.assertNotIn("feeds back", svg)

    def test_footer_focus_ring_visible(self):
        css = (ROOT / "styles.css").read_text(encoding="utf-8")
        self.assertRegex(css, r"\.site-footer a:focus-visible[^{]*\{[^}]*outline-color:\s*var\(--band-text\)")

    def test_flower_colors_in_style_not_attributes(self):
        svg = (ROOT / "assets" / "flower.svg").read_text(encoding="utf-8")
        self.assertNotRegex(svg, r'(fill|stroke)="var\(')

    def test_hero_italic(self):
        self.assertRegex((ROOT / "index.html").read_text(encoding="utf-8"), r"Hi, I'm <em>Asia</em>\.")

    def test_branch_labels_readable(self):
        css = (ROOT / "styles.css").read_text(encoding="utf-8")
        size = re.search(r"\.diagram \.lbl\s*\{[^}]*font-size:\s*(\d+)px", css)
        self.assertIsNotNone(size)
        self.assertGreaterEqual(int(size.group(1)), 12)

    def test_markers_use_plain_auto(self):
        for page in INNER_PAGES:
            with self.subTest(page=page):
                self.assertNotIn("auto-start-reverse", (ROOT / page).read_text(encoding="utf-8"))

    def test_about_structure(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        about = re.search(r'<section aria-labelledby="about">(.*?)</section>', html, re.S)
        self.assertIsNotNone(about)
        a = about.group(1)
        self.assertEqual(len(re.findall(r"<img\b", a)), 1)
        self.assertIn('alt="Asia standing on a wooden dock in front of a lake and a forested mountain"', a)
        self.assertEqual(len(re.findall(r'class="bloom"', a)), 1)
        self.assertIn("Lake Crescent, WA · Photo by Asia", a)
        self.assertIn(">Asia Le, BSN, RN<", a)
        for detail in ("MSN in Nursing Education", "Doodle", "Cat, my tabby, and Doodle", "pressure cooker"):
            with self.subTest(detail=detail):
                self.assertIn(detail, a)
        facts = re.search(r'<ul class="about-facts">(.*?)</ul>', a, re.S)
        self.assertIsNotNone(facts)
        for f in ("4×", "2020", "NYU degrees", "ABCD Award", "Published"):
            with self.subTest(fact=f):
                self.assertIn(f, facts.group(1))

    def test_about_has_no_employer_names(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        about = re.search(r'<section aria-labelledby="about">(.*?)</section>', html, re.S).group(1)
        for name in ("VNS", "Northwell", "Long Island Jewish"):
            with self.subTest(name=name):
                self.assertNotIn(name, about)
        self.assertIn("New York health plan", about)

    def test_about_image_size(self):
        img = ROOT / "assets" / "about.jpg"
        self.assertTrue(img.is_file())
        self.assertLessEqual(img.stat().st_size, 200 * 1024)
        out = subprocess.run(["sips", "-g", "pixelWidth", str(img)], capture_output=True, text=True, check=True).stdout
        self.assertLessEqual(int(re.search(r"pixelWidth:\s*(\d+)", out).group(1)), 900)

    def test_about_image_has_no_gps(self):
        img = ROOT / "assets" / "about.jpg"
        self.assertNotIn(b"GPS", img.read_bytes()[:65536])
        out = subprocess.run(["mdls", "-name", "kMDItemLatitude", str(img)], capture_output=True, text=True).stdout
        self.assertIn("(null)", out)

    def test_case_titles_match_homepage(self):
        home = (ROOT / "index.html").read_text(encoding="utf-8")
        for page, title in CASE_TITLES.items():
            html = (ROOT / page).read_text(encoding="utf-8")
            with self.subTest(page=page):
                self.assertIn(f'<span class="case-title">{title}</span>', home)
                self.assertRegex(html, r"<h1>" + re.escape(title) + r"</h1>")
                self.assertIn(f"<title>{title} · Asia Le</title>", html)

    def test_flower_asset_has_symbol(self):
        svg = ROOT / "assets" / "flower.svg"
        self.assertTrue(svg.is_file())
        self.assertIn('<symbol id="flower"', svg.read_text(encoding="utf-8"))

    def test_updated_resume_backs_site_metrics(self):
        text = subprocess.run(["textutil", "-convert", "txt", "-stdout",
                               str(ROOT / "source" / "Asia_Le_Resume_updated.docx")],
                              capture_output=True, text=True, check=True).stdout
        for fact in ("50 reviewers across an 80-person department", "90%"):
            with self.subTest(fact=fact):
                self.assertIn(fact, text)


if __name__ == "__main__":
    unittest.main()
