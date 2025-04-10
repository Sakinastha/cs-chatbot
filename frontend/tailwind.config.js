/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
      './src/**/*.{html,js,ts,jsx,tsx}', // Adjust path if you are using TypeScript
    ],
    theme: {
      extend: {
        colors: {
          primary: '#1D4ED8', // Blue primary color
          secondary: '#F1F5F9', // Light gray for background
        },
      },
    },
    plugins: [],
  }
  