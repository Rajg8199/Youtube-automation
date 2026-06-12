import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // PhoneWala Gyan brand: dark theme, orange accent.
        brand: {
          orange: "#FF6A00",
          orangeDim: "#CC5500",
        },
      },
    },
  },
  plugins: [],
};

export default config;
