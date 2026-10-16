/** @type {import('tailwindcss').Config} */
// Colores semánticos: los valores viven en src/index.css como canales RGB (claro por defecto,
// oscuro bajo `.dark`), de modo que `bg-accent/10` y similares funcionan en ambos temas.
const token = (nombre) => `rgb(var(--${nombre}) / <alpha-value>)`

export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
      },
      colors: {
        bg: token('bg'),
        surface: { DEFAULT: token('surface'), 2: token('surface-2') },
        line: token('line'),
        fg: { DEFAULT: token('fg'), muted: token('fg-muted'), subtle: token('fg-subtle') },
        accent: { DEFAULT: token('accent'), hover: token('accent-hover'), text: token('accent-text') },
        success: { DEFAULT: token('success'), text: token('success-text') },
        warning: { DEFAULT: token('warning'), text: token('warning-text') },
        danger: { DEFAULT: token('danger'), text: token('danger-text') },
      },
    },
  },
  plugins: [],
}
