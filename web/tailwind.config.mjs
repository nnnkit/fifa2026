/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{astro,html,js,jsx,ts,tsx}'],
  darkMode: 'media',
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      colors: {
        ink: {
          DEFAULT: '#0A0A0A',
          50: '#F7F7F7',
          100: '#EDEDED',
          200: '#D9D9D9',
          300: '#B8B8B8',
          400: '#8E8E8E',
          500: '#6B6B6B',
          600: '#4A4A4A',
          700: '#2E2E2E',
          800: '#1A1A1A',
          900: '#0A0A0A',
        },
        accent: {
          DEFAULT: '#2563EB',
          hover: '#1D4ED8',
        },
        status: {
          available: '#16A34A',
          yellow:    '#EAB308',
          doubtful:  '#EA580C',
          injured:   '#DC2626',
          suspended: '#1F2937',
        },
      },
      fontSize: {
        'xxs': ['0.6875rem', { lineHeight: '1rem', letterSpacing: '0.02em' }],
      },
      letterSpacing: {
        tightish: '-0.011em',
      },
      maxWidth: {
        'reading': '68ch',
      },
    },
  },
  plugins: [],
};
