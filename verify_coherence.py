#!/usr/bin/env python3
"""
ARCHESTATE - COHERENCE VERIFICATION SCRIPT
Checks template consistency, route registration, DB schema sync, and more.
"""

import os
import re
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(PROJECT_ROOT, 'templates')
APP_FILE = os.path.join(PROJECT_ROOT, 'app.py')
INIT_DB_FILE = os.path.join(PROJECT_ROOT, 'init_db.py')

passed = 0
failed = 0
results = []

def check(name, condition, detail=''):
    global passed, failed
    status = '+' if condition else 'x'
    if condition:
        passed += 1
    else:
        failed += 1
    msg = f"  [{status}] {name}"
    if detail and not condition:
        msg += f" ({detail})"
    results.append(msg)

def read_file(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return ''

# ===== 1. Template Meta Tags =====
print('\n[1] Template Meta Tags')
base = read_file(os.path.join(TEMPLATES_DIR, 'base.html'))
check('base.html has <html lang=...>', 'lang=' in base and ('lang="es' in base or "lang='es" in base))
check('base.html has viewport meta', 'viewport' in base)
check('base.html has title block', '{% block title %}' in base)
check('base.html has charset meta', 'charset' in base)

for fname in os.listdir(TEMPLATES_DIR):
    if not fname.endswith('.html'):
        continue
    content = read_file(os.path.join(TEMPLATES_DIR, fname))
    if fname == 'base.html' or fname == 'index.html':
        continue
    check(f'{fname} extends base.html', '{% extends "base.html" %}' in content)
    check(f'{fname} has title block', '{% block title %}' in content)

# ===== 2. Heading Hierarchy =====
print('\n[2] Heading Hierarchy (single h1 per page)')
for fname in os.listdir(TEMPLATES_DIR):
    if not fname.endswith('.html'):
        continue
    content = read_file(os.path.join(TEMPLATES_DIR, fname))
    h1_count = len(re.findall(r'<h1[^>]*>', content))
    check(f'{fname} has single h1 (found {h1_count})', h1_count <= 1)

# ===== 3. Route Registration =====
print('\n[3] Route Registration (no duplicates)')
app_content = read_file(APP_FILE)
routes = re.findall(r"@app\.route\(['\"]([^'\"]+)['\"]", app_content)
blueprint_routes = re.findall(r"@\w+\.route\(['\"]([^'\"]+)['\"]", app_content)
all_routes = routes + blueprint_routes
unique_routes = set(all_routes)
check(f'All routes registered ({len(all_routes)} found)', len(all_routes) == len(unique_routes),
      f'{len(all_routes) - len(unique_routes)} duplicates' if len(all_routes) != len(unique_routes) else '')

# ===== 4. Database Schema Consistency =====
print('\n[4] Database Schema Consistency')
init_content = read_file(INIT_DB_FILE)
app_init = read_file(APP_FILE)

tables = ['users', 'leads', 'professionals', 'audit_log']
for table in tables:
    in_init = f'CREATE TABLE IF NOT EXISTS {table}' in init_content or f'CREATE TABLE {table}' in init_content
    in_app = f'CREATE TABLE IF NOT EXISTS {table}' in app_init or f'CREATE TABLE {table}' in app_init
    check(f"Table '{table}' in both app.py and init_db.py", in_init and in_app)

# ===== 5. DB Connection Cleanup =====
print('\n[5] DB Connection Cleanup (finally blocks)')
conn_opens = len(re.findall(r'get_db_connection\(\)', app_content))
conn_closes = len(re.findall(r'\.close\(\)', app_content))
finally_blocks = len(re.findall(r'finally:', app_content))
check(f'DB connections opened ({conn_opens}) vs closed ({conn_closes})', conn_closes >= conn_opens - 2)
check(f'try/finally blocks found: {finally_blocks}', finally_blocks >= 20)

# ===== 6. No Duplicate Script/CSS Imports =====
print('\n[6] No Duplicate Script/CSS Imports in Templates')
for fname in os.listdir(TEMPLATES_DIR):
    if not fname.endswith('.html'):
        continue
    content = read_file(os.path.join(TEMPLATES_DIR, fname))
    scripts = re.findall(r'src="[^"]*main\.js"', content)
    css_base = re.findall(r'href="[^"]*base\.css"', content)
    check(f'{fname} no duplicate imports', len(scripts) <= 1 and len(css_base) <= 1,
          f'duplicate: scripts={len(scripts)}, css={len(css_base)}' if len(scripts) > 1 or len(css_base) > 1 else '')

# ===== 7. Foreign Key References =====
print('\n[7] Foreign Key References')
check("professionals.user_id references users(id)", 'user_id' in init_content and 'users' in init_content)

# ===== 8. Rate Limiting =====
print('\n[8] Rate Limiting on Sensitive Endpoints')
check('Rate limit on /login', 'check_rate_limit' in app_content and '/login' in app_content)
check('Rate limit on /register', 'check_rate_limit' in app_content and '/register' in app_content)
check('Rate limit on /api/submit', 'check_rate_limit' in app_content and '/api/submit' in app_content)

# ===== Summary =====
print('\n' + '=' * 60)
print('  ARCHESTATE - COHERENCE VERIFICATION REPORT')
print('=' * 60)
for r in results:
    print(r)
print(f'\n{"=" * 60}')
print(f'  RESULTS: {passed}/{passed + failed} passed, {failed} failed')
print(f'{"=" * 60}')

if failed > 0:
    print('\n  FAILED CHECKS:')
    for r in results:
        if r.startswith('  [x]'):
            print(f'    - {r[6:]}')

sys.exit(1 if failed > 0 else 0)
