"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  ResizablePanelGroup,
  ResizablePanel,
  ResizableHandle,
} from "@/components/ui/resizable";
import { CodeMirrorEditor } from "@/components/latex/codemirror-editor";
import { PdfPreview } from "@/components/latex/pdf-preview";
import api, { compilePaper } from "@/lib/api";
import { Save, Download, RefreshCw } from "lucide-react";
import { toast } from "sonner";

const DEBOUNCE_MS = 1500;

const DEFAULT_TEX = `\\documentclass{article}
\\title{My Paper}
\\author{Author}
\\date{\\today}

\\begin{document}
\\maketitle

\\section{Introduction}
Write your introduction here.

\\end{document}
`;

const DEFAULT_BIB = `@article{example2024,
  author  = {Doe, Jane},
  title   = {An Example Article},
  journal = {Journal of Examples},
  year    = {2024},
  volume  = {1},
  pages   = {1--10},
}
`;

interface LatexEditorProps {
  paperId: string;
  /** Optional initial content loaded from the server. */
  initialTex?: string;
  initialBib?: string;
}

export function LatexEditor({
  paperId,
  initialTex,
  initialBib,
}: LatexEditorProps) {
  const localStorageTexKey = `paperpilot_latex_draft_tex_${paperId}`;
  const localStorageBibKey = `paperpilot_latex_draft_bib_${paperId}`;

  // -----------------------------------------------------------------
  // State
  // -----------------------------------------------------------------
  const [texContent, setTexContent] = useState<string>(() => {
    if (typeof window === "undefined") return initialTex ?? DEFAULT_TEX;
    return (
      localStorage.getItem(localStorageTexKey) ??
      initialTex ??
      DEFAULT_TEX
    );
  });

  const [bibContent, setBibContent] = useState<string>(() => {
    if (typeof window === "undefined") return initialBib ?? DEFAULT_BIB;
    return (
      localStorage.getItem(localStorageBibKey) ??
      initialBib ??
      DEFAULT_BIB
    );
  });

  const [activeTab, setActiveTab] = useState<"tex" | "bib">("tex");
  const [isCompiling, setIsCompiling] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [pdfB64, setPdfB64] = useState<string | null>(null);
  const [compileErrors, setCompileErrors] = useState<string[]>([]);

  // Debounce timer ref
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // -----------------------------------------------------------------
  // Persist drafts to localStorage on every change
  // -----------------------------------------------------------------
  useEffect(() => {
    if (typeof window !== "undefined") {
      localStorage.setItem(localStorageTexKey, texContent);
    }
  }, [texContent, localStorageTexKey]);

  useEffect(() => {
    if (typeof window !== "undefined") {
      localStorage.setItem(localStorageBibKey, bibContent);
    }
  }, [bibContent, localStorageBibKey]);

  // -----------------------------------------------------------------
  // Compile function
  // -----------------------------------------------------------------
  const compile = useCallback(async () => {
    setIsCompiling(true);
    setCompileErrors([]);
    try {
      const result = await compilePaper(paperId, texContent, bibContent);
      if (result.pdf_base64) {
        setPdfB64(result.pdf_base64);
        setCompileErrors([]);
      } else {
        setCompileErrors(result.errors?.length ? result.errors : ["Compilation failed."]);
      }
    } catch (err) {
      setCompileErrors([
        err instanceof Error ? err.message : "Compilation request failed.",
      ]);
    } finally {
      setIsCompiling(false);
    }
  }, [paperId, texContent, bibContent]);

  // -----------------------------------------------------------------
  // Auto-compile with 1.5s debounce
  // -----------------------------------------------------------------
  const scheduleCompile = useCallback(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      compile();
    }, DEBOUNCE_MS);
  }, [compile]);

  const handleTexChange = useCallback(
    (value: string) => {
      setTexContent(value);
      scheduleCompile();
    },
    [scheduleCompile]
  );

  const handleBibChange = useCallback(
    (value: string) => {
      setBibContent(value);
      scheduleCompile();
    },
    [scheduleCompile]
  );

  // Cleanup debounce on unmount
  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, []);

  // -----------------------------------------------------------------
  // Save handler (persists .tex to the papers API)
  // -----------------------------------------------------------------
  const handleSave = async () => {
    setIsSaving(true);
    try {
      // The existing papers API doesn't yet have a PATCH for tex content,
      // so we trigger a compile (which also validates the source) and
      // notify the user that the draft is saved locally.
      if (typeof window !== "undefined") {
        localStorage.setItem(localStorageTexKey, texContent);
        localStorage.setItem(localStorageBibKey, bibContent);
      }
      toast.success("Draft saved to local storage");
    } finally {
      setIsSaving(false);
    }
  };

  // -----------------------------------------------------------------
  // Download PDF handler
  // -----------------------------------------------------------------
  const handleDownloadPdf = () => {
    if (!pdfB64) {
      toast.error("No compiled PDF available yet.");
      return;
    }
    try {
      const binary = atob(pdfB64);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
      const blob = new Blob([bytes], { type: "application/pdf" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `paper-${paperId}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error("Failed to download PDF.");
    }
  };

  // -----------------------------------------------------------------
  // Render
  // -----------------------------------------------------------------
  return (
    <div className="flex flex-col h-full">
      {/* ── Toolbar ─────────────────────────────────────────── */}
      <div className="flex items-center gap-2 px-3 py-2 border-b bg-card shrink-0">
        <Button
          size="sm"
          variant="outline"
          onClick={handleSave}
          disabled={isSaving}
        >
          <Save className="h-4 w-4 mr-1.5" />
          Save Draft
        </Button>
        <Button
          size="sm"
          variant="outline"
          onClick={() => compile()}
          disabled={isCompiling}
        >
          <RefreshCw
            className={`h-4 w-4 mr-1.5 ${isCompiling ? "animate-spin" : ""}`}
          />
          Compile
        </Button>
        <Button
          size="sm"
          variant="outline"
          onClick={handleDownloadPdf}
          disabled={!pdfB64}
        >
          <Download className="h-4 w-4 mr-1.5" />
          Download PDF
        </Button>
      </div>

      {/* ── Split pane ──────────────────────────────────────── */}
      <div className="flex-1 overflow-hidden">
        <ResizablePanelGroup direction="horizontal">
          {/* Left: editor */}
          <ResizablePanel defaultSize={50} minSize={25}>
            <div className="flex flex-col h-full">
              <Tabs
                value={activeTab}
                onValueChange={(v) => setActiveTab(v as "tex" | "bib")}
                className="flex flex-col h-full"
              >
                <TabsList className="shrink-0 justify-start rounded-none border-b h-9 px-3 bg-muted/40">
                  <TabsTrigger value="tex" className="text-xs">
                    paper.tex
                  </TabsTrigger>
                  <TabsTrigger value="bib" className="text-xs">
                    references.bib
                  </TabsTrigger>
                </TabsList>

                {/* .tex editor */}
                <TabsContent
                  value="tex"
                  className="flex-1 overflow-hidden mt-0 data-[state=inactive]:hidden"
                >
                  <CodeMirrorEditor
                    key="tex-editor"
                    value={texContent}
                    onChange={handleTexChange}
                    language="tex"
                    className="h-full"
                  />
                </TabsContent>

                {/* .bib editor */}
                <TabsContent
                  value="bib"
                  className="flex-1 overflow-hidden mt-0 data-[state=inactive]:hidden"
                >
                  <CodeMirrorEditor
                    key="bib-editor"
                    value={bibContent}
                    onChange={handleBibChange}
                    language="bib"
                    className="h-full"
                  />
                </TabsContent>
              </Tabs>
            </div>
          </ResizablePanel>

          <ResizableHandle withHandle />

          {/* Right: PDF preview */}
          <ResizablePanel defaultSize={50} minSize={25}>
            <PdfPreview
              pdfB64={pdfB64}
              isCompiling={isCompiling}
              errors={compileErrors}
            />
          </ResizablePanel>
        </ResizablePanelGroup>
      </div>
    </div>
  );
}
