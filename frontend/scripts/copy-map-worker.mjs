import { mkdir, copyFile } from 'node:fs/promises';
const target = new URL('../public/maplibre/', import.meta.url);
await mkdir(target, { recursive: true });
for (const file of ['maplibre-gl-worker.mjs', 'maplibre-gl-shared.mjs']) {
  await copyFile(new URL(`../node_modules/maplibre-gl/dist/${file}`, import.meta.url), new URL(file, target));
}
