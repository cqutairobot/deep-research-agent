/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        space: {
          950: '#080c14',
          900: '#0f172a',
          850: '#131b2e',
          800: '#1e293b',
          700: '#334155',
          600: '#475569',
        },
        brand: {
          50: '#eff6ff',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
        }
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace']
      },
      animation: {
        'pulse-subtle': 'pulse-subtle 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow': 'glow 3s ease-in-out infinite alternate',
      },
      keyframes: {
        'pulse-subtle': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.4' },
        },
        'glow': {
          '0%': { filter: 'drop-shadow(0 0 15px rgba(59, 130, 246, 0.3))' },
          '100%': { filter: 'drop-shadow(0 0 25px rgba(99, 102, 241, 0.6))' }
        }
      }
    },
  },
  plugins: [],
}
