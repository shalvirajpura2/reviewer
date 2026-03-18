import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "rgb(var(--background) / <alpha-value>)",
        surface: "rgb(var(--surface) / <alpha-value>)",
        surface2: "rgb(var(--surface2) / <alpha-value>)",
        border: "rgb(var(--border) / <alpha-value>)",
        border2: "rgb(var(--border2) / <alpha-value>)",
        text_primary: "rgb(var(--text) / <alpha-value>)",
        text_secondary: "rgb(var(--text2) / <alpha-value>)",
        text_tertiary: "rgb(var(--text3) / <alpha-value>)",
        accent: "rgb(var(--accent) / <alpha-value>)",
        success: "rgb(var(--green) / <alpha-value>)",
        warning: "rgb(var(--amber) / <alpha-value>)",
        danger: "rgb(var(--red) / <alpha-value>)"
      },
      fontFamily: {
        sans: ["Instrument Sans", "sans-serif"],
        mono: ["Geist Mono", "monospace"],
        display: ["Syne", "sans-serif"]
      },
      boxShadow: {
        panel: "0 0 0 1px rgba(255,255,255,0.02)"
      }
    }
  },
  plugins: []
};

export default config;
