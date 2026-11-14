import { useEffect, useRef } from 'react';
import { reducedMotion } from '../viz';
import { LAYERS, RAMP, frameCodes, globeCells, type Cell } from './globe';

const SECONDS_PER_TURN = 50;
const FRAME_MS = 1000 / 24;
const START_TURN = 0.06; // first frame faces the Atlantic, with the Americas, Europe and Africa in view

/**
 * Decorative rotating globe drawn with text characters, with the EcoDelta wordmark in a band across its middle.
 * Shows land and sea only, no data. Glyphs are drawn once into a sprite sheet, so a frame is only image copies.
 */
export function AsciiGlobe() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wordRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current!;
    const word = wordRef.current!;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    // colors come from the tokens file, read once: ocean, then land from the night side to the lit side
    const css = getComputedStyle(canvas);
    const token = (n: string) => css.getPropertyValue(n).trim();
    const styles: [string, number][] = [
      [token('--blue'), 0.55],
      [token('--teal'), 0.45],
      [token('--teal'), 0.85],
      [token('--green'), 0.95],
      [token('--lime'), 1],
    ];
    const font = css.fontFamily;

    let cells: Cell[] = [];
    let codes = new Int16Array(0);
    let dx = new Float32Array(0);
    let dy = new Float32Array(0);
    const sheet = document.createElement('canvas');
    let sw = 0;
    let sh = 0;
    let turn = START_TURN;
    let raf = 0;
    let last = 0;
    let visible = true;

    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      frameCodes(cells, turn, codes);
      for (let i = 0; i < codes.length; i++) {
        const v = codes[i];
        if (v < 0) continue;
        ctx.drawImage(sheet, (v % RAMP.length) * sw, ((v / RAMP.length) | 0) * sh, sw, sh, dx[i], dy[i], sw, sh);
      }
    };

    const layout = () => {
      const size = canvas.clientWidth;
      if (!size) return;
      const dpr = Math.min(2, window.devicePixelRatio || 1);
      canvas.width = canvas.height = Math.round(size * dpr);
      const fs = Math.max(5.5, Math.min(9, size / 66));
      const cw = fs * 0.62;
      const ch = fs * 1.05;
      const cols = Math.floor(size / cw);
      const rows = Math.floor(size / ch);
      const [ox, oy] = [(size - cols * cw) / 2, (size - rows * ch) / 2];
      // keep the wordmark's box (plus a little air) free of characters
      const c = canvas.getBoundingClientRect();
      const w = word.getBoundingClientRect();
      const hole = { x0: w.left - c.left - ox - 2 * cw, y0: w.top - c.top - oy - ch / 2, x1: w.right - c.left - ox + 2 * cw, y1: w.bottom - c.top - oy + ch / 2 };
      cells = globeCells(cols, rows, cw, ch, size / 2 - 2, hole);
      codes = new Int16Array(cells.length);
      dx = Float32Array.from(cells, (k) => Math.round((ox + k.c * cw) * dpr));
      dy = Float32Array.from(cells, (k) => Math.round((oy + k.r * ch) * dpr));

      // sprite sheet: one row per layer (color), one column per ramp character
      sw = Math.ceil(cw * dpr);
      sh = Math.ceil(ch * dpr);
      sheet.width = sw * RAMP.length;
      sheet.height = sh * LAYERS;
      const s = sheet.getContext('2d')!;
      s.font = `600 ${fs * dpr}px ${font}`;
      s.textAlign = 'center';
      s.textBaseline = 'middle';
      styles.forEach(([color, alpha], l) => {
        s.fillStyle = color;
        s.globalAlpha = alpha;
        [...RAMP].forEach((g, k) => s.fillText(g, k * sw + sw / 2, l * sh + sh / 2));
      });
      draw();
    };

    const still = reducedMotion();
    const tick = (now: number) => {
      raf = requestAnimationFrame(tick);
      const dt = now - last;
      if (dt < FRAME_MS) return;
      last = now - (dt % FRAME_MS); // keep the 24 fps cadence on a 60 Hz screen (draws every 2 or 3 frames)
      turn += Math.min(dt, 100) / 1000 / SECONDS_PER_TURN; // a long pause does not jump the globe ahead
      draw();
    };
    const run = () => {
      cancelAnimationFrame(raf);
      raf = 0;
      if (still || !visible || document.hidden) return;
      last = performance.now();
      raf = requestAnimationFrame(tick);
    };

    const resize = new ResizeObserver(layout);
    resize.observe(canvas);
    const seen = new IntersectionObserver(([e]) => {
      visible = e.isIntersecting;
      run();
    });
    seen.observe(canvas);
    document.addEventListener('visibilitychange', run);
    // lay out again once the font is in: glyph shapes and the wordmark's width depend on it
    document.fonts?.ready.then(layout, () => {});
    layout();
    run();
    return () => {
      cancelAnimationFrame(raf);
      resize.disconnect();
      seen.disconnect();
      document.removeEventListener('visibilitychange', run);
    };
  }, []);

  return (
    <div className="globe-wrap" aria-hidden="true">
      <canvas ref={canvasRef} className="globe" />
      <span ref={wordRef} className="globe__word">
        Eco<b>Delta</b>
      </span>
    </div>
  );
}
