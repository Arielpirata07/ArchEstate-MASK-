# ArchEstate - Design System

## Design Tokens

### Colors

| Token | Hex | Uso principal |
|-------|-----|---------------|
| `midnight` | `#000410` | Texto primario, fondos oscuros, botones primarios |
| `midnight-light` | `#101E33` | Navbar, superficies oscuras secundarias |
| `gold` | `#735A3A` | Acento primario, estados activos, bordes de énfasis |
| `gold-light` | `#A68A64` | Acento secundario, highlights sutiles |
| `paper` | `#FAF9F7` | Fondo de página |
| `paper-dark` | `#F4F3F1` | Headers de card, fondos sutiles de sección |

**Colores semánticos** (Tailwind por defecto, usar con moderación):
- `emerald-50/100/600/700` — Estados de éxito, aprobación
- `rose-50/100/500/600/700` — Error, peligro, rechazo
- `amber-50/100/400/700` — Advertencia, pendiente
- `blue-50/700` — Información neutra

### Typography

| Elemento | Fuente | Tamaño | Peso | Estilo |
|----------|--------|--------|------|--------|
| Título de página | Newsreader | `text-4xl` | — | Cursiva en acento |
| Subtítulo de sección | Newsreader | `text-2xl`–`text-3xl` | — | Cursiva |
| Título de card | Newsreader | `text-lg`–`text-xl` | — | Normal o cursiva |
| Cuerpo | Manrope | `text-sm`–`text-base` | — | — |
| Labels de campo | Manrope | `text-[10px]` | bold | uppercase tracking-widest |
| Headers de tabla | Manrope | `text-[10px]` | bold | uppercase tracking-widest text-gold |
| Badges | Manrope | `text-[9px]` | bold | uppercase tracking-widest |
| Micro-texto | Manrope | `text-[8px]`–`text-[9px]` | bold | uppercase tracking-widest |

**Fuentes cargadas:** Newsreader (200–800, cursiva) + Manrope (200–800) via Google Fonts.

> ⚠️ Toda clase custom de Tailwind (colores, fuentes) debe estar en `static/js/tailwind-config.js`.

---

## Dark Mode

Activado con clase `dark` en `<html>`. Toggle en `dark-mode.js`. La preferencia se guarda en `user_preferences.theme`.

### Variables CSS

| Variable | Light | Dark |
|----------|-------|------|
| `--bg-primary` | `#FAF9F7` | `#0a0e1a` |
| `--bg-secondary` | `#F4F3F1` | `#101E33` |
| `--bg-card` | `#FFFFFF` | `#1a2332` |
| `--text-primary` | `#000410` | `#FAF9F7` |
| `--text-secondary` | `rgba(0,4,16,0.5)` | `rgba(250,249,247,0.6)` |
| `--accent` | `#735A3A` | `#A68A64` |
| `--border` | `rgba(0,4,16,0.1)` | `rgba(250,249,247,0.1)` |

### Overrides de Tailwind

Clases como `bg-white`, `bg-paper`, `text-midnight`, `border-midnight/20` se mapean automáticamente a valores dark via CSS en `base.css`. No usar colores hardcodeados — usar las clases Tailwind estándar que ya tienen override.

Ejemplo: `.dark .bg-white { background: var(--bg-card) }` convierte cualquier `bg-white` a color oscuro.

### Transición

`<html class="theme-transition">` aplica `transition: background-color 0.4s` a todos los elementos durante el cambio de tema. Se remueve después de 400ms.

---

## Componentes

### Botones

**Primario (CTA principal):**
```
bg-gold text-white py-4 rounded font-bold uppercase tracking-widest text-xs hover:bg-midnight transition-all duration-300
```

**Secundario:**
```
bg-paper-dark text-midnight hover:bg-gold hover:text-white transition-all duration-300 rounded text-[10px] font-bold uppercase tracking-widest border border-midnight/5
```

**Peligro / Baja:**
```
bg-rose-600 text-white rounded text-[10px] font-bold uppercase tracking-widest hover:bg-midnight transition-all duration-300
```

**Acción de tabla (ghost oscuro):**
```
inline-flex items-center gap-1.5 px-3 py-2 bg-midnight text-white rounded text-[10px] font-bold uppercase tracking-widest hover:bg-gold transition-all
```

**Acción de tabla (ghost dorado):**
```
inline-flex items-center gap-1.5 px-3 py-2 bg-gold text-white rounded text-[10px] font-bold uppercase tracking-widest hover:bg-midnight transition-all
```

**Acción de tabla (ghost claro):**
```
inline-flex items-center gap-1.5 px-3 py-2 bg-paper-dark text-midnight rounded text-[10px] font-bold uppercase tracking-widest hover:bg-gold hover:text-white transition-all
```

**Ícono solo:**
```
p-2 rounded hover:bg-paper-dark transition-all duration-200 text-midnight/30 hover:text-gold
```

### Cards

**Estándar:**
```
bg-white rounded-lg shadow-xl overflow-hidden
```

**Con borde lateral (KPI):**
```
bg-white rounded-lg shadow p-5 border-l-4 border-{color}
```

**Interactiva con hover:**
```
bg-white rounded-lg shadow-lg border border-midnight/5 card-hover
```

**Auth (login/register):**
```
bg-white p-10 rounded-lg shadow-2xl border-t-4 border-gold
```

**Panel de estado pendiente (oscuro):**
```
bg-midnight rounded-lg p-8
```

### Inputs

**Border-bottom (formularios principales):**
```
bg-transparent border-0 border-b-2 border-midnight/20 focus:border-gold focus:ring-0 py-2 transition-all text-sm outline-none
```

**Con ícono prefijo (border-bottom):**
```
bg-transparent border-0 border-b border-midnight/10 focus:border-gold focus:ring-0 py-3 pl-8 transition-all outline-none
```

**Bordered (filtros y admin):**
```
px-3 py-2 border border-midnight/20 rounded text-sm focus:border-gold focus:outline-none transition-all
```

**Búsqueda con ícono:**
```
pl-8 pr-3 py-2 border border-midnight/20 rounded text-sm focus:border-gold focus:outline-none w-full
```
+ ícono `<i data-lucide="search">` absoluto a la izquierda.

### Selects

```
bg-paper-dark border-0 border-b border-midnight/10 focus:border-gold focus:ring-0 py-3 transition-all text-sm
```

Para filtros admin/profesional (bordered):
```
px-3 py-2 border border-midnight/20 rounded text-sm focus:border-gold focus:outline-none
```

### Badges de Estado

```
px-2 py-1 rounded text-[9px] font-bold uppercase tracking-widest
```

| Estado | Clases |
|--------|--------|
| Aprobado / Activo | `bg-emerald-50 text-emerald-700` |
| Rechazado / Baja | `bg-rose-50 text-rose-700` |
| Pendiente | `bg-amber-50 text-amber-700` |
| Cuenta baja | `bg-midnight/10 text-midnight/50` |
| Neutro | `bg-paper-dark text-midnight/60` |

### Chips de Selección (user.html / professional.html)

**Horizontal (parking, orientación):**
```
px-3 py-2 rounded border-2 text-[10px] font-bold uppercase tracking-widest transition-all
```

**Vertical en lista (estado, antigüedad):**
```
w-full text-left px-3 py-2 rounded border-2 text-[10px] font-bold uppercase tracking-widest transition-all
```

**Redondeados (filtros de profesional):**
```
px-3 py-1.5 rounded-full text-[10px] font-bold uppercase tracking-widest border transition-all
```

**Estados de chip:**
- Activo: `border-midnight bg-midnight text-white`
- Inactivo: `border-midnight/20 text-midnight hover:border-gold`

> ⚠️ Al cambiar el estado de un chip, **reconstruir `className` completo** desde la cadena base — nunca usar `String.replace()` con regex sobre clases Tailwind (los `/` en `border-midnight/20` lo rompen).

### Steppers +/−

```html
<div class="flex items-center gap-3">
    <button type="button" onclick="stepNum('campo', -1)"
        class="w-8 h-8 rounded-full border border-midnight/20 flex items-center justify-center
               text-midnight hover:border-gold hover:text-gold transition-all text-lg leading-none">−</button>
    <input id="campo-input" name="campo" type="number" min="0" max="20" value="" placeholder="—"
           class="w-12 text-center bg-white border-0 border-b-2 border-midnight/20 focus:border-gold focus:ring-0 py-1 text-sm font-semibold">
    <button type="button" onclick="stepNum('campo', 1)"
        class="w-8 h-8 rounded-full border border-midnight/20 flex items-center justify-center
               text-midnight hover:border-gold hover:text-gold transition-all text-lg leading-none">+</button>
</div>
```

### Upload Widget (professional.html)

Zona drag & drop renderizada por JS (`renderUploadWidget(containerId)`). Estados:
1. **Dropzone** — borde punteado, ícono cloud, hover con highlight gold
2. **Preview** — ícono por tipo (PDF rojo / imagen azul), nombre, tamaño, botón X
3. **Progreso** — barra gold animada con porcentaje
4. **Éxito** — banner emerald con nombre y botón de descarga + opción "Reemplazar"

### Status Buttons (Visto/Contactado)

Componente CSS custom en `professional.css` (no Tailwind puro).

- Base: `.status-btn`
- Activo Visto: `.status-btn.status-active.status-btn-seen` → gold (`#735A3A`)
- Activo Contactado: `.status-btn.status-active.status-btn-contacted` → emerald (`#059669`)
- Animación toggle: `.status-btn.status-toggling` → pulse scale 1→1.06→1

Uso en JS: toggle manual de clases CSS. El ícono Lucide usa `fill: currentColor; fill-opacity: 0.15` cuando está activo.

### Budget Popup

Overlay `fixed inset-0 z-50` con slider dual range + inputs numéricos. Componente en `main.js`.

- Trigger: `#budget-popup-trigger`
- Panel: `bg-white rounded-2xl shadow-2xl p-8 w-full max-w-lg mx-4`
- Currency select: ARG / USD / EUR
- Slider: dos `input[type=range]` superpuestos con fill gold (`#budget-slider-fill`)
- Inputs numéricos: min/max inline
- Checkbox "Sin límite máximo"
- Botones: "Restablecer" (border) + "Aceptar" (bg-midnight)
- Cierra con `#budget-popup-close` o click fuera del panel

### OTP Modal (Verificación Telefónica)

Modal inline en `profile.html` (no usa `showToast()`).

- Overlay: `bg-midnight/60 backdrop-blur-sm`
- Panel: `bg-white rounded-lg shadow-2xl border-t-4 border-gold`
- Input de 6 dígitos con auto-focus y espaciado amplio
- Timer de reenvío con countdown (botón deshabilitado)
- Botón "Verificar" con estado de carga
- Estados: enviado / verificado / error / expirado

### Flash Messages

Renderizadas en `base.html` vía `get_flashed_messages(with_categories=true)`.

| Categoría | Estilo |
|-----------|--------|
| `success` | `bg-emerald-50 border border-emerald-200 text-emerald-700` |
| `error` | `bg-rose-50 border border-rose-200 text-rose-700` |
| `info` | `bg-blue-50 border border-blue-200 text-blue-700` |

Se auto-ocultan después de 5s con `setTimeout` y `fadeOut`.

### Tags de Filtros Activos

```
inline-flex items-center gap-1.5 px-2.5 py-1 bg-gold/10 text-gold border border-gold/20 rounded-full text-[9px] font-bold uppercase tracking-widest
```
Con botón X interno: `hover:text-rose-500 transition-colors`.

### Tablas

```
w-full text-left border-collapse
```
- Header row: `bg-paper-dark border-b border-midnight/5`
- Header cell: `p-4 text-[10px] uppercase tracking-widest font-bold text-gold`
- Body row: `border-b border-midnight/5 hover:bg-paper transition-colors`
- Body cell: `p-4`

> Las filas de cuentas inactivas usan `opacity-60` adicional.

### Modales

**Overlay:**
```
fixed inset-0 z-50 bg-midnight/60 backdrop-blur-sm
```

**Panel:**
```
absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-md
bg-white rounded-lg shadow-2xl border-t-4 border-gold overflow-hidden
```

**Aviso interno (warning box):**
```
mx-8 mb-6 p-3 bg-{color}-50 border border-{color}-100 rounded flex items-start gap-3
```

> Los modales que cambian íconos dinámicamente deben reconstruir `innerHTML` completo del botón/aviso — no mutar el `<svg>` que Lucide genera.

### Toasts

Definidos en `main.js → showToast(message, type)`. Posición: `fixed bottom-8 right-8 z-[100]`.

| Tipo | Color |
|------|-------|
| `'success'` | `bg-emerald-600` |
| `'error'` | `bg-rose-600` |
| `'info'` | `bg-midnight` |

### Panel de Pasos (Estado Pendiente)

Fondo `bg-midnight`, pasos con íconos circulares:
- Completado: `bg-gold` con check blanco
- Pendiente: `bg-white/10 border border-white/20` con número
- Labels: `text-white` / `text-white/60` según estado

### Form Validation States

Clases CSS en `base.css` para validación en tiempo real:

| Clase | Efecto |
|-------|--------|
| `.input-valid` | Borde emerald (`#059669`) |
| `.input-invalid` | Borde rose (`#e11d48`) |
| `.field-error` | Texto error inline (oculto por defecto, `opacity: 0`) |
| `.field-error--visible` | Muestra el error (`opacity: 1`) |

Validación en tiempo real: `main.js` → `validateEmail()`, `validateBudgetForCurrency()`. El campo `.input-animated` tiene una línea gold que crece desde el centro al hacer focus.

---

### Contenedor de página
```
max-w-7xl mx-auto w-full pt-24 pb-12 px-6
```

### Grids frecuentes

| Uso | Clases |
|-----|--------|
| Cards de landing (3 col) | `grid-cols-1 md:grid-cols-3 gap-6` |
| KPI cards (4 col) | `grid-cols-2 md:grid-cols-4 gap-4` |
| Form de usuario (pending + upload) | `grid-cols-1 lg:grid-cols-5 gap-8` (2+3) |
| Dashboard charts fila 1 | `grid-cols-1 md:grid-cols-2 gap-6` |
| Dashboard charts fila 2 | `grid-cols-1 md:grid-cols-3 gap-6` (2+1) |
| Form de 2 columnas | `grid-cols-2 gap-6` |
| Admin gestión | `grid-cols-1 lg:grid-cols-3 gap-8` (2+1) |

---

## Sistema de Animaciones

### Duraciones
| Nombre | Duración | Uso |
|--------|----------|-----|
| fast | 150ms | Hover de estado |
| normal | 300ms | Card hover, transiciones de botón |
| slow | 500ms | Apertura de modal |
| slower | 800ms | Animaciones scroll-triggered |

### Keyframes disponibles (landing.css)
| Nombre | Efecto |
|--------|--------|
| `fadeInUp` | opacity 0→1 + translateY(30px)→0 |
| `slideInLeft` / `slideInRight` | Entrada lateral |
| `float` | Oscilación vertical (elementos decorativos) |
| `pulseGlow` | Box-shadow animado |
| `typing` + `blink` | Efecto máquina de escribir |

### Contadores animados (dashboard)
```javascript
function animateCounter(el, target) {
    const duration = 700;
    const start = performance.now();
    const step = (now) => {
        const t = Math.min((now - start) / duration, 1);
        el.textContent = Math.round(target * (1 - Math.pow(1 - t, 3)));
        if (t < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
}
```

---

## Accesibilidad

- Contraste mínimo WCAG AA: 4.5:1 para texto normal — `text-midnight/40` falla en fondo blanco para 10px, usar mínimo `text-midnight/50`
- Focus en inputs: `focus:border-gold focus:outline-none`
- Focus visible global: `outline: 2px solid #735A3A; outline-offset: 2px` en todos los interactivos via `base.css`
- Focus en botones: `focus:ring-2 focus:ring-gold focus:ring-offset-2`
- Botones solo-ícono: `aria-label` o `title`
- **Skip link**: `.skip-link` — aparece al hacer Tab desde el top, lleva al contenido principal
- **Visually hidden**: `.visually-hidden` — contenido solo para screen readers (1px clip)
- **Target size**: botones y links tienen `min-width/min-height: 24px` (WCAG 2.5.8)
- **`:target` offset**: `scroll-margin-top: 80px` para headers sticky
- Modales: `Escape` cierra, foco atrapado dentro con Tab cycle
- ARIA en modales: `role="dialog"`, `aria-modal="true"`, `aria-labelledby` apuntando al título

---

## Anti-patterns

| ❌ NO hacer | ✅ Hacer en cambio |
|-------------|-------------------|
| `bg-[#735A3A]` | `bg-gold` |
| `alert()` / `confirm()` | `showToast()` / modal personalizado |
| Mutating className con `.replace()` en clases Tailwind con slash | Reconstruir `className` completo desde string base |
| `querySelector('i')` en un contenedor donde Lucide ya inicializó | Reconstruir `innerHTML` con nuevos `<i>` y llamar `lucide.createIcons()` |
| Mutar `<svg>` que Lucide ya generó | Reconstruir `<innerHTML>` con `<i data-lucide>` y llamar `lucide.createIcons()` |
| Usar `window.event` implícito | Pasar `event` como parámetro explícito en handlers inline |
| Mezclar `rounded-3xl` y `rounded-lg` en la misma página | `rounded-lg` para todo |
| Íconos emoji en lugar de Lucide | `<i data-lucide="nombre">` |
| JS inline que duplica lógica de `main.js` | Importar/usar las funciones globales |
| `text-midnight/40` en texto de 10px | `text-midnight/50` mínimo |