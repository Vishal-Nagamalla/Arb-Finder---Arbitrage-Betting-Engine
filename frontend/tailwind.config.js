/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: {
          primary: "#0a0a0f",
          secondary: "#12121a",
          card: "#16161f",
          hover: "#1c1c28",
          border: "#252536",
        },
        accent: {
          green: "#00e87b",
          greenDim: "#00e87b22",
          red: "#ff4757",
          redDim: "#ff475722",
          blue: "#4a9eff",
          blueDim: "#4a9eff22",
          yellow: "#ffbe0b",
          yellowDim: "#ffbe0b22",
        },
        text: {
          primary: "#e8e8ed",
          secondary: "#8888a0",
          muted: "#555570",
        },
      },
      fontFamily: {
        sans: ['"DM Sans"', "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', '"Fira Code"', "monospace"],
      },
    },
  },
  plugins: [],
};
