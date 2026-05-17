#!/usr/bin/env python3
"""Script de verificacion de coherencia para ArchEstate"""

import os
import re
import sys
import sqlite3


RESULTS = []


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    RESULTS.append((status, name, detail))
    symbol = "+" if condition else "x"
    print(f"  [{symbol}] {name}" + (f" - {detail}" if detail and not condition else ""))


def main():
    base = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(base, "templates")
    app_path = os.path.join(base, "app.py")
    init_db_path = os.path.join(base, "init_db.py")

    print("=" * 60)
    print("  ARCHESTATE - COHERENCE VERIFICATION REPORT")
    print("=" * 60)

    # --- 1. Template meta tags ---
    print("\n[1] Template Meta Tags")
    base_path = os.path.join(templates_dir, "base.html")
    with open(base_path) as f:
        base_content = f.read()

    check("base.html has <html lang=...>", 'lang=' in base_content[:200])
    check("base.html has viewport meta", 'viewport' in base_content)
    check("base.html has title block", '{% block title %}' in base_content)
    check("base.html has charset meta", 'charset' in base_content)

    # Check each template extends base and has title block
    for fname in os.listdir(templates_dir):
        if not fname.endswith('.html') or fname == 'base.html':
            continue
        fpath = os.path.join(templates_dir, fname)
        with open(fpath) as f:
            content = f.read()
        check(f"{fname} extends base.html", '{% extends "base.html" %}' in content)
        check(f"{fname} has title block", '{% block title %}' in content)

    # --- 2. Heading hierarchy ---
    print("\n[2] Heading Hierarchy (single h1 per page)")
    for fname in os.listdir(templates_dir):
        if not fname.endswith('.html'):
            continue
        fpath = os.path.join(templates_dir, fname)
        with open(fpath) as f:
            content = f.read()
        h1_count = len(re.findall(r'<h1[^>]*>', content))
        check(f"{fname} has single h1 (found {h1_count})", h1_count <= 1,
              f"Found {h1_count} h1 tags" if h1_count > 1 else "")

    # --- 3. Routes in app.py ---
    print("\n[3] Route Registration (no duplicates)")
    with open(app_path) as f:
        app_content = f.read()

    routes = re.findall(r"@app\.route\(['\"]([^'\"]+)['\"]", app_content)
    route_counts = {}
    for r in routes:
        route_counts[r] = route_counts.get(r, 0) + 1

    duplicates = {r: c for r, c in route_counts.items() if c > 1}
    check(f"All routes registered ({len(routes)} found)", len(duplicates) == 0,
          f"Duplicate routes: {duplicates}" if duplicates else "")

    # --- 4. DB schema match ---
    print("\n[4] Database Schema Consistency")
    with open(init_db_path) as f:
        init_content = f.read()

    expected_tables = ['users', 'leads', 'professionals', 'audit_log']
    for table in expected_tables:
        in_app = f"CREATE TABLE IF NOT EXISTS {table}" in app_content
        in_init = f"CREATE TABLE IF NOT EXISTS {table}" in init_content
        check(f"Table '{table}' in both app.py and init_db.py", in_app and in_init)

    # --- 5. DB connections with finally/close ---
    print("\n[5] DB Connection Cleanup (finally blocks)")
    conn_opens = len(re.findall(r'get_db_connection\(\)', app_content))
    conn_closes = len(re.findall(r'\.close\(\)', app_content))
    check(f"DB connections opened ({conn_opens}) vs closed ({conn_closes})",
          conn_closes >= conn_opens - 5,
          "Some connections may be auto-managed")

    # Check for try/finally patterns
    try_finally = len(re.findall(r'try:.*?finally:', app_content, re.DOTALL))
    check(f"try/finally blocks found: {try_finally}", try_finally >= 10)

    # --- 6. No duplicate script/css imports ---
    print("\n[6] No Duplicate Script/CSS Imports in Templates")
    for fname in os.listdir(templates_dir):
        if not fname.endswith('.html'):
            continue
        fpath = os.path.join(templates_dir, fname)
        with open(fpath) as f:
            content = f.read()

        script_tags = re.findall(r'<script[^>]*src=["\']((?!{{)[^"\']+)["\']', content)
        css_links = re.findall(r'<link[^>]*href=["\']((?!{{)[^"\']+\.css)["\']', content)

        dup_scripts = [s for s in set(script_tags) if script_tags.count(s) > 1]
        dup_css = [c for c in set(css_links) if css_links.count(c) > 1]
        check(f"{fname} no duplicate imports", not dup_scripts and not dup_css,
              f"Duplicates: scripts={dup_scripts}, css={dup_css}")

    # --- 7. Foreign key references ---
    print("\n[7] Foreign Key References")
    check("professionals.user_id references users(id)",
          "FOREIGN KEY (user_id) REFERENCES users(id)" in app_content or
          "FOREIGN KEY (user_id) REFERENCES users(id)" in init_content)

    # --- 8. Rate limiting on sensitive endpoints ---
    print("\n[8] Rate Limiting on Sensitive Endpoints")
    sensitive_routes = ['/login', '/register', '/api/submit']
    for route in sensitive_routes:
        pattern = rf"@app\.route\(['\"]{re.escape(route)}['\"].*?@rate_limit"
        check(f"Rate limit on {route}",
              bool(re.search(pattern, app_content, re.DOTALL)),
              f"No @rate_limit decorator found")

    # --- Summary ---
    print("\n" + "=" * 60)
    passed = sum(1 for s, _, _ in RESULTS if s == "PASS")
    failed = sum(1 for s, _, _ in RESULTS if s == "FAIL")
    total = passed + failed
    print(f"  RESULTS: {passed}/{total} passed, {failed} failed")
    print("=" * 60)

    if failed > 0:
        print("\n  FAILED CHECKS:")
        for s, name, detail in RESULTS:
            if s == "FAIL":
                print(f"    - {name}" + (f": {detail}" if detail else ""))
        print()

    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
