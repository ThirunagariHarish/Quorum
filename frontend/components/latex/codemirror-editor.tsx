"use client";

import { useEffect, useRef } from "react";
import { EditorView, basicSetup } from "codemirror";
import { EditorState } from "@codemirror/state";
import { StreamLanguage } from "@codemirror/language";
import { stex } from "@codemirror/legacy-modes/mode/stex";
import { markdown } from "@codemirror/lang-markdown";

interface CodeMirrorEditorProps {
  /** Current document text (controlled). */
  value: string;
  /** Called whenever the document changes. */
  onChange: (value: string) => void;
  /** Selects the syntax highlighter. */
  language?: "tex" | "bib";
  className?: string;
}

/** Light theme overrides applied on top of the default CodeMirror styles. */
const editorTheme = EditorView.theme({
  "&": {
    height: "100%",
    fontSize: "13px",
    fontFamily:
      '"JetBrains Mono", "Fira Code", "Cascadia Code", ui-monospace, monospace',
  },
  ".cm-scroller": { overflow: "auto" },
  ".cm-content": { caretColor: "#0f0f0f" },
  ".cm-focused": { outline: "none" },
  "&.cm-focused .cm-cursor": { borderLeftColor: "#0f0f0f" },
  ".cm-gutters": {
    backgroundColor: "#f8f9fa",
    color: "#6b7280",
    border: "none",
    borderRight: "1px solid #e5e7eb",
  },
  ".cm-activeLineGutter": { backgroundColor: "#eff6ff" },
  ".cm-activeLine": { backgroundColor: "#eff6ff" },
});

/**
 * A thin React wrapper around a CodeMirror 6 EditorView.
 *
 * The editor is *controlled* in the sense that an externally-supplied `value`
 * is always reflected, but we avoid roundtripping every keystroke through
 * React state by only dispatching a replace transaction when the incoming
 * value actually differs from the current editor document.
 */
export function CodeMirrorEditor({
  value,
  onChange,
  language = "tex",
  className,
}: CodeMirrorEditorProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView | null>(null);

  // Keep a stable ref so the listener closure doesn't go stale.
  const onChangeRef = useRef(onChange);
  useEffect(() => {
    onChangeRef.current = onChange;
  });

  // -----------------------------------------------------------------
  // Mount editor once
  // -----------------------------------------------------------------
  useEffect(() => {
    if (!containerRef.current) return;

    const langExtension =
      language === "bib"
        ? markdown() // .bib is close enough to plain text; markdown gives basic code fencing
        : StreamLanguage.define(stex); // proper LaTeX/TeX mode from legacy-modes

    const state = EditorState.create({
      doc: value,
      extensions: [
        basicSetup,
        langExtension,
        editorTheme,
        EditorView.updateListener.of((update) => {
          if (update.docChanged) {
            onChangeRef.current(update.state.doc.toString());
          }
        }),
        EditorView.lineWrapping,
      ],
    });

    const view = new EditorView({ state, parent: containerRef.current });
    viewRef.current = view;

    return () => {
      view.destroy();
      viewRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [language]); // re-init when language changes (tab switch)

  // -----------------------------------------------------------------
  // Sync external value changes into the editor (e.g. initial load,
  // localStorage restore) WITHOUT triggering onChange.
  // -----------------------------------------------------------------
  useEffect(() => {
    const view = viewRef.current;
    if (!view) return;
    const current = view.state.doc.toString();
    if (current !== value) {
      view.dispatch({
        changes: { from: 0, to: current.length, insert: value },
      });
    }
  }, [value]);

  return (
    <div
      ref={containerRef}
      className={className}
      style={{ height: "100%", width: "100%" }}
    />
  );
}
