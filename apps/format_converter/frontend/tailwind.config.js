/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        surface: {
          0: '#0d1017',
          50: '#11141d',
          100: '#161a25',
          200: '#1c2030',
          300: '#23273a',
          400: '#2a3045',
        },
        accent: {
          blue: '#6366f1',
          purple: '#a855f7',
          cyan: '#22d3ee',
          pink: '#ec4899',
          green: '#10b981',
          amber: '#f59e0b',
        },
        text: {
          primary: '#e8ecf2',
          secondary: '#989fb0',
          muted: '#636b7d',
        },
      },
      fontFamily: {
        sans: ['"Inter"', '"SF Pro Display"', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['"JetBrains Mono"', '"Fira Code"', 'monospace'],
      },
      animation: {
        'float': 'float 6s ease-in-out infinite',
        'pulse-glow': 'pulse-glow 2s ease-in-out infinite',
        'slide-up': 'slide-up 0.4s ease-out',
        'fade-in': 'fade-in 0.3s ease-out',
        'spin-slow': 'spin 20s linear infinite',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0px) rotate(0deg)' },
          '33%': { transform: 'translateY(-20px) rotate(1deg)' },
          '66%': { transform: 'translateY(10px) rotate(-1deg)' },
        },
        'pulse-glow': {
          '0%, 100%': { boxShadow: '0 0 20px rgba(99,102,241,0.1)' },
          '50%': { boxShadow: '0 0 40px rgba(99,102,241,0.25)' },
        },
        'slide-up': {
          from: { opacity: '0', transform: 'translateY(20px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        'fade-in': {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}
