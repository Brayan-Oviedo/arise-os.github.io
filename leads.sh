#!/usr/bin/env bash
# AriseOS — LeadOS Colombia Runner
# Generates 1000+ high-quality leads across categories
# Usage: bash leads.sh [category] [limit]
# Requires: pip install scrapling[all] dnspython && scrapling-install

set -euo pipefail

RUNNER="../AriseOS/plugins/LeadOS/skills/scrapling-engine/runner.py"
OUTPUT_DIR="./leads"
LIMIT=${2:-250}
CATEGORY=${1:-"all"}

mkdir -p "$OUTPUT_DIR"

timestamp() { date +"%Y%m%d_%H%M%S"; }
log() { echo "[AriseOS LeadOS] $*"; }

run_search() {
  local source="$1" query="$2" location="$3" outfile="$4" limit="$5"
  log "→ $source | $query @ $location | limit:$limit"
  python3 "$RUNNER" \
    --source "$source" \
    --query "$query" \
    --location "$location" \
    --limit "$limit" \
    --mode pro \
    2>>"$OUTPUT_DIR/runner.log" \
    | tee "$outfile"
  local count
  count=$(wc -l < "$outfile" 2>/dev/null || echo 0)
  log "  ✓ $count leads → $outfile"
}

run_audifonos() {
  log "═══ AUDÍFONOS & AUDIO ═══"
  run_search google_maps "tienda audífonos accesorios audio" "Bogotá Colombia"     "$OUTPUT_DIR/audifonos_bogota.jsonl"     100
  run_search google_maps "tienda audífonos auriculares"       "Medellín Colombia"   "$OUTPUT_DIR/audifonos_medellin.jsonl"   100
  run_search google_maps "tienda audio bluetooth tecnología"  "Cali Colombia"       "$OUTPUT_DIR/audifonos_cali.jsonl"       50
  run_search instagram   "tienda audífonos colombia"          "Colombia"            "$OUTPUT_DIR/audifonos_ig.jsonl"         50
  log "  → Audifonos total: ~300 leads"
}

run_relojes() {
  log "═══ RELOJES & RELOJERÍA ═══"
  run_search google_maps "relojería relojes joyas"            "Bogotá Colombia"     "$OUTPUT_DIR/relojes_bogota.jsonl"       100
  run_search google_maps "tienda de relojes relojería"        "Medellín Colombia"   "$OUTPUT_DIR/relojes_medellin.jsonl"     100
  run_search google_maps "relojería relojes Barranquilla"     "Colombia"            "$OUTPUT_DIR/relojes_barranquilla.jsonl" 50
  run_search instagram   "relojería relojes lujo colombia"    "Colombia"            "$OUTPUT_DIR/relojes_ig.jsonl"           50
  log "  → Relojes total: ~300 leads"
}

run_aromas() {
  log "═══ AROMAS & FRAGANCIAS ═══"
  run_search google_maps "tienda aromas perfumes velas"       "Bogotá Colombia"     "$OUTPUT_DIR/aromas_bogota.jsonl"        100
  run_search google_maps "tienda fragancias aromas"           "Medellín Colombia"   "$OUTPUT_DIR/aromas_medellin.jsonl"      100
  run_search google_maps "perfumería aromas difusores"        "Cali Colombia"       "$OUTPUT_DIR/aromas_cali.jsonl"          50
  run_search instagram   "tienda aromas colombia fragancias"  "Colombia"            "$OUTPUT_DIR/aromas_ig.jsonl"            50
  log "  → Aromas total: ~300 leads"
}

run_tecnologia() {
  log "═══ TECNOLOGÍA & ACCESORIOS ═══"
  run_search google_maps "tienda tecnología celulares accesorios" "Colombia"        "$OUTPUT_DIR/tech_colombia.jsonl"        100
  log "  → Tech total: ~100 leads"
}

merge_all() {
  log "═══ MERGEANDO TODOS LOS LEADS ═══"
  local merged="$OUTPUT_DIR/all_leads_$(timestamp).jsonl"
  cat "$OUTPUT_DIR"/*.jsonl | sort -u > "$merged" 2>/dev/null || true
  local total
  total=$(wc -l < "$merged" 2>/dev/null || echo 0)
  log "✓ TOTAL CONSOLIDADO: $total leads únicos → $merged"

  # Dedup by phone + convert to CSV
  python3 - <<'PYEOF'
import json, csv, sys, os, glob

output_dir = './leads'
files = glob.glob(os.path.join(output_dir, '*.jsonl'))
seen_phones, seen_emails = set(), set()
all_leads = []

for f in files:
    if 'all_leads' in f:
        continue
    with open(f) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                lead = json.loads(line)
            except json.JSONDecodeError:
                continue
            phone = (lead.get('phone') or '').replace(' ','').replace('-','')
            email = (lead.get('email') or '').lower()
            key = phone or email
            if not key:
                continue
            if phone in seen_phones or email in seen_emails:
                continue
            if phone: seen_phones.add(phone)
            if email: seen_emails.add(email)
            all_leads.append(lead)

csv_file = os.path.join(output_dir, f'leads_colombia_final.csv')
if all_leads:
    keys = ['source','name','display_name','company','address','phone','email','website','category','city','followers','rating','review_count','contact_available']
    with open(csv_file, 'w', newline='', encoding='utf-8-sig') as cf:
        writer = csv.DictWriter(cf, fieldnames=keys, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(all_leads)
    print(f'[AriseOS LeadOS] ✓ CSV final: {len(all_leads)} leads únicos → {csv_file}')
else:
    print('[AriseOS LeadOS] Sin leads para exportar')
PYEOF
}

case "$CATEGORY" in
  audifonos) run_audifonos ;;
  relojes)   run_relojes ;;
  aromas)    run_aromas ;;
  tech)      run_tecnologia ;;
  all|*)
    log "Ejecutando todas las categorías (target: 1000+ leads Colombia)"
    run_audifonos
    run_relojes
    run_aromas
    run_tecnologia
    merge_all
    log ""
    log "═══════════════════════════════════════"
    log "  AriseOS LeadOS — Colombia completado"
    log "  Archivos en: $OUTPUT_DIR/"
    log "  CSV final: $OUTPUT_DIR/leads_colombia_final.csv"
    log "  Importa el CSV al dashboard: dashboard.html"
    log "═══════════════════════════════════════"
    ;;
esac
