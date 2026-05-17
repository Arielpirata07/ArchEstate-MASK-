# ArchEstate - Design System

## Design Tokens

### Colors

| Token | Hex | Usage |
|-------|-----|-------|
| `midnight` | `#000410` | Primary text, dark backgrounds, buttons |
| `midnight-light` | `#101E33` | Navbar, secondary dark surfaces |
| `gold` | `#735A3A` | Primary accent, active states, borders, links |
| `gold-light` | `#A68A64` | Secondary accent, subtle highlights |
| `paper` | `#FAF9F7` | Page background |
| `paper-dark` | `#F4F3F1` | Card headers, subtle backgrounds |

**Semantic colors** (Tailwind defaults, usar con moderacion):
- `emerald-50/500/600/700` - Success states
- `rose-50/500/600` - Error/danger states
- `amber-50/400` - Warning/pending states

### Typography

| Element | Font | Size | Weight | Style |
|---------|------|------|--------|-------|
| Page title | Newsreader | `text-4xl` | default | italic accent |
| Section title | Newsreader | `text-lg` | default | italic |
| Body | Manrope | `text-sm` / `text-base` | default | - |
| Labels | Manrope | `text-[10px]` | bold | uppercase, tracking-widest |
| Table headers | Manrope | `text-[10px]` | bold | uppercase, tracking-widest, text-gold |
| Badges | Manrope | `text-[9px]` | bold | uppercase, tracking-widest |
| Micro-text | Manrope | `text-[8px]` | default | - |

**Fonts loaded:**
- Newsreader (200-800, italic) via Google Fonts
- Manrope (200-800) via Google Fonts

### Spacing

| Context | Pattern |
|---------|---------|
| Page container | `max-w-7xl mx-auto w-full pt-24 pb-12 px-6` |
| Section gap | `space-y-8` |
| Form sections | `space-y-10` |
| Form fields | `mb-6` / `mb-8` |
| Grid gap | `gap-4` / `gap-6` / `gap-8` |
| Card padding | `p-6` / `p-8` / `p-10` |
| Label margin | `mb-2` / `mb-3` |

### Border Radius

| Element | Value |
|---------|-------|
| Cards | `rounded-lg` |
| Buttons | `rounded` |
| Chips | `rounded-full` |
| Badges | `rounded` |
| Inputs | `rounded` (solo bordered style) |
| Modals | `rounded-lg` |

### Shadows

| Level | Class | Usage |
|-------|-------|-------|
| Light | `shadow` | Subtle elevation |
| Medium | `shadow-lg` | Cards, dropdowns |
| Strong | `shadow-xl` | Primary cards, forms |
| Maximum | `shadow-2xl` | Modals, toast, hero elements |

---

## Component Library

### Buttons

**Primary:**
```
bg-gold text-white py-4 rounded font-bold uppercase tracking-widest text-xs hover:bg-midnight transition-all duration-300
```

**Secondary:**
```
bg-paper-dark text-midnight hover:bg-gold hover:text-white transition-all duration-300 rounded text-[10px] font-bold uppercase tracking-widest
```

**Danger:**
```
bg-rose-600 text-white rounded text-[10px] font-bold uppercase tracking-widest hover:bg-midnight transition-all duration-300
```

**Ghost/Table Action:**
```
px-3 py-2 bg-midnight text-white rounded text-[10px] font-bold uppercase tracking-widest hover:bg-gold transition-all duration-300
```

**Icon Button:**
```
p-2 rounded hover:bg-paper-dark transition-all duration-200
```

### Cards

**Standard:**
```
bg-white rounded-lg shadow-xl overflow-hidden
```

**Interactive (hover lift):**
```
bg-white rounded-lg shadow-lg border border-midnight/5 card-hover
```

**KPI:**
```
bg-white rounded-lg shadow p-5 border-l-4 border-{color}
```

**Auth (login/register):**
```
bg-white p-10 rounded-lg shadow-2xl border-t-4 border-gold
```

### Inputs

**Border-bottom style (formularios principales):**
```
bg-transparent border-0 border-b-2 border-midnight/20 focus:border-gold focus:ring-0 py-2 transition-all text-sm
```

**Bordered style (filtros, admin):**
```
px-3 py-2 border border-midnight/20 rounded text-sm focus:border-gold focus:outline-none transition-all
```

**With icon prefix:**
```
bg-transparent border-0 border-b border-midnight/10 focus:border-gold focus:ring-0 py-3 pl-8 transition-all outline-none
```

### Selects

```
bg-paper-dark border-0 border-b border-midnight/10 focus:border-gold focus:ring-0 py-3 transition-all text-sm
```

Custom chevron SVG en `user.css`.

### Badges

**Status:**
```
px-2 py-1 bg-{color}-50 text-{color}-700 text-[9px] font-bold uppercase tracking-widest rounded
```
- `emerald` = approved/active
- `rose` = rejected/error
- `amber` = pending/warning

**Role:**
```
px-2 py-1 rounded text-[9px] font-bold uppercase tracking-widest
```

**Filter tags:**
```
inline-flex items-center gap-1.5 px-2.5 py-1 bg-gold/10 text-gold border border-gold/20 rounded-full text-[9px] font-bold uppercase tracking-widest
```

### Chips

```
border-2 rounded-full px-3 py-1.5 text-[10px] font-semibold transition-all duration-200
```
- Active: `border-midnight bg-midnight text-white`
- Inactive: `border-midnight/20 text-midnight hover:border-gold`

### Tables

```
w-full text-left border-collapse
```
- Header: `bg-paper-dark border-b border-midnight/5`
- Header cells: `p-4 text-[10px] uppercase tracking-widest font-bold text-gold`
- Body rows: `border-b border-midnight/5 hover:bg-paper transition-colors`

### Modals

**Overlay:**
```
fixed inset-0 bg-midnight/60 backdrop-blur-sm z-50
```

**Container:**
```
bg-white rounded-lg shadow-2xl border-t-4 border-gold max-w-md w-full mx-4
```

**Animation:** fade-in scale-up (0.95 -> 1) 0.2s ease-out

### Toasts

```
fixed bottom-4 right-4 md:bottom-8 md:right-8 z-50
```
- Entry: slide-in from bottom + fade
- Exit: fade + slide-up
- Duration: 4000ms with progress bar
- Colors: emerald-600 (success), rose-600 (error), midnight (info)

---

## Animation System

### Durations

| Name | Duration | Usage |
|------|----------|-------|
| `fast` | 150ms | Hover state changes |
| `normal` | 300ms | Card hover, button transitions |
| `slow` | 500ms | Modal open/close, toast entry |
| `slower` | 800ms | Scroll-triggered animations |

### Easing

| Name | Curve | Usage |
|------|-------|-------|
| `ease-out` | `cubic-bezier(0.16, 1, 0.3, 1)` | Entry animations |
| `ease-in-out` | `cubic-bezier(0.4, 0, 0.2, 1)` | Continuous animations |
| `spring` | `cubic-bezier(0.34, 1.56, 0.64, 1)` | Scale/bounce effects |

### Keyframes

| Name | Effect | Usage |
|------|--------|-------|
| `fadeInUp` | opacity 0->1, translateY(30px)->0 | Scroll reveal |
| `fadeIn` | opacity 0->1 | Generic fade |
| `slideInRight` | translateX(50px)->0 | Toast entry |
| `scaleIn` | scale(0.95)->1, opacity 0->1 | Modal open |
| `scaleOut` | scale(1)->0.95, opacity 1->0 | Modal close |
| `pulse` | subtle scale oscillation | CTA buttons |
| `float` | translateY oscillation | Decorative elements |
| `shimmer` | background-position slide | Skeleton loading |
| `ripple` | scale + opacity circle | Button click effect |

### Scroll Animations

Elements with `.animate-on-scroll` class are animated when they enter the viewport via Intersection Observer:
- `.fade-in-up`: default scroll animation
- `.fade-in`: simple fade
- `.slide-in-left`: slide from left
- `.slide-in-right`: slide from right
- `.stagger-1` through `.stagger-5`: sequential delays

---

## Layout System

### Breakpoints

| Name | Width | Usage |
|------|-------|-------|
| `sm` | 640px | Mobile landscape |
| `md` | 768px | Tablet, hamburger menu breakpoint |
| `lg` | 1024px | Desktop |
| `xl` | 1280px | Large desktop |

### Grid Patterns

**3-column (landing cards):**
```
grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8
```

**2-column (user form):**
```
grid-cols-1 lg:grid-cols-2
```

**4-column (KPI cards):**
```
grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6
```

---

## Accessibility Guidelines

### Contrast
- All text must meet WCAG AA: 4.5:1 for normal text, 3:1 for large text
- `text-midnight/40` on white fails AA for 10px text - use `text-midnight/50` minimum

### Focus
- All interactive elements must have visible focus state
- Use `focus:border-gold` for inputs
- Use `focus:ring-2 focus:ring-gold focus:ring-offset-2` for buttons

### ARIA
- Modals: `role="dialog"`, `aria-modal="true"`, `aria-labelledby`
- Icon-only buttons: `aria-label`
- Forms: `id`/`for` label associations

### Keyboard
- Skip-to-content link as first focusable element
- Escape closes modals
- Tab trap within modals
- All interactive elements reachable via keyboard

---

## Anti-patterns

### DO NOT
- Use hardcoded hex colors instead of Tailwind tokens (e.g., `bg-[#735A3A]` instead of `bg-gold`)
- Mix `rounded-3xl` cards with `rounded-lg` cards in the same page
- Use emoji icons instead of Lucide icons
- Create duplicate CSS rules across files
- Add inline JS that duplicates main.js logic
- Use `alert()` or `confirm()` for user feedback (use toast instead)
- Skip `defer` on script tags
- Forget `loading="lazy"` on below-fold images
- Use `text-midnight/40` for 10px text (fails contrast)
- Create modals without animations or ARIA attributes
- Add new font families without updating tailwind-config.js
