/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      colors: {
        brand: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          900: '#1e3a8a',
        }
      },
      keyframes: {
        slideInDown: {
          '0%': { transform: 'translate(-50%, -100%)', opacity: 0 },
          '100%': { transform: 'translate(-50%, 0)', opacity: 1 },
        },
        fadeInUp: {
          '0%': { transform: 'translate(-50%, -40%)', opacity: 0 },
          '100%': { transform: 'translate(-50%, -50%)', opacity: 1 },
        }
      },
      animation: {
        'slideInDown': 'slideInDown 0.4s ease-out forwards',
        'fadeInUp': 'fadeInUp 0.4s ease-out forwards',
      }
    },
  },
  plugins: [],
}
