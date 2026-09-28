/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
      },
      boxShadow: {
        soft: '0 16px 50px rgba(15, 23, 42, 0.08)',
        'soft-dark': '0 16px 50px rgba(0, 0, 0, 0.35)',
      },
    },
  },
  plugins: [],
}
