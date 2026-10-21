# Plan: Mejorar coherencia, animaciones y personalización por rol en la landing

**Fecha:** 2026-10-21  
**Alcance:** Sin refactor completo. Cambios incrementales.  
**Objetivo:** Hacer la landing más fácil de usar tanto desde el inicio como cuando ya hay un rol definido, manteniendo el diseño actual.

## Decisiones confirmadas

| Punto | Decisión | Notas |
| :-- | :-- | :-- |
| 1) Sesión vs landing | **Ocultar los 3 cards si hay sesión** | Solo mostrar hero personalizado + CTA directo al panel. Se mantienen `stats`, "Cómo funciona" y `FAQ` para no romper la landing. |
| 2) Header | **Cambios puntuales en `base.html`** | Sin reescribir navbar completo. Únicamente lo justo para coherencia. |
| 3) Badge de rol | **Solo en el navbar** | Pequeño `pill` con colores distintos por rol, prioridad sutil. No duplicar en hero. |
| 4) Footer | **Solo ritmo visual** | Ajustar paddings, borde superior, tipografía y espaciados. Sin agregar links nuevos. |
| 5) Jerarquía de cards (anónimo) | **Énfasis sutil** | Mantener las 3 cards, dar ligero énfasis con borde dorado fino/glow muy sutil. Sin banner gigante. |
| 6) Animaciones | **Normalizar + `prefers-reduced-motion`** | Mantener mismas clases/estructura de `landing.js`. Unificar timings/easings donde aplique y reforzar reduced motion. |

## Archivos a modificar

| Archivo | Acción |
| :-- | :-- |
| `templates/landing.html` | Lógica condicional por sesión/rol. Ocultar bloque de 3 cards si logueado. Hero "Bienvenido de vuelta" con CTA al panel según rol + link "Conocer más" para scrollear. |
| `templates/base.html` | Cambios puntuales en navbar logueado: mostrar `username` + pill de rol con colores por rol. Sin tocar mobile menu, notificaciones ni lógica existente. |
| `static/css/landing.css` | Ajustes footer (ritmo visual). Jerarquía sutil para cards anónimos. Reforzar `prefers-reduced-motion`. |
| `static/js/landing.js` | Detectar `prefers-reduced-motion`. Omitir parallax, typing effect, magnetic hover y evitar/omitir partículas. Mantener scroll-reveals, contadores, step connectors, navbar shrink, FAQ y alerta. |
| `i18n/translations.py` | Añadir keys mínimas: `hero.welcome_back`, `hero.continue_to_panel`, `hero.learn_more` (ES/EN). |

## Detalles de implementación

### 1) Hero personalizado (logueado)
- Texto: `{{ t('hero.welcome_back') }} {{ session.get('username') }}`
- CTA primario según rol:
  - `admin` → `{{ url_for('admin.admin_view') }}`
  - `professional` → `{{ url_for('professional.professional_view') }}`
  - `client` → `{{ url_for('client.user_view') }}`
- CTA secundario: link con `href="#how-it-works"` o al bloque correspondiente para "Conocer más" sin mostrar cards.
- Mantener resto de secciones (`stats`, `how-it-works`, `FAQ`).

### 2) Badge de rol en navbar
| Rol | Clases sugeridas |
| :-- | :-- |
| `client` | `text-[9px] uppercase tracking-widest px-2 py-0.5 rounded-full bg-paper-dark/70 text-midnight/70 border border-midnight/10` |
| `professional` | `text-[9px] uppercase tracking-widest px-2 py-0.5 rounded-full bg-gold/10 text-gold border border-gold/25` |
| `admin` | `text-[9px] uppercase tracking-widest px-2 py-0.5 rounded-full bg-midnight/90 text-gold border border-gold/35` |

Solo visible cuando hay sesión. Ubicado junto al username, alineado verticalmente.

### 3) Jerarquía sutil cards anónimas
- Mantener los 3 `<a>` existentes.
- Aplicar énfasis muy sutil (borde dorado fino / ligero shadow) sin cambiar estructura/grid.
- Asegurar `:focus-visible` correcto.
- Sin mover orden ni convertir en banner.

### 4) Footer
- Ajustar paddings verticales
- Afinar borde superior (`border-gold/15` aprox)
- Mantener tipografía/estilo existente
- Sin agregar links

### 5) Animaciones
- En `landing.js` leer `matchMedia('(prefers-reduced-motion: reduce)')` al inicio
- Si reducido: omitir parallax, typing, magnetic hover, deshabilitar/omitir partículas
- Mantener scroll-reveals, counters, connectors, navbar shrink, FAQ, alerta
- Normalizar timings/easings donde haya inconsistencias

## Orden de implementación
1. `templates/landing.html` - lógica por sesión + ocultar cards + hero personalizado
2. `templates/base.html` - badge de rol puntual en navbar
3. `static/css/landing.css` - footer + jerarquía cards + reduced motion
4. `static/js/landing.js` - reduced motion
5. `i18n/translations.py` - keys mínimas
6. Validación

## Validación
- [ ] Anónimo: ve 3 cards con jerarquía sutil
- [ ] Logueado (cliente/profesional/admin): ocultan cards, hero personalizado + CTA correcto, badge solo en navbar con color correcto
- [ ] Reduced motion activo: sin parallax/typing/magnetic/partículas
- [ ] Mobile: layout correcto
- [ ] Light/Dark: legible
- [ ] Footer con ritmo visual ajustado
- [ ] Sin rotura de secciones restantes
- [ ] `python -m pytest tests/test_public_bp.py tests/test_i18n.py -v`
- [ ] `python verify_coherence.py`
- [ ] `node --check` en JS modificados
