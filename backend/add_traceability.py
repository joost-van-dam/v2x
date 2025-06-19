# ─── add_traceability.py ─────────────────────────────────────────────
"""
Gebruik:
    python add_traceability.py <pad-naar-tests>  (bv. backend/tests)

•  Zoekt alle *.py in de meegegeven map (rekursief)
•  Plakt vóór elke test_… functie één regel:
       @pytest.mark.tc("<trace-id>")
•  Trace-ID’s worden bepaald via de mapping hieronder.
•  Niet-bestaande ID in mapping  → script slaat die test over
•  Verschijnt er al zo’n marker, dan wordt hij vervangen.

Het script maakt eerst een backup-copy *.orig* van elk gewijzigd bestand.
Daarnaast schrijft het een CSV ‘trace_matrix.csv’ met Requirement-ID,
Testcase-ID en bestandslocatie.
"""
from pathlib import Path
import re, sys, csv, textwrap

# ─── 1. Vul hier je mapping Testfunctie → Trace-ID ────────────────
#     (exacte functienaam, geen parameters)
TRACE_MAP = {
    # backend/tests/test_chargepoint_rpc_routes.py
    "test_set_and_get_alias_success":       "TC-U01",
    "test_set_and_get_alias_not_registered":"TC-U02",
    "test_get_settings_not_registered":     "TC-U03",
    "test_enable_disable_and_get":          "TC-U04",
    "test_send_generic_command_and_404":    "TC-U05",
    "test_remote_start_v16_variations":     "TC-U06",
    "test_remote_start_v201_variations":    "TC-U07",
    "test_remote_stop_v16_and_v201_and_404":"TC-U08",
    "test_set_current_v16_and_v201_and_404":"TC-U09",
    "test_configuration_v16_and_v201_full_logic":"TC-U10",
    "test_list_cps_filters_and_all":        "TC-U11",
    "test_invalid_paths_return_404":        "TC-U12",

    # test_chargepoint_session.py
    "test_listen_calls_route_and_disconnect":"TC-U13",
    "test_send_call_invokes_parser_and_returns":"TC-U14",
    "test_send_call_logs_and_handles_no_response":"TC-U15",

    # test_ocpp_command_strategy.py (grofweg één ID voor hele file)
    "test_v16_remote_start_default":        "TC-U16",

    # test_connect_charge_point_and_list.py
    "test_charge_point_connect_and_list":   "TC-I01",

    # test_e2e_rpc_commands.py
    "test_remote_start_and_stop_via_http":  "TC-I02",
    "test_configuration_via_http":          "TC-I03",
    "test_list_before_and_after_connect":   "TC-E01",
    "test_set_alias_and_get_settings":      "TC-E02",
    "test_enable_disable_and_settings":     "TC-E03",
    "test_meter_values":                    "TC-E04",
}

# ─── 2. Mapping Requirement-ID → lijst Testcase-ID’s ───────────────
REQ_MATRIX = {
    "BE-1": ["TC-U01", "TC-E02"],
    "BE-2": ["TC-U05","TC-U09","TC-U10","TC-U13","TC-U14","TC-U15","TC-U16"],
    "BE-3": ["TC-U02"],
    "BE-4": ["TC-U03","TC-U04","TC-U12","TC-E03"],
    "BE-5": ["TC-U11"],
    "BE-6": [],
    "FE-1": ["TC-I01","TC-E01","TC-E02","TC-E03"],
    "FE-2": ["TC-I02"],
    "FE-3": ["TC-U06","TC-U07","TC-U08","TC-I03","TC-E04"],
    "FE-4": [],
    "FE-5": [],
    "FE-6": [],
    "FE-7": [],
}

MARK_RE = re.compile(r"^\s*@pytest\.mark\.tc\(.*?\)\s*$", re.M)

def process_file(path: Path):
    txt = path.read_text(encoding="utf-8")
    changed = False
    for func, tc in TRACE_MAP.items():
        pat = re.compile(rf"(^\s*def\s+{func}\s*\()", re.M)
        m = pat.search(txt)
        if not m:
            continue
        start = m.start()
        # verwijder bestaande marker (indien aanwezig)
        txt = MARK_RE.sub("", txt, count=0)
        # opnieuw zoeken (posities kunnen veranderd zijn)
        m = pat.search(txt)
        if not m:
            continue
        indent = re.match(r"^\s*", m.group(0)).group(0)
        marker = f"{indent}@pytest.mark.tc(\"{tc}\")\n"
        txt = txt[:m.start()] + marker + txt[m.start():]
        changed = True
    if changed:
        path.rename(path.with_suffix(path.suffix + ".orig"))
        path.write_text(txt, encoding="utf-8")
    return changed

def main():
    if len(sys.argv) != 2:
        print("Usage: python add_traceability.py <tests_root>")
        sys.exit(1)
    root = Path(sys.argv[1])
    if not root.is_dir():
        print("Directory not found:", root)
        sys.exit(1)

    rows = []
    for p in root.rglob("test_*.py"):
        if process_file(p):
            print("Updated", p.relative_to(root.parent))
        # zoek markers in (eventueel) gewijzigde file
        txt = p.read_text(encoding="utf-8")
        for m in re.finditer(r"@pytest\.mark\.tc\(\"([^\"]+)\"\)", txt):
            tc = m.group(1)
            rows.append((tc, str(p.relative_to(root.parent))))

    # matrix CSV
    with open("trace_matrix.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["RequirementID", "TestcaseID"])
        for rid, tcs in REQ_MATRIX.items():
            for tc in tcs:
                w.writerow([rid, tc])
    print("CSV trace_matrix.csv generated.")

if __name__ == "__main__":
    main()
# ────────────────────────────────────────────────────────────────
