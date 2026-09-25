import { cp, mkdir } from "node:fs/promises";
import { join } from "node:path";

const dist = new URL("../dist/", import.meta.url);
const routes = ["pricing", "terms", "privacy"];

for (const route of routes) {
  const targetDir = new URL(`./${route}/`, dist);
  await mkdir(targetDir, { recursive: true });
  await cp(new URL("./index.html", dist), join(targetDir.pathname, "index.html"));
}

console.log(`Prepared SPA entry points: ${routes.map((route) => `/${route}`).join(", ")}`);
