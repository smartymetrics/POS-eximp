/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './templates/**/*.{html,js}',
    './static/**/*.{html,js}',
  ],
  theme: {
    extend: {
      colors: {
        'brand-gold': '#C47D0A',
        'brand-gold-pale': '#a96008',
        'studio-bg': '#2b2b2b',
        'paper-white': '#ffffff',
      },
    },
  },
  plugins: [],
}
