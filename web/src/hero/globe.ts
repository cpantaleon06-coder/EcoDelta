// Pure math for the decorative ASCII globe in the hero. It draws land and ocean only, never data.
import { LAND_ROWS, MASK_H, MASK_W } from './landMask';

export const RAMP = ' .:-=+*#%@';
export const LAYERS = 5; // 0 = ocean, 1..4 = land from the night side to the lit side
export const TILT = (23.4 * Math.PI) / 180; // Earth's axial tilt, leaning the north pole to the right
const LIGHT = (() => {
  const v = [-0.6, 0.45, 0.66]; // from the upper left, a little in front
  const n = Math.hypot(...v);
  return v.map((x) => x / n);
})();

// the hex rows decoded once into one byte per cell, so a frame is plain array lookups
const LAND = Uint8Array.from({ length: MASK_W * MASK_H }, (_, i) => {
  const [row, col] = [Math.floor(i / MASK_W), i % MASK_W];
  return (parseInt(LAND_ROWS[row][col >> 2], 16) >> (3 - (col & 3))) & 1;
});
export const isLand = (row: number, col: number) => LAND[row * MASK_W + col] === 1;

/** A glyph code: layer * RAMP.length + index in RAMP, or -1 for nothing. */
const code = (layer: number, k: number) => layer * RAMP.length + k;

/** One character position on the disc. Everything except the longitude shift is fixed, so a frame is a lookup. */
export interface Cell {
  c: number; // column in the character grid
  r: number; // row
  maskRow: number;
  maskCol0: number; // mask column (fractional) seen here when the rotation is 0
  land: number; // glyph code when this position shows land
  ocean: number; // glyph code when it shows ocean (-1: leave empty)
}

/** A rectangle in px from the grid's top left corner that the globe leaves empty (room for the wordmark). */
export interface Hole {
  x0: number;
  y0: number;
  x1: number;
  y1: number;
}

/**
 * Characters of a sphere of radius `radius` px on a grid of `cols` x `rows` cells of `cw` x `ch` px.
 * Land takes the dense end of the ramp, ocean sparse dots; both get denser toward the lit side.
 */
export function globeCells(cols: number, rows: number, cw: number, ch: number, radius: number, hole?: Hole): Cell[] {
  const cells: Cell[] = [];
  const [cos, sin] = [Math.cos(TILT), Math.sin(TILT)];
  for (let r = 0; r < rows; r++)
    for (let c = 0; c < cols; c++) {
      const px = (c + 0.5) * cw;
      const py = (r + 0.5) * ch;
      if (hole && px > hole.x0 && px < hole.x1 && py > hole.y0 && py < hole.y1) continue;
      const x = (px - (cols * cw) / 2) / radius;
      const y = -(py - (rows * ch) / 2) / radius;
      const d = x * x + y * y;
      if (d > 1) continue;
      const z = Math.sqrt(1 - d);
      const light = Math.max(0, x * LIGHT[0] + y * LIGHT[1] + z * LIGHT[2]);
      // undo the tilt (a rotation in the screen plane) to get globe coordinates
      const gx = x * cos - y * sin;
      const gy = x * sin + y * cos;
      const lat = (Math.asin(Math.max(-1, Math.min(1, gy))) * 180) / Math.PI;
      const lon = (Math.atan2(gx, z) * 180) / Math.PI;
      const lit = 0.1 + 0.9 * light; // a little ambient light keeps the night side visible
      cells.push({
        c,
        r,
        maskRow: Math.min(MASK_H - 1, Math.floor((90 - lat) / (180 / MASK_H))),
        maskCol0: (lon + 180) / (360 / MASK_W),
        // land: '+' on the night side up to '@' in full light, in four tones
        land: code(1 + Math.min(3, Math.floor(lit * 4)), 5 + Math.round(lit * 4)),
        // ocean: dots on every other column where light falls, ':' near the brightest point, and a thin rim
        ocean: d > 0.94 || (c % 2 === 0 && light > 0.22) ? code(0, light > 0.85 ? 2 : 1) : -1,
      });
    }
  return cells;
}

/**
 * Glyph codes of one frame, in the order of `cells`. `turn` is the rotation in revolutions;
 * land moves west to east (left to right), as seen from space.
 */
export function frameCodes(cells: Cell[], turn: number, out = new Int16Array(cells.length)): Int16Array {
  const shift = turn * MASK_W;
  for (let i = 0; i < cells.length; i++) {
    const k = cells[i];
    const col = (((Math.floor(k.maskCol0 - shift) % MASK_W) + MASK_W) % MASK_W) | 0;
    out[i] = isLand(k.maskRow, col) ? k.land : k.ocean;
  }
  return out;
}
