import logging
from datetime import datetime, timezone

from flask import Blueprint, jsonify, render_template, url_for

import models
from services.database import date_format_sql, now_sql

logger = logging.getLogger(__name__)

public_bp = Blueprint('public', __name__, url_prefix='')


@public_bp.route('/')
def index():
    return render_template('landing.html')


@public_bp.route('/api/landing/stats', methods=['GET'])
def landing_stats():
    conn = None
    try:
        conn = models.get_db_connection()

        total_leads = conn.execute('SELECT COUNT(*) FROM leads').fetchone()[0]
        total_pros = conn.execute(
            "SELECT COUNT(*) FROM professionals WHERE status = 'approved'"
        ).fetchone()[0]
        total_zones = conn.execute(
            'SELECT COUNT(DISTINCT zone) FROM leads WHERE zone != ""'
        ).fetchone()[0]
        leads_this_month = conn.execute(f'''
            SELECT COUNT(*) FROM leads
            WHERE {date_format_sql('timestamp', '%Y-%m')} = {now_sql()}
        ''').fetchone()[0]

        return jsonify({
            'total_leads': total_leads or 0,
            'total_professionals': total_pros or 0,
            'total_zones': total_zones or 0,
            'leads_this_month': leads_this_month or 0,
        })
    except Exception as e:
        logger.exception('Error en landing_stats')
        return jsonify({
            'total_leads': 0,
            'total_professionals': 0,
            'total_zones': 0,
            'leads_this_month': 0,
        }), 500
    finally:
        if conn:
            conn.close()


@public_bp.route('/sitemap.xml')
def sitemap():
    today = datetime.now(timezone.utc).date().isoformat()
    public_urls = [
        {'loc': url_for('public.index', _external=True), 'changefreq': 'daily', 'priority': '1.0'},
        {'loc': url_for('professional.professional_view', _external=True), 'changefreq': 'weekly', 'priority': '0.7'},
    ]
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for url in public_urls:
        xml += f'  <url>\n    <loc>{url["loc"]}</loc>\n'
        xml += f'    <lastmod>{today}</lastmod>\n'
        xml += f'    <changefreq>{url["changefreq"]}</changefreq>\n'
        xml += f'    <priority>{url["priority"]}</priority>\n'
        xml += '  </url>\n'
    xml += '</urlset>'
    return xml, 200, {'Content-Type': 'application/xml'}


@public_bp.route('/robots.txt')
def robots():
    sitemap_url = url_for('public.sitemap', _external=True)
    content = f"""User-agent: *
Allow: /
Disallow: /admin/
Disallow: /api/
Disallow: /login
Disallow: /register
Disallow: /usuario
Disallow: /profesional
Sitemap: {sitemap_url}
"""
    return content, 200, {'Content-Type': 'text/plain'}


@public_bp.route('/estadisticas')
def budget_stats():
    from app_setup import get_budget_stats_from_db
    stats = get_budget_stats_from_db()
    return jsonify(stats)


@public_bp.route('/estadisticas-popup')
def budget_stats_for_popup():
    return jsonify({
        'min': 0,
        'max': 10000000000,
        'ranges': [],
        'currency_options': ['ARG', 'USD', 'EUR'],
    })
