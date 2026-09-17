const ALLOWED_EXTERNAL_PROTOCOLS = new Set(["https:"]);

/** Return only an absolute HTTPS URL suitable for an external link or image. */
export function safeExternalUrl(value: string | null | undefined): string | null {
  if (!value) return null;
  try {
    const url = new URL(value.trim());
    return ALLOWED_EXTERNAL_PROTOCOLS.has(url.protocol) ? url.toString() : null;
  } catch {
    return null;
  }
}

/** Allow only bounded raster data URLs produced by the PDF image extractor. */
export function safeImageUrl(value: string | null | undefined): string | null {
  if (!value) return null;
  const trimmed = value.trim();
  if (/^data:image\/(?:jpeg|jpg|png|webp);base64,[A-Za-z0-9+/=]+$/i.test(trimmed) && trimmed.length <= 750_000) {
    return trimmed;
  }
  return safeExternalUrl(trimmed);
}
