DEFAULT_LANG = 'es'
SUPPORTED_LANGS = ('es', 'en')


def get_browser_language(request):
    accept = request.headers.get('Accept-Language', '')
    if not accept:
        return DEFAULT_LANG
    for part in accept.split(','):
        lang_tag = part.strip().split(';')[0].strip().lower()
        if lang_tag.startswith('es'):
            return 'es'
        if lang_tag.startswith('en'):
            return 'en'
    return DEFAULT_LANG
