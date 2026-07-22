/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: {
          DEFAULT: '#080012',
          card: '#120028',
          hover: '#1c0040',
        },
        accent: {
          cyan: '#00fff7',
          pink: '#ff00aa',
          purple: '#a855f7',
          blue: '#38bdf8',
          green: '#4ade80',
          coral: '#fb7185',
          lavender: '#d8b4fe',
          peach: '#fda4af',
        },
      },
    },
  },
  plugins: [],
}
