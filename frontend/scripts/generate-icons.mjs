import { deflateSync } from "node:zlib";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const root = join(import.meta.dirname, "..", "public");
const navy = [9, 30, 58, 255];
const white = [248, 250, 252, 255];
const cyan = [56, 189, 248, 255];
const amber = [245, 158, 11, 255];

function crc32(buffer) {
  let crc = 0xffffffff;
  for (const byte of buffer) {
    crc ^= byte;
    for (let bit = 0; bit < 8; bit += 1) crc = (crc >>> 1) ^ (0xedb88320 & -(crc & 1));
  }
  return (crc ^ 0xffffffff) >>> 0;
}

function chunk(type, data) {
  const name = Buffer.from(type);
  const body = Buffer.concat([name, data]);
  const out = Buffer.alloc(12 + data.length);
  out.writeUInt32BE(data.length, 0);
  body.copy(out, 4);
  out.writeUInt32BE(crc32(body), data.length + 8);
  return out;
}

function png(width, height, pixels) {
  const rows = [];
  for (let y = 0; y < height; y += 1) rows.push(Buffer.concat([Buffer.from([0]), pixels.subarray(y * width * 4, (y + 1) * width * 4)]));
  const header = Buffer.alloc(13);
  header.writeUInt32BE(width, 0);
  header.writeUInt32BE(height, 4);
  header[8] = 8;
  header[9] = 6;
  return Buffer.concat([
    Buffer.from("89504e470d0a1a0a", "hex"),
    chunk("IHDR", header),
    chunk("IDAT", deflateSync(Buffer.concat(rows), { level: 9 })),
    chunk("IEND", Buffer.alloc(0)),
  ]);
}

function cubic(a, b, c, d, t) {
  const u = 1 - t;
  return u ** 3 * a + 3 * u ** 2 * t * b + 3 * u * t ** 2 * c + t ** 3 * d;
}

function pathSegments(size) {
  const p = (x, y) => [x * size, y * size];
  const outline = [];
  const accent = [];
  const addCubic = (start, c1, c2, end, steps = 18) => {
    let previous = p(...start);
    for (let i = 1; i <= steps; i += 1) {
      const t = i / steps;
      const current = p(cubic(start[0], c1[0], c2[0], end[0], t), cubic(start[1], c1[1], c2[1], end[1], t));
      outline.push([previous, current]);
      previous = current;
    }
  };
  addCubic([0.5, 0.359], [0.422, 0.266], [0.281, 0.297], [0.25, 0.422]);
  addCubic([0.25, 0.422], [0.219, 0.563], [0.344, 0.797], [0.5, 0.797]);
  addCubic([0.5, 0.797], [0.656, 0.797], [0.781, 0.563], [0.75, 0.422]);
  addCubic([0.75, 0.422], [0.719, 0.297], [0.578, 0.266], [0.5, 0.359]);
  outline.push([p(0.5, 0.359), p(0.5, 0.344)], [p(0.5, 0.344), p(0.5, 0.25)]);
  let previous = p(0.563, 0.219);
  for (let i = 1; i <= 12; i += 1) {
    const t = i / 12;
    const current = p(cubic(0.563, 0.625, 0.703, 0.75, t), cubic(0.219, 0.172, 0.172, 0.203, t));
    accent.push([previous, current]);
    previous = current;
  }
  return { outline, accent };
}

function distanceToSegment(px, py, ax, ay, bx, by) {
  const dx = bx - ax;
  const dy = by - ay;
  const length = dx * dx + dy * dy || 1;
  const t = Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / length));
  const x = ax + t * dx;
  const y = ay + t * dy;
  return Math.hypot(px - x, py - y);
}

function drawIcon(size) {
  const pixels = Buffer.alloc(size * size * 4);
  const paths = pathSegments(size);
  const set = (x, y, color) => {
    if (x < 0 || y < 0 || x >= size || y >= size) return;
    const offset = (y * size + x) * 4;
    for (let i = 0; i < 4; i += 1) pixels[offset + i] = color[i];
  };
  const roundedCorner = (x, y, cx, cy, radius) => Math.hypot(x - cx, y - cy) <= radius;
  const stroke = size * 3.5 / 64;

  for (let y = 0; y < size; y += 1) {
    for (let x = 0; x < size; x += 1) {
      const px = x + 0.5;
      const py = y + 0.5;
      const r = size * 0.25;
      const inside = (px >= r && px <= size - r) || (py >= r && py <= size - r)
        || roundedCorner(px, py, r, r, r) || roundedCorner(px, py, size - r, r, r)
        || roundedCorner(px, py, r, size - r, r) || roundedCorner(px, py, size - r, size - r, r);
      if (!inside) continue;
      let color = navy;
      if (paths.outline.some(([a, b]) => distanceToSegment(px, py, ...a, ...b) <= stroke / 2)) color = white;
      if (paths.accent.some(([a, b]) => distanceToSegment(px, py, ...a, ...b) <= stroke / 2)) color = cyan;
      if (distanceToSegment(px, py, size / 2, size * 0.469, size / 2, size * 0.625) <= stroke / 2
        || Math.hypot(px - size / 2, py - size * 0.719) <= size * 2 / 64) color = amber;
      set(x, y, color);
    }
  }
  return png(size, size, pixels);
}

mkdirSync(root, { recursive: true });
const files = new Map([
  ["icon-512.png", drawIcon(512)],
  ["icon-192.png", drawIcon(192)],
  ["apple-touch-icon.png", drawIcon(180)],
  ["favicon-32x32.png", drawIcon(32)],
  ["favicon-16x16.png", drawIcon(16)],
]);
for (const [name, data] of files) writeFileSync(join(root, name), data);

const png32 = files.get("favicon-32x32.png");
const png16 = files.get("favicon-16x16.png");
const icoHeader = Buffer.alloc(6);
icoHeader.writeUInt16LE(0, 0);
icoHeader.writeUInt16LE(1, 2);
icoHeader.writeUInt16LE(2, 4);
const entry = (size, data, offset) => {
  const item = Buffer.alloc(16);
  item[0] = size;
  item[1] = size;
  item[4] = 1;
  item[6] = 32;
  item.writeUInt32LE(data.length, 8);
  item.writeUInt32LE(offset, 12);
  return item;
};
const icoEntries = Buffer.concat([entry(16, png16, 6 + 32), entry(32, png32, 6 + 32 + png16.length)]);
writeFileSync(join(root, "favicon.ico"), Buffer.concat([icoHeader, icoEntries, png16, png32]));
