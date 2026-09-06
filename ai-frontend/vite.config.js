import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["robots.txt"],
      manifest: {
        name: "مساعد الذكاء الاصطناعي",
        short_name: "AI Assistant",
        description: "مساعد ذكاء اصطناعي بالعربية والإنجليزية",
        lang: "ar",
        dir: "rtl",
        theme_color: "#0f172a",
        background_color: "#0f172a",
        display: "standalone",
        start_url: "/",
        icons: [
          { src: "pwa-192x192.png", sizes: "192x192", type: "image/png" },
          { src: "pwa-512x512.png", sizes: "512x512", type: "image/png" },
        ],
      },
      workbox: {
        // ما نخزّن ردود /chat أو /ws — تفاعلية وتحتاج اتصال حي دائمًا.
        // الهدف هنا تحميل أسرع للواجهة الثابتة فقط (JS/CSS)، مو استخدام offline كامل
        navigateFallbackDenylist: [/^\/chat/, /^\/ws/],
      },
    }),
  ],
  server: {
    port: 5173,
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.js",
  },
});
