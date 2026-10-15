"""Compatibilidad: la implementación vive en models/ (base, users, leads, ...).

`import models` y `from models import X` siguen funcionando igual (FASE 3.1).
"""
from models.base import (
    DatabaseError,
    SimpleTTLCache,
    _GuardedConnection,
    get_db_connection,
)
from models.users import *
from models.leads import *
from models.professionals import *
from models.pipeline import *
from models.calendar import *
from models.notifications import *
from models.organizations import *
from models.form_options import *
from models.preferences import *
from models.misc import *
