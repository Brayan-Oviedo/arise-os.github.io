"""
AriseOS LeadOS — 1000 Leads Pipeline
Scrapes Colombia (all cities) × all niches → dedup → score → outreach copy → dashboard JSON
Usage: python3 leads_1000_pipeline.py
"""
from __future__ import annotations
import json, os, re, subprocess, sys, time, hashlib
from pathlib import Path

BASE      = Path(__file__).parent
RUNNER    = Path(__file__).parent.parent / "AriseOS/plugins/LeadOS/skills/scrapling-engine/runner.py"
LEADS_DIR = BASE / "leads"
OUTPUT_JSON = BASE / "leads" / "leads_1000_final.json"
OUTPUT_CSV  = BASE / "leads" / "leads_1000_final.csv"

LEADS_DIR.mkdir(exist_ok=True)

# ── Scraping targets ──────────────────────────────────────────────────────────
CITIES = ["Bogotá", "Medellín", "Cali", "Barranquilla"]

MAPS_QUERIES = [
    "restaurante",
    "peluquería barbería",
    "tienda ropa boutique",
    "spa centro estética",
    "gimnasio fitness",
    "hotel hospedaje",
    "dentista odontología",
    "agencia marketing digital",
    "consultora empresa",
    "veterinaria",
    "panadería pastelería",
    "joyería bisutería",
    "fotógrafo fotografía",
    "academia escuela idiomas",
]

IG_QUERIES = [
    ("restaurante colombiano", "Colombia"),
    ("moda ropa mujer", "Bogotá"),
    ("negocio emprendimiento", "Medellín"),
    ("boutique tienda", "Cali"),
    ("salon belleza", "Bogotá"),
    ("gym fitness", "Colombia"),
    ("emprendedor colombia", "Colombia"),
    ("marca colombiana", "Colombia"),
]

# ── Outreach copy generator ───────────────────────────────────────────────────

def _detect_category(name: str, bio: str = "") -> str:
    t = (name + " " + bio).lower()
    if re.search(r'restaur|comida|food|caf[eé]|burger|pizza|sushi|bistro|panad|pastel', t):
        return "restaurante"
    if re.search(r'peluq|barber|salon|salón|belleza|beauty|spa|estética|uña|nail', t):
        return "belleza"
    if re.search(r'ropa|moda|boutique|fashion|cloth|wear|vestido|camis', t):
        return "moda"
    if re.search(r'gym|fitnes|deport|sport|ejercicio|entrena', t):
        return "fitness"
    if re.search(r'hotel|hosped|hospedaje|hostal|apart', t):
        return "hotel"
    if re.search(r'dent|odont|clínica|clinica|médic|medic|salud|farma', t):
        return "salud"
    if re.search(r'agencia|marketing|digital|publicidad|branding', t):
        return "agencia"
    if re.search(r'asesor|consult|abogad|jurídic', t):
        return "consultora"
    if re.search(r'foto|vídeo|video|produc|cine|media', t):
        return "creativo"
    if re.search(r'joya|reloj|watch|jewelry|bisut', t):
        return "joyería"
    if re.search(r'tech|tecnol|software|app|digit|celular|electr', t):
        return "tecnología"
    if re.search(r'vet|mascota|pet|animal', t):
        return "veterinaria"
    if re.search(r'academ|escuela|curso|taller|idioma|inglés', t):
        return "educación"
    return "otro"


def generate_outreach(lead: dict) -> dict:
    company = lead.get("company") or lead.get("name") or lead.get("display_name") or "tu negocio"
    category = lead.get("category", "otro")
    source   = lead.get("source", "google_maps")

    # Category-specific pain point
    pain = {
        "restaurante":  "muchos restaurantes pierden reservas por no tener web profesional",
        "belleza":      "los salones que tienen web y reservas online duplican sus citas",
        "moda":         "una landing bien diseñada multiplica las ventas online",
        "fitness":      "los gyms con web profesional llenan sus clases mucho más rápido",
        "hotel":        "los hoteles con buena presencia digital reciben más reservas directas",
        "salud":        "los consultorios con web profesional capturan más pacientes nuevos",
        "agencia":      "una landing premium demuestra tu capacidad mucho mejor que redes solas",
        "consultora":   "una web profesional genera más confianza y más clientes ideales",
        "creativo":     "tu trabajo merece un portafolio web que lo muestre como se debe",
        "joyería":      "una página de lujo convierte más compradores premium",
        "tecnología":   "una landing optimizada convierte más visitantes en clientes",
        "veterinaria":  "los dueños de mascotas buscan vet online — una web los captura",
        "educación":    "más inscripciones llegan cuando el proceso es fácil y digital",
        "otro":         "una web profesional puede traerte muchos más clientes",
    }.get(category, "una web profesional puede traerte muchos más clientes")

    dm = (
        f"Hola {company} 👋 Diseño landing pages que convierten visitas en clientes reales. "
        f"¿Te muestro demo gratis? Sin compromiso."
    )[:149]

    if source == "instagram":
        dm = (
            f"Hola 👋 Vi tu perfil y {pain}. "
            f"Diseño tu web en 24h. ¿Te muestro demo gratis?"
        )[:149]

    email_subj = f"Más clientes para {company} — idea rápida"
    email_body = f"""Hola equipo de {company},

Vi su negocio y tengo una idea concreta para ustedes: {pain}.

Soy Brayan de AriseOS. Diseño landing pages profesionales en 24-48h, enfocadas en convertir visitas en clientes reales.

¿15 minutos para mostrarles ejemplos de negocios similares en Colombia?

Quedo atento,
Brayan Oviedo — AriseOS
WhatsApp: +57 350 701 6717
brayan.oviedo@ceiba.com.co"""

    return {"outreach_dm": dm, "outreach_email_subject": email_subj, "outreach_email": email_body}


# ── Scoring ───────────────────────────────────────────────────────────────────

def score_lead(lead: dict) -> int:
    s = 0
    if lead.get("email"):   s += 30
    if lead.get("phone"):   s += 25
    if lead.get("website"): s += 15

    followers = lead.get("followers") or 0
    if followers >= 5000:  s += 20
    elif followers >= 1000: s += 12
    elif followers >= 500:  s += 6

    rating = lead.get("rating") or 0
    if rating >= 4.5:  s += 10
    elif rating >= 4.0: s += 6

    reviews = lead.get("review_count") or 0
    if reviews >= 50:  s += 8
    elif reviews > 10: s += 4

    bio = lead.get("bio") or ""
    if len(bio) > 50:  s += 4

    return min(s, 100)


def tier(score: int) -> str:
    if score >= 75: return "A"
    if score >= 55: return "B"
    if score >= 40: return "C"
    return "D"


# ── Load existing JSONL ───────────────────────────────────────────────────────

def load_existing() -> list:
    leads, seen = [], set()
    for f in sorted(LEADS_DIR.glob("*.jsonl")):
        if "pipeline" in f.name or "final" in f.name:
            continue
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                lead = json.loads(line)
            except Exception:
                continue
            key = _lead_key(lead)
            if key and key not in seen:
                seen.add(key)
                leads.append(lead)
    print(f"[LOAD] {len(leads)} existing leads", flush=True)
    return leads


def _lead_key(lead: dict) -> str | None:
    phone   = re.sub(r'\D', '', lead.get("phone") or "")
    email   = (lead.get("email") or "").lower().strip()
    name    = (lead.get("name") or lead.get("display_name") or "").strip()
    website = (lead.get("website") or "").lower().strip().rstrip("/")
    if phone and len(phone) >= 7:
        return f"phone:{phone}"
    if email and "@" in email:
        return f"email:{email}"
    if website:
        return f"web:{website}"
    if name and len(name) > 3:
        return f"name:{name.lower()}"
    return None


# ── Run scraper ────────────────────────────────────────────────────────────────

def run_scraper(source: str, query: str, location: str, limit: int = 20) -> list:
    slug = re.sub(r'[^a-z0-9]+', '_', f"{source}_{query}_{location}".lower())[:60]
    cache = LEADS_DIR / f"scraped_{slug}.jsonl"
    if cache.exists() and cache.stat().st_size > 10:
        lines = [l for l in cache.read_text().splitlines() if l.strip()]
        print(f"[CACHE] {source} '{query}' {location}: {len(lines)} cached", flush=True)
        return [json.loads(l) for l in lines]

    print(f"[SCRAPE] {source} '{query}' @ {location} limit={limit} ...", flush=True)
    cmd = [
        sys.executable, str(RUNNER),
        "--source", source,
        "--query", query,
        "--location", location,
        "--limit", str(limit),
        "--max-leads", str(limit),
        "--mode", "pro",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        lines  = [l for l in result.stdout.splitlines() if l.strip()]
        leads  = []
        for l in lines:
            try:
                leads.append(json.loads(l))
            except Exception:
                pass
        print(f"[DONE] {source} '{query}' {location}: {len(leads)} leads", flush=True)
        if leads:
            cache.write_text("\n".join(json.dumps(l, ensure_ascii=False) for l in leads))
        return leads
    except subprocess.TimeoutExpired:
        print(f"[TIMEOUT] {source} '{query}' {location}", flush=True)
        return []
    except Exception as e:
        print(f"[ERROR] {source} '{query}' {location}: {e}", flush=True)
        return []


# ── Main pipeline ─────────────────────────────────────────────────────────────

def main():
    TARGET = 1000
    all_leads: list[dict] = []
    seen_keys: set[str]   = set()

    def add(raw: dict):
        k = _lead_key(raw)
        if k and k in seen_keys:
            return False
        # Must have at least one contact
        if not (raw.get("phone") or raw.get("email") or raw.get("website")):
            return False
        if k:
            seen_keys.add(k)

        company  = raw.get("name") or raw.get("display_name") or raw.get("username") or ""
        city_raw = raw.get("address") or raw.get("location") or ""
        city     = ""
        for c in CITIES:
            if c.lower() in city_raw.lower():
                city = c; break

        category = _detect_category(
            company + " " + (raw.get("bio") or "") + " " + (raw.get("category") or "")
        )
        sc = score_lead(raw)
        outreach = generate_outreach({**raw, "company": company, "category": category})

        enriched = {
            "id":            hashlib.md5((company + (raw.get("phone") or "") + (raw.get("email") or "")).encode()).hexdigest()[:12],
            "source":        raw.get("source", "google_maps"),
            "name":          raw.get("username") or raw.get("display_name") or "",
            "company":       company,
            "phone":         raw.get("phone") or "",
            "email":         raw.get("email") or "",
            "website":       raw.get("website") or "",
            "address":       raw.get("address") or "",
            "city":          city,
            "category":      category,
            "followers":     raw.get("followers") or 0,
            "rating":        raw.get("rating") or 0,
            "review_count":  raw.get("review_count") or 0,
            "bio":           raw.get("bio") or "",
            "profile_url":   raw.get("profile_url") or "",
            "score":         sc,
            "tier":          tier(sc),
            "contact_available": bool(raw.get("phone") or raw.get("email")),
            "status":        "nuevo",
            "outreach_dm":           outreach["outreach_dm"],
            "outreach_email_subject": outreach["outreach_email_subject"],
            "outreach_email":        outreach["outreach_email"],
            "createdAt":     "2026-06-12T00:00:00.000Z",
        }
        all_leads.append(enriched)
        return True

    # 1. Load existing
    for raw in load_existing():
        add(raw)
    print(f"[STATUS] After existing: {len(all_leads)} unique leads with contact", flush=True)

    # 2. Google Maps — all niches × all cities
    for city in CITIES:
        for query in MAPS_QUERIES:
            if len(all_leads) >= TARGET:
                break
            needed  = TARGET - len(all_leads)
            limit   = min(20, needed + 5)
            results = run_scraper("google_maps", query, city, limit)
            added   = sum(1 for r in results if add(r))
            print(f"[STATUS] {len(all_leads)}/{TARGET} (+{added})", flush=True)
            if len(all_leads) >= TARGET:
                break
        if len(all_leads) >= TARGET:
            break

    # 3. Instagram — fallback if still short
    if len(all_leads) < TARGET:
        for query, location in IG_QUERIES:
            if len(all_leads) >= TARGET:
                break
            needed  = TARGET - len(all_leads)
            limit   = min(30, needed + 5)
            results = run_scraper("instagram", query, location, limit)
            added   = sum(1 for r in results if add(r))
            print(f"[STATUS] {len(all_leads)}/{TARGET} (+{added})", flush=True)

    final = all_leads[:TARGET]
    final.sort(key=lambda x: x["score"], reverse=True)

    a = sum(1 for l in final if l["tier"] == "A")
    b = sum(1 for l in final if l["tier"] == "B")
    c = sum(1 for l in final if l["tier"] == "C")
    with_email = sum(1 for l in final if l["email"])
    with_phone = sum(1 for l in final if l["phone"])

    print(f"\n[DONE] {len(final)} leads | A:{a} B:{b} C:{c} | email:{with_email} phone:{with_phone}", flush=True)

    # Save JSON
    OUTPUT_JSON.write_text(json.dumps(final, ensure_ascii=False, indent=2))
    print(f"[SAVED] {OUTPUT_JSON}", flush=True)

    # Save CSV
    headers = ["id","source","company","name","phone","email","website","address","city",
                "category","score","tier","followers","rating","review_count","status",
                "outreach_dm","outreach_email_subject"]
    rows = [headers]
    for l in final:
        rows.append([str(l.get(h,"")) for h in headers])
    csv_text = "﻿" + "\n".join(",".join(f'"{v.replace(chr(34),chr(34)*2)}"' for v in row) for row in rows)
    OUTPUT_CSV.write_text(csv_text)
    print(f"[SAVED] {OUTPUT_CSV}", flush=True)

    print(f"\n=== PIPELINE COMPLETE ===")
    print(f"Leads JSON : {OUTPUT_JSON}")
    print(f"Leads CSV  : {OUTPUT_CSV}")
    print(f"Total      : {len(final)}")
    print(f"A-tier     : {a}  (score ≥75, best for outreach)")
    print(f"B-tier     : {b}  (score 55-74)")
    print(f"C-tier     : {c}  (score 40-54)")
    print(f"With email : {with_email}")
    print(f"With phone : {with_phone}")

    return final


if __name__ == "__main__":
    main()
