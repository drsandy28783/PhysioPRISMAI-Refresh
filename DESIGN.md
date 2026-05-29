# PhysiologicPRISM Design System

Last updated: 2026-05-29

## Color Palette

### Primary Brand

PhysiologicPRISM uses a **teal/dark teal palette** as the primary brand color, representing clinical professionalism and trust.

```css
/* Primary Brand Colors */
--primary: #1a5f5a          /* Primary teal - buttons, headers, key UI elements */
--primary-light: #4a7c7a    /* Lighter teal - hovers, secondary elements */
--primary-hover: #005f56    /* Darker teal - hover states */
```

**Legacy colors** (kept for backward compatibility, should be migrated to primary palette):
```css
--dark-green: #12594C
--mid-green: #20735B
--shadow-green: #9BBFB5
--mint: #4BA684
```

### Background Colors

```css
--background: #F8F9FA                    /* Main page background */
--background-gradient-start: #f8fffe     /* Gradient start (very subtle teal tint) */
--background-gradient-end: #e6f7f5       /* Gradient end (light teal tint) */
--background-alt: #ecf0f1                /* Alternative background */
--white: #ffffff                         /* Card backgrounds, inputs */
```

Body uses a subtle vertical gradient:
```css
background: linear-gradient(180deg, #f8fffe 0%, #e6f7f5 50%, #F8F9FA 100%);
```

### Text Colors

```css
--text-primary: #333333      /* Body text, headings */
--text-secondary: #666666    /* Supporting text, labels */
--text-tertiary: #999999     /* Placeholders, muted text */
```

**Contrast issue identified:** `--text-tertiary` (#999999) is commonly used for placeholders, which may fail WCAG 4.5:1 contrast on white backgrounds.

### Accent Colors

```css
--accent-ai: #e91e63        /* AI features, Quick Mode */
--accent-blue: #3498db      /* Info states, featured items */
--accent-green: #2ecc71     /* Success, positive actions */
--accent-orange: #e67e22    /* Warnings, attention */
--accent-purple: #9b59b6    /* Premium features */
```

**Gradient accent** (used on homepage CTA, featured plan card):
```css
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
```

⚠️ **Design debt:** This gradient is **not** part of the brand color palette (`#1a5f5a` teal family). Creates inconsistency. Consider replacing with:
```css
background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%);
```

### Semantic Colors

```css
/* Error */
--error: #e74c3c
--error-bg: #fdecea
--error-text: #611a15

/* Success */
--success: #27ae60
--success-bg: #e8f5e9
--success-text: #1b5e20

/* Warning */
--warning: #f39c12
```

## Typography

### Font Families

**Primary:** Segoe UI (Windows), -apple-system (macOS), BlinkMacSystemFont (macOS), sans-serif fallback

```css
font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
```

**No display font.** Single font family keeps the UI functional and readable (appropriate for clinical software).

### Type Scale

```css
--font-xs: 12px
--font-sm: 14px
--font-base: 16px      /* Body text */
--font-lg: 18px
--font-xl: 24px
--font-2xl: 32px
```

Actual implementation (headings):
```css
h1: 32px, weight 700, line-height 1.2
h2: 24px, weight 700, line-height 1.3
h3: 18px, weight 600, line-height 1.4
h4: 16px, weight 600, line-height 1.4
p:  16px, line-height 1.5
```

**Scale ratio:** ~1.33 between h2→h1, ~1.33 between h3→h2, modest. Meets Impeccable's ≥1.25 minimum.

### Line Heights

- **Headings:** 1.2–1.4 (tight, appropriate for short text)
- **Body text:** 1.5 (comfortable reading)
- **Small text:** 1.6 (forms, labels)

### Weights

- **700** (bold): h1, h2, primary buttons
- **600** (semibold): h3, h4, labels, secondary buttons
- **500** (medium): some labels, navbar links
- **400** (normal): body text (default)

## Spacing System

**4px base scale** (mobile-aligned):

```css
--spacing-xs: 4px
--spacing-sm: 8px
--spacing-md: 12px
--spacing-lg: 16px
--spacing-xl: 20px
--spacing-2xl: 24px
--spacing-3xl: 32px
```

Utility classes follow this scale:
```css
.m-1 = 4px, .m-2 = 8px, .m-3 = 12px, .m-4 = 16px, .m-5 = 20px, .m-6 = 24px, .m-8 = 32px
```

## Border Radius

```css
--radius-sm: 8px      /* Inputs, small buttons */
--radius-md: 12px     /* Cards, buttons, containers */
--radius-lg: 16px     /* Large cards */
--radius-full: 9999px /* Pills, badges */
```

**Consistent rounding:** 12px is the default for most UI elements (buttons, cards, modals). Creates a soft, approachable feel without being overly playful.

## Shadows

```css
--shadow-color: rgba(0, 0, 0, 0.1)
--shadow-color-hover: rgba(0, 0, 0, 0.15)
```

Shadow utilities:
```css
.shadow-sm:  0 1px 2px
.shadow:     0 2px 4px     /* Default */
.shadow-md:  0 4px 8px
.shadow-lg:  0 8px 16px
.shadow-xl:  0 12px 24px
```

Hover shadows increase depth by ~1.5x the base shadow.

## Components

### Buttons

**Primary button** (`.button`):
- Background: `var(--primary)` #1a5f5a
- Color: white
- Padding: 16px 20px, height: 50px
- Border-radius: 12px
- Font: 16px, weight 600
- Shadow: 0 2px 4px
- Hover: darker bg (`#005f56`), lift 1px, increase shadow

**Secondary button** (`.button-secondary`):
- Background: `rgba(26, 95, 90, 0.1)` (10% teal tint)
- Color: `var(--primary)` teal
- Border: 1px solid `var(--primary-light)`
- Same size/radius as primary
- Hover: increase tint to 15%, darker border

**Small button** (`.small-button`):
- Same styling as primary, smaller: padding 8px 12px, font 14px

**AI button** (`.ai-button`):
- Background: `rgba(233, 30, 99, 0.1)` (light pink tint)
- Border: 2px solid `var(--primary)` teal
- Border-radius: 25px (pill shape)
- Icon + text layout
- Hover: pink accent border

### Forms

**Inputs** (text, email, password, textarea, select):
- Width: 100%
- Padding: 12px 16px
- Margin: 8px 0
- Border: 1px solid `var(--border)` (#e5e7eb)
- Border-radius: 8px
- Font: 16px (prevents zoom on mobile)
- Background: white
- Focus: teal border, 3px teal shadow ring (0 0 0 3px rgba(26, 95, 90, 0.1))

**Placeholder color:** `var(--text-tertiary)` #999999 ⚠️ May fail contrast

**Textareas:**
- Min-height: 100px
- Resize: none (auto-grow via JS)

### Cards

**`.card` / `.plan-card`:**
- Background: white
- Border-radius: 12px
- Padding: 16px
- Shadow: 0 2px 4px
- Hover: lift 2px, increase shadow

**Featured card** (`.plan-card.featured`):
- Border: 2px solid `var(--accent-blue)`
- Background: gradient (purple-blue) `linear-gradient(135deg, #667eea 0%, #764ba2 100%)`
- Text: white

⚠️ **Design debt:** Featured gradient conflicts with teal brand. Consider teal gradient or solid teal with white text.

**Stat card** (`.stat-card`):
- White bg, 16px padding, 12px radius
- Min-height: 120px
- Number: 28px, weight 700, teal color
- Label: 14px, secondary color
- Icon: 48px, primary-light color

### Data Tables

**`.data-table`:**
- Header: teal background (`var(--primary)`), white text, uppercase labels (14px, letter-spacing 0.5px)
- Rows: white bg, 1px bottom border
- Hover: light gray bg (`var(--background)`), pointer cursor
- Striped variant: even rows #f9fafb

### Navbar

- Background: `var(--primary)` teal
- Padding: 16px 24px
- Logo height: 40px
- Links: white, 16px, weight 500
- Hamburger menu on mobile/tablet (<768px)

### Flash Messages

**`.flash`:**
- Padding: 12px 16px, border-radius 8px
- Left border: 4px solid (semantic color)
- Shadow: 0 2px 4px

Variants:
- **Error:** #fdecea bg, #611a15 text, #e74c3c border
- **Success:** #e8f5e9 bg, #1b5e20 text, #27ae60 border
- **Warning:** #fff3cd bg, #856404 text, #f39c12 border
- **Info:** #d1ecf1 bg, #0c5460 text, #3498db border

### Modals

**AI Modal** (`.ai-modal`):
- Overlay: rgba(0, 0, 0, 0.5), backdrop blur 2px
- Content: white bg, 12px radius, max-width 600px, max-height 80vh
- Header: teal bg, white text, 18px heading
- Body: light gray bg (#F8F9FA), overflow auto
- Footer: white bg, buttons right-aligned
- Animation: slide-in from top (0.3s ease-out)

**Loading spinner** (`.ai-spinner`):
- 40px circle, 4px border
- Border-top: teal (animates)
- Animation: 0.8s spin

## Responsive Breakpoints

Mobile-first approach:

```css
/* Small (phones): up to 576px */
- Single column grids
- Full-width buttons
- Hamburger nav
- 16px container padding

/* Medium (tablets): 577px–768px */
- 2-column grids
- Hamburger nav (still)
- 16px container padding

/* Large (desktops): 769px+ */
- 3-column grids (plans)
- Full navbar
- 24px container padding

/* Extra large: 1200px+ */
- Container max-width 1200px
```

## Animations

**Transitions:**
- Default: `all 0.2s ease`
- Modals: `0.3s ease-out`

**Animations:**
- `spin`: 0.8s linear infinite (loading spinners)
- `modalSlideIn`: 0.3s ease-out (slide from top, fade in)
- `modalFadeIn`: 0.2s ease-out
- `slideIn/slideOut`: draft auto-save toast

**Reduced motion:** ⚠️ Not implemented. No `@media (prefers-reduced-motion)` blocks found.

## Layout Patterns

### Containers

- **`.container`**: max-width 1200px, 24px padding
- **`.container-sm`**: max-width 600px, 24px padding
- **`.container-md`**: max-width 800px, 24px padding
- **`.container-card`**: max-width 600px, white bg, 12px radius, shadow (for forms)

### Grids

- **`.plans-grid`, `.dashboard-grid`, `.card-grid`**: `repeat(auto-fit, minmax(280px, 1fr))`
- **`.grid-2`**: 2 columns (1fr each)
- **`.grid-3`**: 3 columns
- **`.grid-4`**: 4 columns

Mobile: all collapse to 1 column below 576px.

### Form Layouts

- **`.form-grid`**: flex column on mobile, 2-column grid on desktop (`.form-grid.two-column`)
- **`.form-group`**: flex column, label + input stacked
- **`.control-group`**: flex row, input + AI button side-by-side (gap 8px)

## Design Debt & Opportunities

### High Priority

1. **Gradient color inconsistency**
   - Homepage CTA button (index.html:60): `linear-gradient(135deg, #667eea 0%, #764ba2 100%)` (purple-blue)
   - Featured plan card: same gradient
   - **Fix:** Replace with teal gradient or solid teal + white text

2. **Placeholder contrast failure**
   - `--text-tertiary` (#999999) on white backgrounds = 2.85:1 contrast
   - **Requirement:** 4.5:1 for WCAG AA
   - **Fix:** Darken to `#757575` (4.54:1) or `#6e6e6e` (4.77:1)

3. **Missing reduced-motion support**
   - All animations lack `@media (prefers-reduced-motion: reduce)` fallbacks
   - **Fix:** Add instant transitions or crossfades for motion-sensitive users

4. **Inline styles scattered across 99 templates**
   - Hard to maintain, overrides design system
   - **Fix:** Extract common patterns to reusable CSS classes

### Medium Priority

5. **Legacy color variables**
   - `--dark-green`, `--mid-green`, `--shadow-green`, `--mint` should be migrated to `--primary` family
   - **Fix:** Global find-replace, remove legacy vars

6. **Typography line-length**
   - No `max-width` on body text in blog posts or long-form content
   - **Fix:** Cap at 65–75ch (Impeccable guideline)

7. **Focus states on custom components**
   - Some buttons/cards may lack visible focus indicators
   - **Fix:** Audit with keyboard nav, ensure 3px outline on all interactive elements

8. **Motion intentionality**
   - Current motion is functional (hover lifts, modal slides) but not expressive
   - **Opportunity:** Add staggered list reveals, success state celebrations, progress indicators

### Low Priority

9. **Shadow scale simplification**
   - 6 shadow levels (none, sm, md, lg, xl, plus base) may be overkill
   - **Consider:** Collapse to 4 levels (none, sm, base, lg)

10. **Spacing utility duplication**
    - Both custom properties (`--spacing-lg`) and utility classes (`.m-4`) exist
    - **Consider:** Standardize on one approach (utilities preferred for inline use)

## Brand Voice in Visual Design

**Professional, evidence-based, empowering.**

- **Teal palette** = clinical trust, healthcare professionalism (not sterile blue, not consumer green)
- **Soft rounded corners (12px)** = approachable without being playful
- **Subtle gradients** = depth, premium feel (but currently inconsistent)
- **Generous whitespace** = reduce cognitive load during assessments
- **Clear hierarchy** = guide users through complex workflows
- **Functional motion** = feedback, not decoration

**Not:**
- Consumer-friendly bright colors (too informal)
- Sharp edges or flat design (too cold)
- Heavy animations (distracting during clinical work)
- Trendy gradients or glassmorphism (not timeless)

## Next Steps

See PRODUCT.md "Goals for design work" section for planned improvements.

---

*Auto-generated by Impeccable skill based on static/style.css analysis*
