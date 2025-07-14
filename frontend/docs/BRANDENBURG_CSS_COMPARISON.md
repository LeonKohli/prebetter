# Brandenburg Design Guidelines vs Prebetter CSS Implementation

## Side-by-Side CSS Comparison

### 1. Color System

#### Brandenburg Requirements:
```css
:root {
  /* Grundfarbe (Primary) */
  --grundfarbe: #C13B33;
  --blasse-grundfarbe: rgba(193, 59, 51, 0.x); /* < 100% opacity */
  
  /* Standardfarben */
  --dunkelgrau: #333333; /* Text color */
  --hellgrau: #CCCCCC;   /* Borders and lines */
  --lichtgrau: #F5F5F5;  /* Page background */
  --weiss: #FFFFFF;      /* Content background */
}
```

#### Prebetter Implementation:
```css
:root {
  /* Using OKLCH color space */
  --primary: oklch(0.5481 0.1720 27.6751); /* Orange ~#E97500 */
  --foreground: oklch(0.2002 0 0);         /* Dark gray */
  --border: oklch(0.9491 0 0);             /* Light gray */
  --background: oklch(1.0000 0 0);         /* Pure white */
}
```

### 2. Typography Scale

#### Brandenburg Requirements:
```css
/* Based on 16px standard at desktop */
h1 { font-size: 2.0rem; }     /* 32px */
h2 { font-size: 1.688rem; }   /* 27px */
h3 { font-size: 1.375rem; }   /* 22px */
h4 { 
  font-size: 1.0rem;          /* 16px */
  font-weight: bold;
  font-style: italic;
}
h5 { 
  font-size: 1.0rem;          /* 16px */
  font-weight: bold;
}
h6 { 
  font-size: 1.0rem;          /* 16px */
  font-style: italic;
}

body {
  font-family: 'OpenSans', 'Helvetica', 'Arial', sans-serif;
  font-size: 16px;
  line-height: 1.69;
  font-weight: 400;
}
```

#### Prebetter Implementation:
```css
:root {
  --font-sans: Open Sans, sans-serif;
  --font-serif: Source Serif Pro, serif;
  --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 
               "Liberation Mono", "Courier New", monospace;
}

/* No explicit heading hierarchy defined */
/* Using Tailwind utilities like text-sm, text-base, etc. */
```

### 3. Layout & Spacing

#### Brandenburg Requirements:
```css
/* Fixed container width */
.container {
  max-width: 1140px;
  margin: 0 auto;
}

/* 12-column grid with 15px gutters */
.grid {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: 15px;
}

/* Schutzabstand (protective spacing) */
.content {
  padding-left: 30px;  /* 2 × 15px */
  padding-right: 30px;
}

/* Page border */
.page-wrapper {
  border-left: 1px solid #CCCCCC;
  border-right: 1px solid #CCCCCC;
}

/* Standard height unit */
.header-bar {
  height: 30px; /* Standardhöhe */
}
```

#### Prebetter Implementation:
```css
:root {
  --spacing: 0.25rem; /* 4px base unit */
  --radius: 0.5rem;   /* 8px border radius */
}

/* No fixed container width */
/* Using Tailwind's responsive utilities */
/* Spacing based on 4px increments (Tailwind's default) */

/* Example spacing in components: */
.button {
  padding: 0.5rem 1rem; /* 8px 16px */
}
```

### 4. Component Examples

#### Brandenburg Button:
```css
.button {
  background-color: #C13B33;
  color: #FFFFFF;
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  font-family: 'OpenSans', sans-serif;
  font-size: 16px;
  cursor: pointer;
}

.button:hover {
  background-color: rgba(193, 59, 51, 0.9);
}
```

#### Prebetter Button (from component):
```css
/* Using Tailwind classes */
.button-primary {
  @apply inline-flex items-center justify-center gap-2 
         rounded-md text-sm font-medium 
         transition-[color,background-color,border-color,box-shadow] 
         focus-visible:outline-none focus-visible:ring-[3px] 
         disabled:pointer-events-none disabled:opacity-50 
         border border-input 
         bg-primary text-primary-foreground 
         shadow-xs hover:bg-primary/90 
         focus-visible:ring-ring/50 
         focus-visible:ring-offset-background 
         focus-visible:border-ring;
}
```

### 5. Responsive Breakpoints

#### Brandenburg Requirements:
```css
/* Mobile (Smartphones) */
@media (max-width: 760px) {
  /* Linear/stacked layout */
}

/* Tablet */
@media (min-width: 761px) and (max-width: 980px) {
  /* Tablet layout */
}

/* Desktop */
@media (min-width: 981px) and (max-width: 1280px) {
  /* Desktop layout */
}

/* Fixed width above 1280px */
@media (min-width: 1281px) {
  .container {
    width: 1140px;
  }
}
```

#### Prebetter Implementation (Tailwind defaults):
```css
/* Tailwind breakpoints */
/* sm: 640px */
/* md: 768px */
/* lg: 1024px */
/* xl: 1280px */
/* 2xl: 1536px */

/* Usage example: */
/* <div class="px-4 md:px-6 lg:px-8"> */
```

### 6. Dark Mode

#### Brandenburg Requirements:
```css
/* No dark mode specified in guidelines */
```

#### Prebetter Implementation:
```css
.dark {
  --background: oklch(0.1822 0 0);
  --foreground: oklch(0.9310 0 0);
  --primary: oklch(0.6271 0.1919 27.4078);
  /* ... full dark theme implementation */
}
```

## Key Differences Summary

| Aspect | Brandenburg | Prebetter |
|--------|------------|-----------|
| **Color Format** | HEX (#C13B33) | OKLCH color space |
| **Primary Color** | Red | Orange |
| **Spacing Unit** | 15px | 4px (0.25rem) |
| **Grid System** | 12-column, 15px gaps | Tailwind utilities |
| **Container** | Fixed 1140px | Fluid/responsive |
| **Dark Mode** | Not specified | Fully implemented |
| **Component Style** | Traditional CSS | Utility-first (Tailwind) |
| **Typography Scale** | Explicit rem values | Tailwind size classes |

## Migration Path to Brandenburg Compliance

To align with Brandenburg guidelines, the following CSS changes would be needed:

```css
/* 1. Replace color system */
:root {
  --primary: #C13B33;
  --primary-foreground: #FFFFFF;
  --background: #F5F5F5;
  --foreground: #333333;
  --card: #FFFFFF;
  --border: #CCCCCC;
}

/* 2. Implement typography scale */
h1 { @apply text-[2rem] leading-[1.2]; }
h2 { @apply text-[1.688rem] leading-[1.2]; }
h3 { @apply text-[1.375rem] leading-[1.3]; }
h4 { @apply text-base font-bold italic; }
h5 { @apply text-base font-bold; }
h6 { @apply text-base italic; }

/* 3. Add container constraints */
.brandenburg-container {
  @apply mx-auto;
  max-width: 1140px;
  border-left: 1px solid var(--border);
  border-right: 1px solid var(--border);
}

/* 4. Adjust spacing to 15px base */
.brandenburg-spacing {
  --spacing-unit: 15px;
  padding-left: calc(var(--spacing-unit) * 2);
  padding-right: calc(var(--spacing-unit) * 2);
}
```

Note: Full compliance would require significant structural changes beyond just CSS modifications.