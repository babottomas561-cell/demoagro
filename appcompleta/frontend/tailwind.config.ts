import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        // Fondo beige/crema cálido
        background: '#f7f3ec',

        // Superficies claras
        surface: {
          DEFAULT: '#fffdf9',
          2: '#f5f1e9',
          3: '#ede6db',
        },

        // Bordes suaves sobre beige
        border: {
          DEFAULT: '#e6dfd3',
          subtle: '#f0ebe4',
          strong: '#d7cfbf',
        },

        // Texto oscuro sobre fondo claro
        text: {
          DEFAULT: '#1b1a17',
          muted: '#6f675b',
          subtle: '#968c7e',
        },

        // Verde para acentos
        primary: {
          DEFAULT: '#30945a',
          50:  '#f2f9f4',
          100: '#e0f3e6',
          200: '#bbe5c9',
          300: '#88cfa3',
          400: '#52b47a',
          500: '#30945a',
          600: '#1f7544',
          700: '#185e36',
          800: '#144d2c',
          900: '#103f25',
          950: '#082516',
        },

        // Acento principal = verde vibrante
        accent: {
          DEFAULT: '#30945a',
          dim: '#1f7544',
        },

        danger: '#cf6e63',
        warning: '#a97b2f',
        info: '#5d7fa5',
      },

      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },

      fontSize: {
        '2xs': ['0.625rem', { lineHeight: '0.875rem' }],
      },

      spacing: {
        sidebar: '224px',
        topbar: '56px',
      },

      borderRadius: {
        DEFAULT: '10px',
        lg: '14px',
        xl: '18px',
      },

      boxShadow: {
        card: '0 0 0 1px rgba(28, 26, 23, 0.03)',
        'card-hover': '0 0 0 1px rgba(28, 26, 23, 0.06)',
        glow: '0 0 0 1px rgba(48,148,90,0.12)',
      },

      animation: {
        'fade-in': 'fadeIn 0.2s ease-in-out',
        'slide-in': 'slideIn 0.2s ease-out',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },

      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideIn: {
          '0%': { transform: 'translateX(-8px)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}

export default config
