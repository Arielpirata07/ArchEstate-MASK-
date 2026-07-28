window.I18N = {
    es: {
        // === TOAST ===
        'toast.network_error': 'Error de conexión',
        'toast.success': 'Operación exitosa',
        'toast.error': 'Ocurrió un error',
        'toast.saving': 'Guardando...',
        'toast.saved': 'Guardado',
        'toast.deleted': 'Eliminado',
        'toast.loading': 'Cargando...',

        // === CONFIRM ===
        'confirm.cancel': 'Cancelar',
        'confirm.accept': 'Confirmar',
        'confirm.delete': 'Eliminar',
        'confirm.yes': 'Sí',

        // === NAV ===
        'nav.loading': 'Cargando...',
        'nav.no_notifications': 'Sin notificaciones',
        'nav.error_loading': 'Error al cargar',
        'nav.read': 'Leído',
        'nav.mark_all_read': 'Marcar leídas',

        // === MOBILE ===
        'mobile.menu_open': 'Abrir menú de navegación',
        'mobile.menu_close': 'Cerrar menú de navegación',
        'mobile.solicitud': 'Solicitud',
        'mobile.profesional': 'Profesional',
        'mobile.panel_admin': 'Panel Admin',
        'mobile.configuracion': 'Configuración',
        'mobile.modo_claro': 'Modo Claro',
        'mobile.modo_oscuro': 'Modo Oscuro',
        'mobile.cerrar_sesion': 'Cerrar Sesión',
        'mobile.acceso_privado': 'Acceso Privado',

        // === ACTION ===
        'action.processing': 'Procesando...',
        'action.loading': 'Cargando...',
        'action.saving': 'Guardando...',
        'action.saved': 'Guardado',
        'action.sending': 'Enviando...',
        'action.uploading': 'Subiendo...',
        'action.deleting': 'Eliminando...',
        'action.updating': 'Actualizando...',
        'action.verifying': 'Verificando...',
        'action.save_changes': 'Guardar Cambios',
        'action.cancel': 'Cancelar',
        'action.save': 'Guardar',
        'action.update': 'Actualizar',
        'action.close': 'Cerrar',
        'action.download': 'Descargar',
        'action.verify': 'Verificar',
        'action.view': 'Ver',
        'action.contact': 'Contactar',
        'action.view_phone': 'Ver Teléfono',
        'action.open_whatsapp': 'Abrir chat de WhatsApp',
        'action.send_sms': 'Enviar SMS',
        'action.view_more': 'Ver más',
        'action.view_full_details': 'Ver detalle completo',
        'action.report_phone': 'Reportar teléfono inexistente',
        'action.report': 'Reportar',
        'action.phone': 'Teléfono',
        'action.approve': 'Aprobar',
        'action.reject': 'Rechazar',
        'action.disapprove': 'Desaprobar',
        'action.disable': 'Dar de baja',
        'action.reactivate': 'Reactivar',
        'action.edit': 'Editar',
        'action.deactivate': 'Desactivar',
        'action.activate': 'Activar',
        'action.delete': 'Eliminar',
        'action.restore': 'Restaurar',
        'action.view_lead': 'Ver Lead',
        'action.reset_password': 'Reset Pass',
        'action.enable': 'Activar',
        'action.change_password': 'Cambiar Contraseña',
        'action.save_pro_profile': 'Guardar Perfil Profesional',

        // === VALIDATOR ===
        'validator.required': 'Este campo es obligatorio',
        'validator.email_invalid': 'Formato de email inválido',
        'validator.phone_invalid': 'Formato de teléfono inválido',
        'validator.username_format': '3-30 caracteres, solo letras, números y guión bajo.',
        'validator.password_min': 'Mínimo 6 caracteres.',
        'validator.password_letter': 'Debe contener al menos una letra.',
        'validator.password_number': 'Debe contener al menos un número.',
        'validator.phone_format_country': 'Formato inválido para ${label} (mín. ${min} dígitos)',
        'validator.phone_length': 'Teléfono debe tener entre 8 y 15 dígitos',
        'validator.currency_invalid': 'Moneda no válida.',
        'validator.budget_invalid': 'Presupuesto no válido.',
        'validator.budget_min_for_currency': 'El monto mínimo para ${label} es ${min}. Revisá la moneda seleccionada.',
        'validator.budget_max_for_currency': 'El monto máximo para ${label} es ${max}. Revisá la moneda seleccionada.',
        'validator.built_area_exceeds': 'Los metros construidos no pueden superar el 80% del terreno.',
        'validator.email_empty_or_invalid': 'El email no es válido o está vacío. Verificá tu perfil.',
        'validator.license_format': '3-50 caracteres, solo letras, números y guiones.',

        // === ERROR ===
        'error.server_connection': 'Error de conexión con el servidor',
        'error.connection': 'Error de conexión',
        'error.connection_retry': 'Error de conexión. Intentá de nuevo.',
        'error.phone_fetch_failed': 'No se pudo obtener el teléfono',
        'error.phone_network': 'Error de red al consultar teléfono',
        'error.phone_save': 'Error al guardar el teléfono',
        'error.leads_load': 'Error al cargar leads',
        'error.stats_load': 'Error al cargar estadísticas',
        'error.stats_network': 'Error de conexión al cargar estadísticas',
        'error.upload_failed': 'Error al subir el archivo.',
        'error.upload_network': 'Error de conexión al subir el archivo.',
        'error.file_type_not_allowed': 'Tipo no permitido. Usá: PDF, JPG o PNG.',
        'error.file_too_large': 'El archivo supera los ${max} MB.',
        'error.report': 'Error al reportar',
        'error.process_request': 'Error al procesar la solicitud.',
        'error.load': 'Error al cargar',
        'error.delete': 'Error al eliminar',
        'error.restore': 'Error al restaurar',
        'error.users_load': 'Error al cargar usuarios.',
        'error.password_reset': 'Error al resetear la contraseña.',
        'error.disable': 'Error al dar de baja.',
        'error.reactivate': 'Error al reactivar.',
        'error.avatar_upload': 'Error al subir foto',
        'error.avatar_delete': 'Error al eliminar foto',
        'error.sessions_load': 'Error al cargar sesiones',
        'error.activity_load': 'Error al cargar actividad',
        'error.code_send': 'Error al enviar el código.',
        'error.form_options_load': 'Error al cargar opciones',
        'error.generic': 'Error',

        // === STATUS ===
        'status.approved': 'Aprobado',
        'status.rejected': 'Rechazado',
        'status.pending': 'Pendiente',
        'status.processed': 'Procesado',
        'status.active': 'Activo',
        'status.inactive': 'Inactivo',
        'status.seen': 'Visto',
        'status.contacted': 'Contactado',
        'status.account_disabled': 'Cuenta baja',
        'status.no_account': 'Sin cuenta',
        'status.no_document': 'Sin documento',
        'status.protected': 'Protegida',

        // === ROLE ===
        'role.admin': 'Admin',
        'role.professional': 'Profesional',
        'role.client': 'Cliente',

        // === THEME ===
        'theme.light': 'Modo Claro',
        'theme.dark': 'Modo Oscuro',

        // === PROPERTY ===
        'property.department': 'Departamento',
        'property.house': 'Casa',
        'property.duplex': 'Dúplex',
        'property.penthouse': 'Penthouse',
        'property.commercial': 'Local Comercial',

        // === BUDGET ===
        'budget.unlimited': 'Ilimitado',
        'budget.greater_than': 'Presupuesto mayor a ',
        'budget.label': 'Presupuesto: ',
        'budget.up_to_200k': 'Hasta $200k',
        'budget.200k_500k': '$200k–$500k',
        'budget.500k_1m': '$500k–$1M',
        'budget.1m_2m': '$1M–$2M',
        'budget.over_2m': 'Más de $2M',

        // === CURRENCY ===
        'currency.usd_name': 'Dólares',
        'currency.eur_name': 'Euros',
        'currency.arg_name': 'Pesos',

        // === OPERATION ===
        'operation.buy': 'Comprar',
        'operation.remodel': 'Remodelación',
        'operation.build': 'Construir',

        // === STYLE ===
        'style.modern': 'Moderno',
        'style.classic': 'Clásico',
        'style.minimalist': 'Minimalista',
        'style.industrial': 'Industrial',
        'style.rustic': 'Rústico',
        'style.contemporary': 'Contemporáneo',
        'style.avant_garde': 'Vanguardista',
        'style.traditional': 'Tradicional',
        'style.mediterranean': 'Mediterráneo',
        'style.nordic': 'Nórdico',
        'style.colonial': 'Colonial',
        'style.art_deco': 'Art Deco',
        'style.bauhaus': 'Bauhaus',
        'style.organic': 'Orgánico',
        'style.high_tech': 'High-Tech',
        'style.neoclassic': 'Neoclásico',
        'style.gothic': 'Gótico',
        'style.baroque': 'Barroco',
        'style.renaissance': 'Renacentista',
        'style.other': 'Otro',

        // === AUTOCOMPLETE ===
        'autocomplete.use_query': 'Usar: ${query}',
        'autocomplete.free_text': '(texto libre)',
        'autocomplete.type_zone': 'Escribe una zona',
        'autocomplete.no_matches': 'Sin coincidencias',

        // === UPLOAD ===
        'upload.drag_here': 'Arrastrá tu archivo aquí',
        'upload.or_click': 'o hacé clic para seleccionar',
        'upload.max_size': 'PDF · JPG · PNG · Máx. ${max} MB',
        'upload.remove_file': 'Quitar archivo',
        'upload.uploading': 'Subiendo documento...',
        'upload.doc_loaded': 'Documento cargado',
        'upload.replace_doc': 'Reemplazar documento',
        'upload.submit_docs': 'Subir Documentación',
        'upload.docs_sent': 'Documentación enviada',

        // === FILTER ===
        'filter.zone_label': 'Zona: ${zone}',
        'filter.active_count': 'activo${count > 1 ? "s" : ""}',
        'filter.all': 'Todas',

        // === TIME ===
        'time.today': 'Hoy',
        'time.7_days': '7 días',
        'time.30_days': '30 días',

        // === LEADS ===
        'leads.searching': 'Buscando leads...',
        'leads.no_results': 'Sin resultados para estos filtros',
        'leads.no_results_hint': 'Probá ajustando el tipo de vivienda o el rango de inversión',
        'leads.no_type': 'Sin tipo',
        'leads.seen_by_singular': 'inmobiliaria ha visto',
        'leads.seen_by_plural': 'inmobiliarias han visto',
        'leads.view_singular': 'vista',
        'leads.view_plural': 'vistas',
        'leads.under_review': 'En revisión',
        'leads.contacted_by': '{count} profesional(es) contactaron tu solicitud',
        'leads.contact_names': '{names} contactaron tu solicitud',

        // === SPEC ===
        'spec.rooms': 'amb.',
        'spec.bedrooms': 'hab.',
        'spec.bathrooms': 'baños',
        'spec.land_m2': 'm² terreno',

        // === PARKING ===
        'parking.none': 'Sin cochera',
        'parking.single': 'Coch. simple',
        'parking.double': 'Coch. doble',
        'parking.open': 'Desc.',
        'parking.garage': 'Garage',

        // === CHART ===
        'chart.no_type': 'Sin tipo',
        'chart.no_zone': 'Sin zona',
        'chart.types': 'tipos',
        'chart.zones': 'zonas',
        'chart.months': 'meses',
        'chart.no_data': 'Sin datos',

        // === STATS ===
        'stats.new_this_month': 'Nuevo este mes',
        'stats.requests_total': 'solicitudes en total',

        // === PREVIEW ===
        'preview.operation': 'Operación',
        'preview.housing': 'Vivienda',
        'preview.zone': 'Zona',
        'preview.budget': 'Presupuesto',
        'preview.specifications': 'Especificaciones',

        // === MONTH ===
        'month.january': 'Enero',
        'month.february': 'Febrero',
        'month.march': 'Marzo',
        'month.april': 'Abril',
        'month.may': 'Mayo',
        'month.june': 'Junio',
        'month.july': 'Julio',
        'month.august': 'Agosto',
        'month.september': 'Septiembre',
        'month.october': 'Octubre',
        'month.november': 'Noviembre',
        'month.december': 'Diciembre',

        // === CONFIRM DIALOGS ===
        'confirm.reject_professional_warning': '¡ADVERTENCIA! Está a punto de RECHAZAR a este profesional...',
        'confirm.approve_professional': '¿Desea aprobar a este profesional para que pueda acceder a la plataforma?',
        'confirm.delete_lead': '¿Eliminar permanentemente el lead #${id}? Esta acción no se puede deshacer.',
        'confirm.restore_report': '¿Restaurar este reporte a estado pendiente?',
        'confirm.delete_option': '¿Eliminar esta opción?',
        'confirm.delete_avatar': '¿Eliminar foto de perfil?',
        'confirm.delete_pro_photo': '¿Eliminar foto profesional?',
        'confirm.close_session': '¿Cerrar esta sesión?',

        // === PHONE ===
        'phone.enter_number_first': 'Ingresá un número antes de guardar.',
        'phone.saved_to_profile': 'Teléfono guardado en tu perfil.',
        'phone.not_verified': 'No verificado',
        'phone.will_send_as': '✓ Se enviará como ${e164}',
        'phone.verified': 'Verificado',
        'phone.unverified': 'Sin verificar',
        'phone.none': 'Sin teléfono',

        // === PASSWORD ===
        'password.empty': 'vacía',
        'password.weak': 'débil',
        'password.fair': 'aceptable',
        'password.good': 'buena',
        'password.strong': 'fuerte',
        'password.very_weak': 'Muy débil',
        'password.mismatch': 'Las contraseñas no coinciden.',
        'password.min_length': 'La contraseña debe tener al menos 6 caracteres.',
        'password.all_fields_required': 'Todos los campos son requeridos',
        'password.hide': 'Ocultar contraseña',
        'password.show': 'Mostrar contraseña',

        // === USERNAME ===
        'username.taken': '✗ Ese usuario ya está en uso',
        'username.available': '✓ Disponible',

        // === FORM ===
        'form.review_fields': 'Revisá los campos marcados antes de continuar.',

        // === LICENSE ===
        'license.required_for_pro': 'La matrícula es obligatoria para profesionales.',
        'license.verified': '✓ Verificada',
        'license.not_verified': 'No verificada',

        // === AVATAR ===
        'avatar.updated': 'Foto actualizada',
        'avatar.deleted': 'Foto eliminada',

        // === SESSIONS ===
        'sessions.loading': 'Cargando sesiones...',
        'sessions.empty': 'No hay sesiones registradas.',
        'sessions.device': 'Dispositivo',
        'sessions.last_activity': 'Última actividad',

        // === ACTIVITY ===
        'activity.loading': 'Cargando actividad...',
        'activity.empty': 'No hay actividad registrada aún.',

        // === VERIFICATION ===
        'verification.enter_full_code': 'Ingresá el código completo de 6 dígitos.',
        'verification.success': 'Teléfono verificado correctamente',
        'verification.expired': 'Código expirado. Solicitá uno nuevo.',
        'verification.incorrect': 'Código incorrecto.',
        'verification.resent': 'Código reenviado',

        // === DASHBOARD (admin) ===
        'dashboard.pct_of_total': '% del total',
        'dashboard.requires_review': '⚠ Requieren revisión',
        'dashboard.success_rate': '% de intentos exitosos',
        'dashboard.success_rate_short': 'de éxito',
        'dashboard.call_clicks': 'clics en Llamar',

        // === PROS (admin) ===
        'pros.no_results': 'No se encontraron profesionales con los filtros aplicados.',

        // === ADMIN ===
        'admin.admin_action': 'Acción administrativa',
        'admin.reactivate_account': 'Reactivar Cuenta',
        'admin.reactivate_warning': 'El usuario recuperará el acceso a la plataforma inmediatamente.',
        'admin.disable_account': 'Dar de Baja',
        'admin.disable_warning': 'El usuario perderá acceso inmediatamente.',

        // === REPORTS (admin) ===
        'reports.empty': 'No hay reportes para mostrar',
        'reports.lead_deleted': 'Lead eliminado',

        // === SUCCESS ===
        'success.lead_deleted': 'Lead eliminado correctamente',
        'success.report_dismissed': 'Reporte descartado',
        'success.report_restored': 'Reporte restaurado correctamente',

        // === DETAIL (admin lead detail) ===
        'detail.not_specified': 'No especificado',
        'detail.not_specified_fem': 'No especificadas',
        'detail.department': 'Detalles del Departamento',
        'detail.useful_meters': 'Metros Útiles',
        'detail.elevator': 'Ascensor',
        'detail.house': 'Detalles de la Casa',
        'detail.land': 'Terreno',
        'detail.built': 'Construida',
        'detail.pool': 'Piscina',
        'detail.operation_type': 'Tipo de Operación',
        'detail.housing_type': 'Tipo de Vivienda',
        'detail.zone': 'Zona',
        'detail.budget': 'Presupuesto',
        'detail.architectural_style': 'Estilo Arquitectónico',
        'detail.parking': 'Cochera',
        'detail.orientation': 'Orientación',
        'detail.condition': 'Estado',
        'detail.age': 'Antigüedad',
        'detail.contact': 'Contacto',
        'detail.registered': 'Registrado',
        'detail.technical_specs': 'Especificaciones Técnicas',
        'detail.bedrooms': 'Habitaciones',
        'detail.bathrooms': 'Baños',
        'detail.meters': 'Metros',
        'detail.extras_amenities': 'Extras y Comodidades',

        // === PAGINATION ===
        'pagination.reports_page': 'Página ${page} de ${totalPages} (${total} reportes)',
        'pagination.audit_page': 'Página ${page} de ${totalPages} (${total} accesos)',

        // === AUDIT ===
        'audit.revealed': 'Revelado',
        'audit.whatsapp': 'WhatsApp',
        'audit.lead_deleted': 'Lead eliminado',

        // === FORM OPTIONS (admin) ===
        'form_options.empty': 'Sin opciones',
        'form_options.zero_found': '0 opciones encontradas',
        'form_options.results_count': '${count} opción(es) encontrada(s)',
        'form_options.new_option': 'Nueva Opción',
        'form_options.category': 'Categoría',
        'form_options.value': 'Valor',
        'form_options.value_placeholder': 'ej: departamento',
        'form_options.label': 'Etiqueta',
        'form_options.label_placeholder': 'ej: Departamento',
        'form_options.icon_optional': 'Icono (opcional)',
        'form_options.sort_order': 'Orden',
        'form_options.value_label_required': 'Valor y etiqueta son requeridos',
        'form_options.updated': 'Opción actualizada',
        'form_options.created': 'Opción creada',
        'form_options.activated': 'Opción activada',
        'form_options.deactivated': 'Opción desactivada',
        'form_options.deleted': 'Opción eliminada',
        'form_options.edit_option': 'Editar Opción',
        'form_options.select': 'Seleccionar',

        // === ICON SEARCH (admin) ===
        'icon.search': 'Buscar icono',
        'icon.search_placeholder': 'Buscar icono...',
        'icon.none': 'Ninguno',

        // === USERS (usermgmt) ===
        'users.no_results': 'No se encontraron usuarios.',
        'email.none': 'Sin email',

        // === FIELD ===
        'field.not_specified': 'No especificado',

        // === EXTRA MISSING KEYS ===
        'action.dismiss': 'Descartar',
        'status.deleted': 'Eliminado',
        'status.disabled': 'Deshabilitado',
        'status.dismissed': 'Descartado',
        'admin.disable_account_btn': 'Dar de Baja',
        'admin.reactivate_account_btn': 'Reactivar',
        'dashboard.leads': 'Leads',
        'dashboard.phone_success_rate': '% de intentos exitosos',
        'dashboard.this_month': 'Este mes',
        'detail.arch_style': 'Estilo Arquitectónico',
        'detail.extras': 'Extras',
        'detail.floor_block': 'Piso / Bloque',
        'detail.not_specified_pl': 'No especificadas',
        'detail.property_type': 'Tipo de Propiedad',
        'detail.province': 'Provincia',
        'detail.rooms': 'Ambientes',
        'error.options_load': 'Error al cargar opciones',
        'error.pros_load': 'Error al cargar profesionales',
        'form_options.all_categories': 'Todas',
        'form_options.icon': 'Icono',
        'form_options.required_fields': 'Valor y etiqueta son requeridos',
        'icon.none_label': 'Ninguno',
        'pros.no_account': 'Sin cuenta',
        'pros.no_document': 'Sin documento',
        'pros.not_found': 'No se encontraron profesionales.',
        'style.hightech': 'High-Tech',
        'style.vanguard': 'Vanguardista',
        'success.option_activated': 'Opción activada',
        'success.option_created': 'Opción creada',
        'success.option_deactivated': 'Opción desactivada',
        'success.option_deleted': 'Opción eliminada',
        'success.option_updated': 'Opción actualizada',
    },
    en: {
        // === TOAST ===
        'toast.network_error': 'Network error',
        'toast.success': 'Operation successful',
        'toast.error': 'An error occurred',
        'toast.saving': 'Saving...',
        'toast.saved': 'Saved',
        'toast.deleted': 'Deleted',
        'toast.loading': 'Loading...',

        // === CONFIRM ===
        'confirm.cancel': 'Cancel',
        'confirm.accept': 'Confirm',
        'confirm.delete': 'Delete',
        'confirm.yes': 'Yes',

        // === NAV ===
        'nav.loading': 'Loading...',
        'nav.no_notifications': 'No notifications',
        'nav.error_loading': 'Error loading',
        'nav.read': 'Read',
        'nav.mark_all_read': 'Mark all read',

        // === MOBILE ===
        'mobile.menu_open': 'Open navigation menu',
        'mobile.menu_close': 'Close navigation menu',
        'mobile.solicitud': 'Request',
        'mobile.profesional': 'Professional',
        'mobile.panel_admin': 'Admin Panel',
        'mobile.configuracion': 'Settings',
        'mobile.modo_claro': 'Light Mode',
        'mobile.modo_oscuro': 'Dark Mode',
        'mobile.cerrar_sesion': 'Log Out',
        'mobile.acceso_privado': 'Private Access',

        // === ACTION ===
        'action.processing': 'Processing...',
        'action.loading': 'Loading...',
        'action.saving': 'Saving...',
        'action.saved': 'Saved',
        'action.sending': 'Sending...',
        'action.uploading': 'Uploading...',
        'action.deleting': 'Deleting...',
        'action.updating': 'Updating...',
        'action.verifying': 'Verifying...',
        'action.save_changes': 'Save Changes',
        'action.cancel': 'Cancel',
        'action.save': 'Save',
        'action.update': 'Update',
        'action.close': 'Close',
        'action.download': 'Download',
        'action.verify': 'Verify',
        'action.view': 'View',
        'action.contact': 'Contact',
        'action.view_phone': 'View Phone',
        'action.open_whatsapp': 'Open WhatsApp chat',
        'action.send_sms': 'Send SMS',
        'action.view_more': 'View more',
        'action.view_full_details': 'View full details',
        'action.report_phone': 'Report non-existent phone',
        'action.report': 'Report',
        'action.phone': 'Phone',
        'action.approve': 'Approve',
        'action.reject': 'Reject',
        'action.disapprove': 'Disapprove',
        'action.disable': 'Disable',
        'action.reactivate': 'Reactivate',
        'action.edit': 'Edit',
        'action.deactivate': 'Deactivate',
        'action.activate': 'Activate',
        'action.delete': 'Delete',
        'action.restore': 'Restore',
        'action.view_lead': 'View Lead',
        'action.reset_password': 'Reset Pass',
        'action.enable': 'Enable',
        'action.change_password': 'Change Password',
        'action.save_pro_profile': 'Save Professional Profile',

        // === VALIDATOR ===
        'validator.required': 'This field is required',
        'validator.email_invalid': 'Invalid email format',
        'validator.phone_invalid': 'Invalid phone format',
        'validator.username_format': '3-30 characters, letters, numbers and underscore only.',
        'validator.password_min': 'Minimum 6 characters.',
        'validator.password_letter': 'Must contain at least one letter.',
        'validator.password_number': 'Must contain at least one number.',
        'validator.phone_format_country': 'Invalid format for ${label} (min. ${min} digits)',
        'validator.phone_length': 'Phone must be between 8 and 15 digits',
        'validator.currency_invalid': 'Invalid currency.',
        'validator.budget_invalid': 'Invalid budget.',
        'validator.budget_min_for_currency': 'The minimum amount for ${label} is ${min}. Check the selected currency.',
        'validator.budget_max_for_currency': 'The maximum amount for ${label} is ${max}. Check the selected currency.',
        'validator.built_area_exceeds': 'Built area cannot exceed 80% of the land.',
        'validator.email_empty_or_invalid': 'Email is invalid or empty. Check your profile.',
        'validator.license_format': '3-50 characters, letters, numbers and hyphens only.',

        // === ERROR ===
        'error.server_connection': 'Server connection error',
        'error.connection': 'Connection error',
        'error.connection_retry': 'Connection error. Try again.',
        'error.phone_fetch_failed': 'Could not retrieve phone',
        'error.phone_network': 'Network error fetching phone',
        'error.phone_save': 'Error saving phone',
        'error.leads_load': 'Error loading leads',
        'error.stats_load': 'Error loading statistics',
        'error.stats_network': 'Connection error loading statistics',
        'error.upload_failed': 'Error uploading file.',
        'error.upload_network': 'Connection error uploading file.',
        'error.file_type_not_allowed': 'File type not allowed. Use: PDF, JPG or PNG.',
        'error.file_too_large': 'The file exceeds ${max} MB.',
        'error.report': 'Error reporting',
        'error.process_request': 'Error processing request.',
        'error.load': 'Error loading',
        'error.delete': 'Error deleting',
        'error.restore': 'Error restoring',
        'error.users_load': 'Error loading users.',
        'error.password_reset': 'Error resetting password.',
        'error.disable': 'Error disabling.',
        'error.reactivate': 'Error reactivating.',
        'error.avatar_upload': 'Error uploading photo',
        'error.avatar_delete': 'Error deleting photo',
        'error.sessions_load': 'Error loading sessions',
        'error.activity_load': 'Error loading activity',
        'error.code_send': 'Error sending code.',
        'error.form_options_load': 'Error loading options',
        'error.generic': 'Error',

        // === STATUS ===
        'status.approved': 'Approved',
        'status.rejected': 'Rejected',
        'status.pending': 'Pending',
        'status.processed': 'Processed',
        'status.active': 'Active',
        'status.inactive': 'Inactive',
        'status.seen': 'Seen',
        'status.contacted': 'Contacted',
        'status.account_disabled': 'Account disabled',
        'status.no_account': 'No account',
        'status.no_document': 'No document',
        'status.protected': 'Protected',

        // === ROLE ===
        'role.admin': 'Admin',
        'role.professional': 'Professional',
        'role.client': 'Client',

        // === THEME ===
        'theme.light': 'Light Mode',
        'theme.dark': 'Dark Mode',

        // === PROPERTY ===
        'property.department': 'Apartment',
        'property.house': 'House',
        'property.duplex': 'Duplex',
        'property.penthouse': 'Penthouse',
        'property.commercial': 'Commercial',

        // === BUDGET ===
        'budget.unlimited': 'Unlimited',
        'budget.greater_than': 'Budget greater than ',
        'budget.label': 'Budget: ',
        'budget.up_to_200k': 'Up to $200k',
        'budget.200k_500k': '$200k–$500k',
        'budget.500k_1m': '$500k–$1M',
        'budget.1m_2m': '$1M–$2M',
        'budget.over_2m': 'Over $2M',

        // === CURRENCY ===
        'currency.usd_name': 'Dollars',
        'currency.eur_name': 'Euros',
        'currency.arg_name': 'Pesos',

        // === OPERATION ===
        'operation.buy': 'Buy',
        'operation.remodel': 'Remodel',
        'operation.build': 'Build',

        // === STYLE ===
        'style.modern': 'Modern',
        'style.classic': 'Classic',
        'style.minimalist': 'Minimalist',
        'style.industrial': 'Industrial',
        'style.rustic': 'Rustic',
        'style.contemporary': 'Contemporary',
        'style.avant_garde': 'Avant-garde',
        'style.traditional': 'Traditional',
        'style.mediterranean': 'Mediterranean',
        'style.nordic': 'Nordic',
        'style.colonial': 'Colonial',
        'style.art_deco': 'Art Deco',
        'style.bauhaus': 'Bauhaus',
        'style.organic': 'Organic',
        'style.high_tech': 'High-Tech',
        'style.neoclassic': 'Neoclassic',
        'style.gothic': 'Gothic',
        'style.baroque': 'Baroque',
        'style.renaissance': 'Renaissance',
        'style.other': 'Other',

        // === AUTOCOMPLETE ===
        'autocomplete.use_query': 'Use: ${query}',
        'autocomplete.free_text': '(free text)',
        'autocomplete.type_zone': 'Type a zone',
        'autocomplete.no_matches': 'No matches',

        // === UPLOAD ===
        'upload.drag_here': 'Drag your file here',
        'upload.or_click': 'or click to select',
        'upload.max_size': 'PDF · JPG · PNG · Max. ${max} MB',
        'upload.remove_file': 'Remove file',
        'upload.uploading': 'Uploading document...',
        'upload.doc_loaded': 'Document loaded',
        'upload.replace_doc': 'Replace document',
        'upload.submit_docs': 'Upload Documentation',
        'upload.docs_sent': 'Documentation submitted',

        // === FILTER ===
        'filter.zone_label': 'Zone: ${zone}',
        'filter.active_count': 'active',
        'filter.all': 'All',

        // === TIME ===
        'time.today': 'Today',
        'time.7_days': '7 days',
        'time.30_days': '30 days',

        // === LEADS ===
        'leads.searching': 'Searching leads...',
        'leads.no_results': 'No results for these filters',
        'leads.no_results_hint': 'Try adjusting the property type or investment range',
        'leads.no_type': 'No type',
        'leads.seen_by_singular': 'agency has seen',
        'leads.seen_by_plural': 'agencies have seen',
        'leads.view_singular': 'view',
        'leads.view_plural': 'views',
        'leads.under_review': 'Under review',
        'leads.contacted_by': '{count} professional(s) contacted your request',
        'leads.contact_names': '{names} contacted your request',

        // === SPEC ===
        'spec.rooms': 'rooms',
        'spec.bedrooms': 'bedrms',
        'spec.bathrooms': 'bathrooms',
        'spec.land_m2': 'm² land',

        // === PARKING ===
        'parking.none': 'No garage',
        'parking.single': 'Single garage',
        'parking.double': 'Double garage',
        'parking.open': 'Open',
        'parking.garage': 'Garage',

        // === CHART ===
        'chart.no_type': 'No type',
        'chart.no_zone': 'No zone',
        'chart.types': 'types',
        'chart.zones': 'zones',
        'chart.months': 'months',
        'chart.no_data': 'No data',

        // === STATS ===
        'stats.new_this_month': 'New this month',
        'stats.requests_total': 'requests in total',

        // === PREVIEW ===
        'preview.operation': 'Operation',
        'preview.housing': 'Housing',
        'preview.zone': 'Zone',
        'preview.budget': 'Budget',
        'preview.specifications': 'Specifications',

        // === MONTH ===
        'month.january': 'January',
        'month.february': 'February',
        'month.march': 'March',
        'month.april': 'April',
        'month.may': 'May',
        'month.june': 'June',
        'month.july': 'July',
        'month.august': 'August',
        'month.september': 'September',
        'month.october': 'October',
        'month.november': 'November',
        'month.december': 'December',

        // === CONFIRM DIALOGS ===
        'confirm.reject_professional_warning': 'WARNING! You are about to REJECT this professional...',
        'confirm.approve_professional': 'Do you want to approve this professional to access the platform?',
        'confirm.delete_lead': 'Permanently delete lead #${id}? This action cannot be undone.',
        'confirm.restore_report': 'Restore this report to pending status?',
        'confirm.delete_option': 'Delete this option?',
        'confirm.delete_avatar': 'Delete profile photo?',
        'confirm.delete_pro_photo': 'Delete professional photo?',
        'confirm.close_session': 'Close this session?',

        // === PHONE ===
        'phone.enter_number_first': 'Enter a number before saving.',
        'phone.saved_to_profile': 'Phone saved to your profile.',
        'phone.not_verified': 'Not verified',
        'phone.will_send_as': '✓ Will be sent as ${e164}',
        'phone.verified': 'Verified',
        'phone.unverified': 'Unverified',
        'phone.none': 'No phone',

        // === PASSWORD ===
        'password.empty': 'empty',
        'password.weak': 'weak',
        'password.fair': 'fair',
        'password.good': 'good',
        'password.strong': 'strong',
        'password.very_weak': 'Very weak',
        'password.mismatch': 'Passwords do not match.',
        'password.min_length': 'Password must be at least 6 characters.',
        'password.all_fields_required': 'All fields are required',
        'password.hide': 'Hide password',
        'password.show': 'Show password',

        // === USERNAME ===
        'username.taken': '✗ That username is already taken',
        'username.available': '✓ Available',

        // === FORM ===
        'form.review_fields': 'Review the marked fields before continuing.',

        // === LICENSE ===
        'license.required_for_pro': 'License is required for professionals.',
        'license.verified': '✓ Verified',
        'license.not_verified': 'Not verified',

        // === AVATAR ===
        'avatar.updated': 'Photo updated',
        'avatar.deleted': 'Photo deleted',

        // === SESSIONS ===
        'sessions.loading': 'Loading sessions...',
        'sessions.empty': 'No sessions recorded.',
        'sessions.device': 'Device',
        'sessions.last_activity': 'Last activity',

        // === ACTIVITY ===
        'activity.loading': 'Loading activity...',
        'activity.empty': 'No activity recorded yet.',

        // === VERIFICATION ===
        'verification.enter_full_code': 'Enter the full 6-digit code.',
        'verification.success': 'Phone verified successfully',
        'verification.expired': 'Code expired. Request a new one.',
        'verification.incorrect': 'Incorrect code.',
        'verification.resent': 'Code resent',

        // === DASHBOARD (admin) ===
        'dashboard.pct_of_total': '% of total',
        'dashboard.requires_review': '⚠ Requires review',
        'dashboard.success_rate': '% successful attempts',
        'dashboard.success_rate_short': 'success rate',
        'dashboard.call_clicks': 'clicks on Call',

        // === PROS (admin) ===
        'pros.no_results': 'No professionals found with the applied filters.',

        // === ADMIN ===
        'admin.admin_action': 'Administrative action',
        'admin.reactivate_account': 'Reactivate Account',
        'admin.reactivate_warning': 'The user will regain access to the platform immediately.',
        'admin.disable_account': 'Disable Account',
        'admin.disable_warning': 'The user will lose access immediately.',

        // === REPORTS (admin) ===
        'reports.empty': 'No reports to display',
        'reports.lead_deleted': 'Lead deleted',

        // === SUCCESS ===
        'success.lead_deleted': 'Lead deleted successfully',
        'success.report_dismissed': 'Report dismissed',
        'success.report_restored': 'Report restored successfully',

        // === DETAIL (admin lead detail) ===
        'detail.not_specified': 'Not specified',
        'detail.not_specified_fem': 'Not specified',
        'detail.department': 'Apartment Details',
        'detail.useful_meters': 'Usable Area',
        'detail.elevator': 'Elevator',
        'detail.house': 'House Details',
        'detail.land': 'Land',
        'detail.built': 'Built',
        'detail.pool': 'Pool',
        'detail.operation_type': 'Operation Type',
        'detail.housing_type': 'Housing Type',
        'detail.zone': 'Zone',
        'detail.budget': 'Budget',
        'detail.architectural_style': 'Architectural Style',
        'detail.parking': 'Parking',
        'detail.orientation': 'Orientation',
        'detail.condition': 'Condition',
        'detail.age': 'Age',
        'detail.contact': 'Contact',
        'detail.registered': 'Registered',
        'detail.technical_specs': 'Technical Specifications',
        'detail.bedrooms': 'Bedrooms',
        'detail.bathrooms': 'Bathrooms',
        'detail.meters': 'Meters',
        'detail.extras_amenities': 'Extras and Amenities',

        // === PAGINATION ===
        'pagination.reports_page': 'Page ${page} of ${totalPages} (${total} reports)',
        'pagination.audit_page': 'Page ${page} of ${totalPages} (${total} accesses)',

        // === AUDIT ===
        'audit.revealed': 'Revealed',
        'audit.whatsapp': 'WhatsApp',
        'audit.lead_deleted': 'Lead deleted',

        // === FORM OPTIONS (admin) ===
        'form_options.empty': 'No options',
        'form_options.zero_found': '0 options found',
        'form_options.results_count': '${count} option(s) found',
        'form_options.new_option': 'New Option',
        'form_options.category': 'Category',
        'form_options.value': 'Value',
        'form_options.value_placeholder': 'e.g.: apartment',
        'form_options.label': 'Label',
        'form_options.label_placeholder': 'e.g.: Apartment',
        'form_options.icon_optional': 'Icon (optional)',
        'form_options.sort_order': 'Sort order',
        'form_options.value_label_required': 'Value and label are required',
        'form_options.updated': 'Option updated',
        'form_options.created': 'Option created',
        'form_options.activated': 'Option activated',
        'form_options.deactivated': 'Option deactivated',
        'form_options.deleted': 'Option deleted',
        'form_options.edit_option': 'Edit Option',
        'form_options.select': 'Select',

        // === ICON SEARCH (admin) ===
        'icon.search': 'Search icon',
        'icon.search_placeholder': 'Search icon...',
        'icon.none': 'None',

        // === USERS (usermgmt) ===
        'users.no_results': 'No users found.',
        'email.none': 'No email',

        // === FIELD ===
        'field.not_specified': 'Not specified',

        // === EXTRA MISSING KEYS ===
        'action.dismiss': 'Dismiss',
        'status.deleted': 'Deleted',
        'status.disabled': 'Disabled',
        'status.dismissed': 'Dismissed',
        'admin.disable_account_btn': 'Disable',
        'admin.reactivate_account_btn': 'Reactivate',
        'dashboard.leads': 'Leads',
        'dashboard.phone_success_rate': '% successful attempts',
        'dashboard.this_month': 'This month',
        'detail.arch_style': 'Architectural Style',
        'detail.extras': 'Extras',
        'detail.floor_block': 'Floor / Block',
        'detail.not_specified_pl': 'Not specified',
        'detail.property_type': 'Property Type',
        'detail.province': 'Province',
        'detail.rooms': 'Rooms',
        'error.options_load': 'Error loading options',
        'error.pros_load': 'Error loading professionals',
        'form_options.all_categories': 'All',
        'form_options.icon': 'Icon',
        'form_options.required_fields': 'Value and label are required',
        'icon.none_label': 'None',
        'pros.no_account': 'No account',
        'pros.no_document': 'No document',
        'pros.not_found': 'No professionals found.',
        'style.hightech': 'High-Tech',
        'style.vanguard': 'Avant-garde',
        'success.option_activated': 'Option activated',
        'success.option_created': 'Option created',
        'success.option_deactivated': 'Option deactivated',
        'success.option_deleted': 'Option deleted',
        'success.option_updated': 'Option updated',
    }
};

window.__LANG = document.documentElement.lang || 'es';

window.t = function(key, params) {
    var dict = window.I18N[window.__LANG] || window.I18N.es;
    var val = dict[key] || key;
    if (params) {
        Object.keys(params).forEach(function(k) {
            val = val.replace('${' + k + '}', params[k]);
            val = val.replace('{' + k + '}', params[k]);
        });
    }
    return val;
};
