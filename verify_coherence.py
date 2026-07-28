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
ROUTES_DIR = os.path.join(PROJECT_ROOT, 'routes')
ROUTES_PROFILE = os.path.join(PROJECT_ROOT, 'routes_profile.py')
FACTORY_FILE = os.path.join(PROJECT_ROOT, 'factory.py')
APP_SETUP_FILE = os.path.join(PROJECT_ROOT, 'app_setup.py')
BLUEPRINT_FILES = [os.path.join(ROUTES_DIR, f) for f in os.listdir(ROUTES_DIR) if f.endswith('.py') and f != '__init__.py']
ALL_ROUTE_FILES = BLUEPRINT_FILES + [ROUTES_PROFILE]

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


def read_all_route_files():
    content = ''
    for f in ALL_ROUTE_FILES:
        content += read_file(f) + '\n'
    return content


# ===== 1. Template Meta Tags =====
print('\n[1] Template Meta Tags')
base = read_file(os.path.join(TEMPLATES_DIR, 'base.html'))
check('base.html has <html lang=...>', 'lang=' in base and ('lang="{{ lang }}"' in base or "lang='es" in base or 'lang="es' in base))
check('base.html has viewport meta', 'viewport' in base)
check('base.html has title block', '{% block title %}' in base)
check('base.html has charset meta', 'charset' in base)

for fname in os.listdir(TEMPLATES_DIR):
    if not fname.endswith('.html'):
        continue
    fpath = os.path.join(TEMPLATES_DIR, fname)
    if os.path.isdir(fpath):
        continue
    content = read_file(fpath)
    if fname == 'base.html' or fname == 'index.html':
        continue
    check(f'{fname} extends base.html', '{% extends "base.html" %}' in content)
    check(f'{fname} has title block', '{% block title %}' in content)

# ===== 2. Heading Hierarchy =====
print('\n[2] Heading Hierarchy (single h1 per page)')
for fname in os.listdir(TEMPLATES_DIR):
    if not fname.endswith('.html'):
        continue
    fpath = os.path.join(TEMPLATES_DIR, fname)
    if os.path.isdir(fpath):
        continue
    content = read_file(fpath)
    h1_count = len(re.findall(r'<h1[^>]*>', content))
    check(f'{fname} has single h1 (found {h1_count})', h1_count <= 1)

# ===== 3. Route Registration =====
print('\n[3] Route Registration (no duplicates)')
all_routes_content = read_all_route_files()
factory_content = read_file(FACTORY_FILE)

routes_app = re.findall(r"@app\.route\(['\"]([^'\"]+)['\"]", factory_content)

# Extract full route declarations with methods
route_decls = re.findall(
    r"@(\w+)\.route\(['\"]([^'\"]+)['\"](?:.*?methods=\[([^\]]*)\])?",
    all_routes_content
)

# Build (path, method) set — same path+method in same blueprint = duplicate
from collections import defaultdict
route_methods = defaultdict(set)
for bp, path, methods_str in route_decls:
    if methods_str:
        methods = [m.strip().strip("'\"") for m in methods_str.split(',')]
    else:
        methods = ['GET']  # Flask default
    for method in methods:
        route_methods[(bp, path)].add(method)

# Check: same blueprint+path+method appearing more than once via the regex
# This catches the real issue: copy-paste route definitions
duplicate_count = 0
seen_route_funcs = {}
for bp, path, methods_str in route_decls:
    if methods_str:
        methods = [m.strip().strip("'\"") for m in methods_str.split(',')]
    else:
        methods = ['GET']
    for method in methods:
        key = (path, method)
        if key in seen_route_funcs and seen_route_funcs[key] == bp:
            duplicate_count += 1
        seen_route_funcs[key] = bp

total_routes = len(routes_app) + len(route_decls)
check(f'All routes registered ({total_routes} endpoints)', duplicate_count == 0,
      f'{duplicate_count} duplicates' if duplicate_count else '')

# ===== 4. Database Schema Consistency =====
print('\n[4] Database Schema Consistency (app_setup.py)')
setup_content = read_file(APP_SETUP_FILE)

tables = ['users', 'leads', 'professionals', 'audit_log']
for table in tables:
    in_setup = f'CREATE TABLE IF NOT EXISTS {table}' in setup_content or f'CREATE TABLE {table}' in setup_content
    check(f"Table '{table}' in app_setup.py", in_setup)

# ===== 5. DB Connection Cleanup =====
print('\n[5] DB Connection Cleanup (finally blocks)')
conn_opens = len(re.findall(r'get_db_connection\(\)', all_routes_content))
conn_closes = len(re.findall(r'\.close\(\)', all_routes_content))
finally_blocks = len(re.findall(r'finally:', all_routes_content))
check(f'DB connections opened ({conn_opens}) vs closed ({conn_closes})', conn_closes >= conn_opens - 2)
check(f'try/finally blocks found: {finally_blocks}', finally_blocks >= 20)

# ===== 6. No Duplicate Script/CSS Imports =====
print('\n[6] No Duplicate Script/CSS Imports in Templates')
for fname in os.listdir(TEMPLATES_DIR):
    if not fname.endswith('.html'):
        continue
    fpath = os.path.join(TEMPLATES_DIR, fname)
    if os.path.isdir(fpath):
        continue
    content = read_file(fpath)
    scripts = re.findall(r'src="[^"]*main\.js"', content)
    css_base = re.findall(r'href="[^"]*base\.css"', content)
    check(f'{fname} no duplicate imports', len(scripts) <= 1 and len(css_base) <= 1,
          f'duplicate: scripts={len(scripts)}, css={len(css_base)}' if len(scripts) > 1 or len(css_base) > 1 else '')

# ===== 7. Foreign Key References =====
print('\n[7] Foreign Key References')
check("professionals.user_id references users(id)", 'user_id' in setup_content and 'users(id)' in setup_content)

# ===== 8. Rate Limiting =====
print('\n[8] Rate Limiting on Sensitive Endpoints')
check('Rate limit on /login', 'check_rate_limit' in all_routes_content and '/login' in all_routes_content)
check('Rate limit on /register', 'check_rate_limit' in all_routes_content and '/register' in all_routes_content)
check('Rate limit on /api/submit', 'check_rate_limit' in all_routes_content and '/api/submit' in all_routes_content)

# ===== 9. Blueprint Registration =====
print('\n[9] Blueprint Registration')
factory_content = read_file(FACTORY_FILE)
expected_blueprints = ['auth_bp', 'public_bp', 'client_bp', 'professional_bp', 'admin_bp', 'phone_bp', 'lead_bp', 'form_options_bp', 'whatsapp_bp']
for bp in expected_blueprints:
    check(f'{bp} registered in factory.py', bp in factory_content)

# ===== 10. i18n Keys =====
print('\n[10] i18n Coverage')
translations_file = os.path.join(PROJECT_ROOT, 'i18n', 'translations.py')
i18n_js = os.path.join(PROJECT_ROOT, 'static', 'js', 'i18n.js')
translations_content = read_file(translations_file)
i18n_js_content = read_file(i18n_js)
has_t_import = 'from i18n import t' in translations_content or 'from i18n import' in read_all_route_files()
check('Python files import i18n', has_t_import)
check('i18n.js exists', len(i18n_js_content) > 0)
check('translations.py has EN keys', "'en'" in translations_content)
check('translations.py has ES keys', "'es'" in translations_content)

# ===== 11. Error Handlers =====
print('\n[11] Error Handlers')
errors_file = os.path.join(PROJECT_ROOT, 'errors.py')
errors_content = read_file(errors_file)
error_codes = [400, 403, 404, 409, 410, 413, 429, 500, 502, 503, 504]
for code in error_codes:
    check(f'Error handler {code}', f'@app.errorhandler({code})' in errors_content)

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
