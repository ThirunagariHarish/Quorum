"use client";

import { useEffect, useState } from "react";
import { Loader2, FileText } from "lucide-react";

interface PdfPreviewProps {
  /** Base64-encoded PDF string (no data-URL prefix). */
  pdfB64: string | null;
  /** True while a compile is in-flight. */
  isCompiling: boolean;
  /** Compile errors to display. */
  errors: string[];
}

/**
 * Renders the compiled PDF inside an <iframe> using an object-URL derived from
 * the base64 payload, and shows an overlay while compilation is running.
 */
export function PdfPreview({ pdfB64, isCompiling, errors }: PdfPreviewProps) {
  const [objectUrl, setObjectUrl] = useState<string | null>(null);

  // Convert base64 → Blob → object URL whenever pdfB64 changes.
  // The cleanup function is the sole owner of URL revocation.
  useEffect(() => {
    if (!pdfB64) {
      setObjectUrl(null);
      return;
    }

    try {
      const binary = atob(pdfB64);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
      const blob = new Blob([bytes], { type: "application/pdf" });
      const url = URL.createObjectURL(blob);
      setObjectUrl(url);
      return () => {
        URL.revokeObjectURL(url); // sole revocation point
      };
    } catch {
      setObjectUrl(null);
    }
  }, [pdfB64]);

  const hasErrors = errors.length > 0;

  return (
    <div className="flex flex-col h-full relative">
      {/* ── PDF frame ─────────────────────────────────────────── */}
      <div className="flex-1 relative overflow-hidden bg-muted/20">
        {objectUrl ? (
          <iframe
            src={objectUrl}
            className="w-full h-full border-0"
            title="PDF Preview"
            sandbox=""
          />
        ) : !isCompiling && !hasErrors ? (
          <div className="flex flex-col items-center justify-center h-full text-muted-foreground gap-3">
            <FileText className="h-12 w-12 opacity-40" />
            <p className="text-sm">
              PDF preview will appear here after compilation
            </p>
          </div>
        ) : null}

        {/* Compiling overlay */}
        {isCompiling && (
          <div className="absolute inset-0 flex items-center justify-center bg-background/70 backdrop-blur-sm z-10">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Compiling…
            </div>
          </div>
        )}
      </div>

      {/* ── Error console ──────────────────────────────────────── */}
      {hasErrors && (
        <div className="border-t border-destructive/30 bg-destructive/5 max-h-40 overflow-y-auto p-3">
          <p className="text-xs font-semibold text-destructive mb-1">
            Compile errors
          </p>
          <ul className="space-y-0.5">
            {errors.map((err, i) => (
              <li key={`${i}-${err}`} className="text-xs text-destructive font-mono">
                {err}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
