/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'DM Sans', 'system-ui', 'sans-serif'],
      },
      colors: {
        // Legacy primary (kept for any remaining usages)
        primary: {
          50: '#f0fdfa',
          100: '#ccfbf1',
          200: '#99f6e4',
          300: '#5eead4',
          400: '#2dd4bf',
          500: '#14b8a6',
          600: '#0d9488',
          700: '#0f766e',
          800: '#115e59',
          900: '#134e4a',
        },
        // Dark design system
        base: '#080C14',
        surface: '#0D1117',
        'surface-2': '#111827',
        'surface-3': '#1a2234',
        accent: {
          DEFAULT: '#0EA5E9',
          hover: '#38BDF8',
          muted: 'rgba(14,165,233,0.15)',
        },
        glass: 'rgba(255,255,255,0.04)',
        'glass-hover': 'rgba(255,255,255,0.08)',
        'border-glass': 'rgba(255,255,255,0.08)',
        'border-glass-hover': 'rgba(255,255,255,0.14)',
      },
      backgroundImage: {
        'grid-pattern': "linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)",
        'accent-gradient': 'linear-gradient(135deg, #0EA5E9 0%, #06B6D4 100%)',
        'orb-glow': 'radial-gradient(circle, rgba(14,165,233,0.25) 0%, rgba(6,182,212,0.1) 40%, transparent 70%)',
      },
      backgroundSize: {
        'grid': '32px 32px',
      },
      boxShadow: {
        'glass': '0 0 0 1px rgba(255,255,255,0.08)',
        'accent-glow': '0 0 20px rgba(14,165,233,0.3)',
        'card': '0 4px 24px rgba(0,0,0,0.4)',
      },
      animation: {
        'fade-in': 'fadeIn 0.2s ease-out',
        'slide-up': 'slideUp 0.25s ease-out',
        'slide-in-left': 'slideInLeft 0.25s ease-out',
        'dot-bounce': 'dotBounce 1.2s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideInLeft: {
          '0%': { opacity: '0', transform: 'translateX(-16px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
        dotBounce: {
          '0%, 80%, 100%': { transform: 'translateY(0)', opacity: '0.4' },
          '40%': { transform: 'translateY(-6px)', opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}
