// Headless fetcher for www.salute.gov.it, which sits behind a JavaScript "site verification"
// challenge that plain HTTP clients cannot pass. A real Chromium session solves it once, then
// every URL is fetched with the session cookies. Invoked by the Python adapter as a subprocess:
//
//   node ministero_fetch.mjs '<json array of urls>'
//
// stdout: JSON object { url: { status, text | file, error } }. Binary responses (PDF) are written
// to a temp file and returned as `file`.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";
import { createWorker } from "tesseract.js";

const PLAYWRIGHT_MODULE = process.env.MINISTERO_PLAYWRIGHT_MODULE || "playwright";
const WARMUP_URL = "https://www.salute.gov.it/new/it/altro/rss/";
const CHROME_CHANNEL = process.env.MINISTERO_CHROME_CHANNEL || "chrome";
const OCR_ENABLED = process.env.MINISTERO_OCR_ENABLED !== "false";
const OCR_DPI = process.env.MINISTERO_OCR_DPI || "300";
const OCR_LANG = process.env.MINISTERO_OCR_LANG || "ita";
const UA =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36";

const urls = JSON.parse(process.argv[2] || "[]");
const out = {};
const { chromium } = await import(PLAYWRIGHT_MODULE);
let ocrWorker = null;

function localOcrLangPath() {
  const configured = process.env.MINISTERO_OCR_LANG_PATH;
  if (configured) return configured;
  return path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../node_modules/@tesseract.js-data/ita/4.0.0");
}

function renderPdf(pdfFile, outputDir) {
  const prefix = path.join(outputDir, "page");
  const candidates = [process.env.PDFTOPPM_PATH, "pdftoppm"].filter(Boolean);
  let lastError = "pdftoppm non disponibile";
  for (const command of candidates) {
    const result = spawnSync(command, ["-png", "-r", OCR_DPI, pdfFile, prefix], {
      encoding: "utf8",
      windowsHide: true,
    });
    if (result.status === 0) {
      return fs.readdirSync(outputDir)
        .filter((name) => name.startsWith("page-") && name.toLowerCase().endsWith(".png"))
        .sort()
        .map((name) => path.join(outputDir, name));
    }
    lastError = result.error?.message || result.stderr || `pdftoppm exit ${result.status}`;
  }
  throw new Error(lastError);
}

async function ocrPdf(pdfFile) {
  const workDir = fs.mkdtempSync(path.join(os.tmpdir(), "ministero-ocr-"));
  try {
    const images = renderPdf(pdfFile, workDir).slice(0, 6);
    if (!images.length) throw new Error("il PDF non contiene pagine renderizzabili");
    if (!ocrWorker) {
      ocrWorker = await createWorker(OCR_LANG, 1, {
        langPath: localOcrLangPath(),
        logger: () => {},
      });
    }
    const pages = [];
    for (const image of images) {
      const result = await ocrWorker.recognize(image);
      pages.push(result.data.text || "");
    }
    return pages.join("\n").trim();
  } finally {
    fs.rmSync(workDir, { recursive: true, force: true });
  }
}
// Use the Chrome installation already present on the workstation. This avoids
// requiring a second browser download while still allowing the official site
// verification JavaScript to run in a real browser context.
const browser = await chromium.launch({ headless: true, channel: CHROME_CHANNEL });
try {
  const ctx = await browser.newContext({ userAgent: UA, locale: "it-IT" });
  const page = await ctx.newPage();
  await page.goto(WARMUP_URL, { waitUntil: "load", timeout: 60000 });
  await page.waitForTimeout(2500); // let the challenge script set its cookies
  // Download pages/PDFs concurrently; OCR itself remains sequential so one
  // Tesseract worker is reused safely and the archive catch-up stays bounded.
  const fetched = await Promise.all(urls.map(async (url) => {
    try {
      const res = await ctx.request.get(url, { timeout: 60000 });
      const type = res.headers()["content-type"] || "";
      if (type.includes("pdf") || url.toLowerCase().includes(".pdf")) {
        const file = path.join(os.tmpdir(), `ministero_${Date.now()}_${Math.random().toString(36).slice(2)}.pdf`);
        fs.writeFileSync(file, await res.body());
        return [url, { status: res.status(), file }];
      } else {
        return [url, { status: res.status(), text: await res.text() }];
      }
    } catch (e) {
      return [url, { status: 0, error: String(e && e.message ? e.message : e) }];
    }
  }));
  for (const [url, result] of fetched) {
    out[url] = result;
    if (OCR_ENABLED && result.file && result.status === 200) {
      try {
        out[url].ocr_text = await ocrPdf(result.file);
      } catch (e) {
        out[url].ocr_error = String(e && e.message ? e.message : e);
      }
    }
  }
} finally {
  if (ocrWorker) await ocrWorker.terminate();
  await browser.close();
}
process.stdout.write(JSON.stringify(out));
