"""Compatibilidad: implementación en routes/profile/ (FASE 3.4).

`from routes.profile_bp import profile_bp` sigue funcionando.
"""
from routes.profile import profile_bp  # noqa: F401
from routes.profile.exports import _build_export_stats  # noqa: F401
