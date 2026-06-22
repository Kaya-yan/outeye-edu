/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eef3f9',
          100: '#d5e0ef',
          200: '#afc1df',
          300: '#829cc9',
          400: '#5b7ab3',
          500: '#3d5f9a',
          600: '#2f4b7d',
          700: '#1e3a5f',
          800: '#172d4a',
          900: '#111f35',
          950: '#0a1320',
        },
        accent: {
          50: '#fffbeb',
          100: '#fef3c7',
          200: '#fde68a',
          300: '#fcd34d',
          400: '#fbbf24',
          500: '#f59e0b',
          600: '#d97706',
          700: '#b45309',
          800: '#92400e',
          900: '#78350f',
          950: '#451a03',
        },
        success: {
          50: '#f0fdf4',
          100: '#dcfce7',
          200: '#bbf7d0',
          300: '#86efac',
          400: '#4ade80',
          500: '#7c9a82',
          600: '#5f8368',
          700: '#4a6b52',
          800: '#3a5441',
          900: '#2d4233',
          950: '#1a2b1f',
        },
        navy: {
          50: '#f0f4f8',
          100: '#d9e2ec',
          200: '#bcccdc',
          300: '#9fb3c8',
          400: '#829ab1',
          500: '#627d98',
          600: '#486581',
          700: '#334e68',
          800: '#243b53',
          900: '#102a43',
        },
      },
      fontFamily: {
        sans: ['system-ui', '-apple-system', 'Segoe UI', 'Microsoft YaHei', 'PingFang SC', 'sans-serif'],
        serif: ['Georgia', 'Noto Serif SC', 'serif'],
        display: ['system-ui', '-apple-system', 'Segoe UI', 'Microsoft YaHei', 'sans-serif'],
      },
      fontSize: {
        '2xs': ['0.625rem', { lineHeight: '0.875rem' }],
      },
      backdropBlur: {
        xs: '2px',
        sm: '8px',
        md: '12px',
        lg: '16px',
        xl: '24px',
        '2xl': '40px',
        '3xl': '64px',
      },
      boxShadow: {
        soft: '0 1px 3px 0 rgba(30, 58, 95, 0.04), 0 1px 2px -1px rgba(30, 58, 95, 0.06)',
        card: '0 2px 8px -2px rgba(30, 58, 95, 0.06), 0 4px 16px -4px rgba(30, 58, 95, 0.08)',
        elevated:
          '0 4px 12px -4px rgba(30, 58, 95, 0.08), 0 12px 32px -8px rgba(30, 58, 95, 0.12)',
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-out forwards',
        'slide-up': 'slideUp 0.4s ease-out forwards',
        'slide-down': 'slideDown 0.3s ease-out forwards',
        'slide-in-right': 'slideInRight 0.4s ease-out forwards',
        'scale-in': 'scaleIn 0.3s ease-out forwards',
        shimmer: 'shimmer 2s infinite linear',
        'pulse-soft': 'pulseSoft 2s infinite ease-in-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(4px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideUp: {
          '0%': { transform: 'translateY(20px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        slideDown: {
          '0%': { transform: 'translateY(-10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        slideInRight: {
          '0%': { transform: 'translateX(20px)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
        scaleIn: {
          '0%': { transform: 'scale(0.95)', opacity: '0' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        pulseSoft: {
          '0%, 100%': { transform: 'scale(1)' },
          '50%': { transform: 'scale(1.02)' },
        },
      },
      animationDelay: {
        100: '100ms',
        200: '200ms',
        300: '300ms',
        400: '400ms',
        500: '500ms',
      },
      transitionDuration: {
        250: '250ms',
        350: '350ms',
      },
      transitionTimingFunction: {
        'bounce-subtle': 'cubic-bezier(0.34, 1.56, 0.64, 1)',
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
    function ({ addUtilities, matchUtilities, theme }) {
      addUtilities({
        '.animation-delay-100': { animationDelay: '100ms' },
        '.animation-delay-200': { animationDelay: '200ms' },
        '.animation-delay-300': { animationDelay: '300ms' },
        '.animation-delay-400': { animationDelay: '400ms' },
        '.animation-delay-500': { animationDelay: '500ms' },
      });
    },
  ],
};
