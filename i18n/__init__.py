from i18n.translations import TRANSLATIONS, t as _t
from i18n.browser import get_browser_language

DEFAULT_LANG = 'es'
SUPPORTED_LANGS = ('es', 'en')


def t(key, lang=None, **kwargs):
    if lang is None:
        lang = DEFAULT_LANG
    return _t(key, lang, **kwargs)


def get_language():
    from flask import session, g
    if session.get('user_id'):
        try:
            from models import get_user_preferences
            prefs = get_user_preferences(session['user_id'])
            lang = prefs.get('language', DEFAULT_LANG)
            if lang in SUPPORTED_LANGS:
                return lang
        except Exception:
            pass
    try:
        from flask import request
        return get_browser_language(request)
    except Exception:
        pass
    return DEFAULT_LANG
