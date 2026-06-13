import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // PhoneWala Gyan design system — dark, professional, orange accent.
        brand: { orange: "#FF6A00", orangeDim: "#CC5500", hover: "#FF7E22" },
        bg: "#0B0C0E",
        surface: "#131417",
        "surface-2": "#191B20",
        line: "#26282E",
        "line-strong": "#34373F",
        fg: "#F2F3F5",
        "fg-muted": "#9BA1A8",
        "fg-subtle": "#6B7178",
        ok: "#34D399",
        warn: "#FBBF24",
        danger: "#F87171",
        info: "#60A5FA",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      borderRadius: { xl: "0.875rem" },
      boxShadow: {
        card: "0 1px 2px rgba(0,0,0,0.4), 0 1px 3px rgba(0,0,0,0.3)",
        pop: "0 8px 24px rgba(0,0,0,0.5)",
      },
      keyframes: {
        "fade-up": { "0%": { opacity: "0", transform: "translateY(6px)" }, "100%": { opacity: "1", transform: "translateY(0)" } },
        pulsedot: { "0%,100%": { opacity: "1" }, "50%": { opacity: "0.35" } },
      },
      animation: {
        "fade-up": "fade-up 0.3s ease-out both",
        pulsedot: "pulsedot 1.8s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
