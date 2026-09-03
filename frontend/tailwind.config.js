/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ssb: {
          dark: "#0f172a",
          card: "#1e293b",
          border: "#334155",
          accent: "#2563eb",
          hover: "#1d4ed8"
        }
      }
    },
  },
  plugins: [],
}
