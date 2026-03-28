#!/usr/bin/env python3
"""
LoadCalc QA Test Suite
Run after any change to capCity, geocode, or voice parsing logic.

Usage:
    python3 test_loadcalc.py          # all tests
    python3 test_loadcalc.py --live   # include live Nominatim geocode tests (slower, rate-limited)
"""

import re
import sys
import time

# ── capCity logic (mirror of JS implementation) ──────────────────────────────

STATE_MAP = {
    'Alabama':'AL','Alaska':'AK','Arizona':'AZ','Arkansas':'AR','California':'CA',
    'Colorado':'CO','Connecticut':'CT','Delaware':'DE','Florida':'FL','Georgia':'GA',
    'Hawaii':'HI','Idaho':'ID','Illinois':'IL','Indiana':'IN','Iowa':'IA','Kansas':'KS',
    'Kentucky':'KY','Louisiana':'LA','Maine':'ME','Maryland':'MD','Massachusetts':'MA',
    'Michigan':'MI','Minnesota':'MN','Mississippi':'MS','Missouri':'MO','Montana':'MT',
    'Nebraska':'NE','Nevada':'NV','New Hampshire':'NH','New Jersey':'NJ','New Mexico':'NM',
    'New York':'NY','North Carolina':'NC','North Dakota':'ND','Ohio':'OH','Oklahoma':'OK',
    'Oregon':'OR','Pennsylvania':'PA','Rhode Island':'RI','South Carolina':'SC',
    'South Dakota':'SD','Tennessee':'TN','Texas':'TX','Utah':'UT','Vermont':'VT',
    'Virginia':'VA','Washington':'WA','West Virginia':'WV','Wisconsin':'WI','Wyoming':'WY'
}

STATES_ABBR = '|'.join(STATE_MAP.values())

def cap_city(s):
    """Python mirror of JS capCity — must produce identical output."""
    result = s.strip()
    result = re.sub(r'\b\w', lambda m: m.group().upper(), result.lower())
    # Uppercase 2-letter state abbreviations
    result = re.sub(
        r'\b(' + STATES_ABBR.replace('|', '|').lower().title() + r')\b',
        lambda m: m.group().upper(), result, flags=re.I
    )
    # More direct approach: just uppercase any 2-letter word that's a state abbr
    for abbr in STATE_MAP.values():
        result = re.sub(r'\b' + abbr + r'\b', abbr, result, flags=re.I)
    # Add comma before state abbreviation if missing
    if ',' not in result:
        result = re.sub(
            r'\s+(' + STATES_ABBR + r')(\s*\d*\s*)$',
            r', \1\2', result, flags=re.I
        )
    # Handle full state names
    for name, abbr in STATE_MAP.items():
        pattern = r'\b' + name + r'\s*$'
        if re.search(pattern, result, re.I):
            result = re.sub(pattern, abbr, result, flags=re.I)
            if ',' not in result:
                result = re.sub(
                    r'\s+(' + STATES_ABBR + r')\s*$',
                    r', \1', result, flags=re.I
                )
            break
    return result.strip()


# ── Test Cases ───────────────────────────────────────────────────────────────

CAP_CITY_TESTS = [
    # (input, expected) — covers voice, typed, GPS, autocomplete paths
    # Voice input (full state names)
    ('nashville tennessee',       'Nashville, TN'),
    ('dallas texas',              'Dallas, TX'),
    ('columbus ohio',             'Columbus, OH'),
    ('kansas city missouri',      'Kansas City, MO'),
    ('indianapolis indiana',      'Indianapolis, IN'),
    ('albany new york',           'Albany, NY'),
    ('el paso texas',             'El Paso, TX'),
    ('fort worth texas',          'Fort Worth, TX'),
    ('north canton ohio',         'North Canton, OH'),
    ('new york new york',         'New York, NY'),
    ('west palm beach florida',   'West Palm Beach, FL'),
    ('north charleston south carolina', 'North Charleston, SC'),

    # Typed input (abbreviations, no comma)
    ('nashville tn',              'Nashville, TN'),
    ('Dallas TX',                 'Dallas, TX'),
    ('north canton oh',           'North Canton, OH'),
    ('san antonio tx',            'San Antonio, TX'),
    ('el paso tx',                'El Paso, TX'),

    # Already formatted (should not double-comma)
    ('Dallas, TX',                'Dallas, TX'),
    ('Nashville, TN',             'Nashville, TN'),
    ('North Canton, OH',          'North Canton, OH'),

    # Edge cases
    ('  dallas  tx  ',            'Dallas, TX'),      # extra whitespace
    ('DALLAS TX',                 'Dallas, TX'),      # all caps
    ('dallas tx 75201',           'Dallas, TX 75201'), # with zip
]

VOICE_PARSE_TESTS = [
    # (raw transcript, expected_origin, expected_dest, expected_rate)
    ('dallas texas to nashville tennessee rate 850',    'Dallas, TX',    'Nashville, TN', '850'),
    ('from columbus ohio to kansas city missouri rate 1200', 'Columbus, OH', 'Kansas City, MO', '1200'),
    ('north canton oh to jefferson oh rate 650',        'North Canton, OH', 'Jefferson, OH', '650'),
    ('dallas tx to nashville tn $950',                  'Dallas, TX',    'Nashville, TN', '950'),
    ('el paso texas to san antonio texas rate 400',     'El Paso, TX',   'San Antonio, TX', '400'),
    # "route" misheard as "rate" by speech recognition
    ('dallas texas to nashville tennessee route 850',   'Dallas, TX',    'Nashville, TN', '850'),
    ('north canton ohio to jefferson ohio route 650',   'North Canton, OH', 'Jefferson, OH', '650'),
]

# Geocode tests — only run with --live flag (hits Nominatim API)
GEOCODE_TESTS = [
    # (input, expected_lat_range, description)
    ('Jefferson, OH',     (41.5, 42.0),   'Should be village in Ashtabula County, NOT Jefferson County'),
    ('Springfield, OH',   (39.7, 40.1),   'Clark County'),
    ('Columbus, OH',      (39.8, 40.1),   'Franklin County'),
    ('Dallas, TX',        (32.6, 32.9),   'Dallas city, not Dallas County centroid'),
    ('Kansas City, MO',   (39.0, 39.2),   'Kansas City proper'),
    ('Portland, OR',      (45.4, 45.6),   'Portland Oregon, not other Portlands'),
]


def run_cap_city_tests():
    print("═══ capCity Tests ═══")
    passed = failed = 0
    for inp, expected in CAP_CITY_TESTS:
        got = cap_city(inp)
        if got == expected:
            print(f"  ✅ {inp!r:40s} → {got}")
            passed += 1
        else:
            print(f"  ❌ {inp!r:40s} → {got!r} (expected {expected!r})")
            failed += 1
    print(f"  {'─'*50}")
    print(f"  {passed} passed, {failed} failed\n")
    return failed


def run_voice_parse_tests():
    print("═══ Voice Parse Tests ═══")
    passed = failed = 0
    for transcript, exp_origin, exp_dest, exp_rate in VOICE_PARSE_TESTS:
        t = transcript.lower()
        # Extract rate ("route" is common speech-to-text misinterpretation)
        rm = re.search(r'(?:rate|route)\s+\$?(\d+)', t, re.I) or re.search(r'\$(\d{3,4})', t, re.I)
        got_rate = rm.group(1) if rm else None
        # Strip rate from transcript
        clean = re.sub(r'\s*(?:rate|route)\s+\$?\d+', '', t, flags=re.I)
        clean = re.sub(r'\s*\$\d{3,4}', '', clean, flags=re.I).strip()
        # Parse origin/dest
        tm = re.match(r'(?:from\s+)?(.+?)\s+to\s+(.+)', clean, re.I)
        got_origin = cap_city(tm.group(1).strip()) if tm else None
        got_dest = cap_city(tm.group(2).strip()) if tm else None

        ok = got_origin == exp_origin and got_dest == exp_dest and got_rate == exp_rate
        if ok:
            print(f"  ✅ \"{transcript[:50]}\"")
            print(f"     → {got_origin} → {got_dest} @ ${got_rate}")
            passed += 1
        else:
            print(f"  ❌ \"{transcript[:50]}\"")
            print(f"     Got:      {got_origin} → {got_dest} @ ${got_rate}")
            print(f"     Expected: {exp_origin} → {exp_dest} @ ${exp_rate}")
            failed += 1
    print(f"  {'─'*50}")
    print(f"  {passed} passed, {failed} failed\n")
    return failed


def run_geocode_tests():
    print("═══ Live Geocode Tests (Nominatim) ═══")
    import requests
    passed = failed = 0
    for city, lat_range, desc in GEOCODE_TESTS:
        try:
            r = requests.get('https://nominatim.openstreetmap.org/search', params={
                'q': city + ', USA', 'format': 'json', 'limit': 5, 'addressdetails': 1
            }, headers={'User-Agent': 'LoadCalc/1.0', 'Accept-Language': 'en'}, timeout=10)
            results = r.json()
            if not results:
                print(f"  ❌ {city:20s} — no results")
                failed += 1
                continue

            city_name = city.split(',')[0].strip().lower()
            # Apply same county filter as JS
            def is_county(item):
                dn = (item.get('display_name', '') or '').lower()
                a = item.get('address', {})
                return (dn.startswith(city_name + ' county') or
                        (item.get('class') == 'boundary' and item.get('type') == 'administrative'
                         and not a.get('city') and not a.get('town') and not a.get('village')))

            places = [r for r in results if not is_county(r)]
            best = places[0] if places else results[0]
            lat = float(best['lat'])

            if lat_range[0] <= lat <= lat_range[1]:
                print(f"  ✅ {city:20s} lat={lat:.4f}  ({desc})")
                passed += 1
            else:
                print(f"  ❌ {city:20s} lat={lat:.4f}  EXPECTED {lat_range[0]}-{lat_range[1]}  ({desc})")
                failed += 1
        except Exception as e:
            print(f"  ❌ {city:20s} — error: {e}")
            failed += 1
        time.sleep(1.1)  # Nominatim rate limit

    print(f"  {'─'*50}")
    print(f"  {passed} passed, {failed} failed\n")
    return failed


# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    live = '--live' in sys.argv
    total_failures = 0

    total_failures += run_cap_city_tests()
    total_failures += run_voice_parse_tests()

    if live:
        total_failures += run_geocode_tests()
    else:
        print("═══ Geocode Tests ═══")
        print("  ⏭  Skipped (run with --live to test against Nominatim)\n")

    print("━" * 55)
    if total_failures == 0:
        print("✅ ALL TESTS PASSED")
    else:
        print(f"❌ {total_failures} FAILURE(S)")
    sys.exit(1 if total_failures else 0)
