// Prints the halftone dot tile used as --texture-dots in src/styles/tokens.css: a seamless 96px tile,
// a 6px dot grid with clustered dropout, as a CSS data URI. Usage: node scripts/build-dot-texture.mjs
let seed = 7;
const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
const N = 16, P = 6;
// smooth, tile-periodic noise: a few sine waves whose periods divide the tile
const waves = Array.from({ length: 4 }, () => ({ kx: 1 + Math.floor(rnd() * 3), ky: 1 + Math.floor(rnd() * 3), ph: rnd() * 6.28 }));
const noise = (i, j) => waves.reduce((s, w) => s + Math.sin((2 * Math.PI * (w.kx * i + w.ky * j)) / N + w.ph), 0) / waves.length;
let d = '';
for (let j = 0; j < N; j++) for (let i = 0; i < N; i++) if (noise(i, j) + (rnd() - 0.5) * 0.9 > -0.15) d += `M${i * P + 3} ${j * P + 3}h0`;
const svg = `<svg xmlns='http://www.w3.org/2000/svg' width='96' height='96'><path d='${d}' stroke='%233ddc97' stroke-width='2.2' stroke-linecap='round'/></svg>`;
console.log(`url("data:image/svg+xml,${svg}")`);
console.error((d.match(/M/g) || []).length, 'dots of', N * N, '| chars', svg.length);
