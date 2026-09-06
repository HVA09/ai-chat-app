import typography from "@tailwindcss/typography";

/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {},
  },
  // typography يفعّل صنوف prose/prose-slate المستخدَمة بـ LegalPageShell.jsx (كانت
  // بدون أي تأثير فعلي لأنها ما كانت مسجّلة هون رغم استخدامها بالكود)
  plugins: [typography],
};
