"""LaTeX compilation utilities using Tectonic."""

from __future__ import annotations

import logging
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class CompilationResult:
    success: bool
    pdf_bytes: bytes | None = None
    log: str = ""
    errors: list[str] = field(default_factory=list)


class LaTeXCompiler:
    """Compile LaTeX documents to PDF using the Tectonic engine."""

    # Greek letters and common math symbols that are only valid inside math mode
    _BARE_MATH_CMDS = (
        r"alpha", r"beta", r"gamma", r"delta", r"epsilon", r"zeta", r"eta",
        r"theta", r"iota", r"kappa", r"lambda", r"mu", r"nu", r"xi",
        r"pi", r"rho", r"sigma", r"tau", r"upsilon", r"phi", r"chi",
        r"psi", r"omega",
        r"Gamma", r"Delta", r"Theta", r"Lambda", r"Xi", r"Pi", r"Sigma",
        r"Upsilon", r"Phi", r"Psi", r"Omega",
        r"nabla", r"infty", r"partial", r"forall", r"exists",
        r"leq", r"geq", r"neq", r"approx", r"sim", r"propto",
        r"times", r"div", r"pm", r"mp", r"cdot", r"ldots", r"cdots",
        r"sum", r"prod", r"int", r"oint",
        r"hat", r"bar", r"vec", r"tilde", r"dot", r"ddot",
        r"mathbf", r"mathit", r"mathrm", r"mathcal", r"mathbb",
    )

    def __init__(self, tectonic_path: str = "tectonic") -> None:
        self.tectonic_path = tectonic_path

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compile(
        self,
        tex_content: str,
        bib_content: str | None = None,
        figures: dict[str, bytes] | None = None,
    ) -> CompilationResult:
        """Pre-process then compile LaTeX to PDF."""
        with tempfile.TemporaryDirectory(prefix="quorum_") as tmpdir:
            tmppath = Path(tmpdir)

            # Write figure files first so pre_process can check them
            if figures:
                for name, data in figures.items():
                    (tmppath / name).write_bytes(data)

            # Pre-process: fix common issues before compilation
            processed = self.pre_process(tex_content, tmppath)

            tex_path = tmppath / "paper.tex"
            tex_path.write_text(processed, encoding="utf-8")

            if bib_content:
                (tmppath / "references.bib").write_text(bib_content, encoding="utf-8")

            try:
                result = subprocess.run(
                    [self.tectonic_path, "-X", "compile", str(tex_path)],
                    capture_output=True,
                    text=True,
                    cwd=tmpdir,
                    timeout=120,
                )
            except FileNotFoundError:
                return CompilationResult(
                    success=False,
                    log="Tectonic not found. Install with: cargo install tectonic",
                    errors=["tectonic binary not found"],
                )
            except subprocess.TimeoutExpired:
                return CompilationResult(
                    success=False,
                    log="Compilation timed out after 120 seconds",
                    errors=["timeout"],
                )

            log_output = result.stdout + result.stderr
            errors = self.parse_errors(log_output)

            # ── One-shot auto-fix retry ──────────────────────────────
            if result.returncode != 0 and errors:
                fixed_tex = self.attempt_auto_fix(processed, errors)
                if fixed_tex is not None:
                    tex_path.write_text(fixed_tex, encoding="utf-8")
                    try:
                        result = subprocess.run(
                            [self.tectonic_path, "-X", "compile", str(tex_path)],
                            capture_output=True,
                            text=True,
                            cwd=tmpdir,
                            timeout=120,
                        )
                    except subprocess.TimeoutExpired:
                        return CompilationResult(
                            success=False,
                            log="Compilation timed out after 120 seconds (retry)",
                            errors=["timeout"],
                        )
                    log_output = result.stdout + result.stderr
                    errors = self.parse_errors(log_output)

            pdf_path = tex_path.with_suffix(".pdf")
            if result.returncode == 0 and pdf_path.exists():
                return CompilationResult(
                    success=True,
                    pdf_bytes=pdf_path.read_bytes(),
                    log=log_output,
                    errors=errors,
                )

            return CompilationResult(
                success=False,
                log=log_output,
                errors=errors,
            )

    def pre_process(self, tex_content: str, tmpdir: Path | None = None) -> str:
        """Apply safety pre-processing before LaTeX compilation.

        Steps (in order):
          1. Normalize line endings to LF.
          2. Inject missing packages: microtype, float.
          3. Ensure \\balance appears before \\bibliographystyle.
          4. Fix bare figure placement specifiers ([h] → [!htbp]).
          5. Replace \\includegraphics references to missing files with a fbox placeholder.
          6. Wrap obvious bare math commands (Greek letters etc.) in $...$.
        """
        content = tex_content

        # 1. Normalize line endings
        content = content.replace("\r\n", "\n").replace("\r", "\n")

        # 2. Inject missing packages before \begin{document}
        content = self._inject_package_if_missing(content, "microtype")
        content = self._inject_package_if_missing(content, "float")

        # 3. Ensure \balance before \bibliographystyle
        content = self._ensure_balance(content)

        # 4. Fix bare figure placement specifiers
        content = self._fix_figure_placement(content)

        # 5. Replace missing \includegraphics references with placeholder
        if tmpdir is not None:
            content = self._fix_missing_figures(content, tmpdir)

        # 6. Wrap bare math commands outside math mode
        content = self._wrap_bare_math_cmds(content)

        return content

    # ------------------------------------------------------------------
    # Parsing / auto-fix
    # ------------------------------------------------------------------

    @staticmethod
    def parse_errors(log: str) -> list[str]:
        """Extract errors *and* important warnings from a Tectonic/LaTeX log."""
        patterns = [
            re.compile(r"^! (.+)$", re.MULTILINE),
            re.compile(r"^l\.\d+ (.+)$", re.MULTILINE),
            re.compile(r"error: (.+)$", re.MULTILINE),
            re.compile(r"Error: (.+)$", re.MULTILINE),
            # Overfull hbox warnings (text overflow)
            re.compile(r"(Overfull \\hbox[^\n]+)", re.MULTILINE),
            # Float too large
            re.compile(r"(Float too large[^\n]*)", re.MULTILINE),
            # Missing figure file
            re.compile(r"(File `[^']+' not found)", re.MULTILINE),
            re.compile(r"(Cannot find file `[^'\n]+)", re.MULTILINE),
        ]
        errors: list[str] = []
        seen: set[str] = set()
        for pattern in patterns:
            for match in pattern.findall(log):
                msg = match.strip()
                if msg not in seen:
                    seen.add(msg)
                    errors.append(msg)
        return errors

    @staticmethod
    def attempt_auto_fix(tex_content: str, errors: list[str]) -> str | None:
        """Try to auto-fix common LaTeX errors. Returns fixed content or None."""
        fixed = tex_content
        changed = False

        for error in errors:
            # ---- Undefined control sequence ----
            if "Undefined control sequence" in error:
                match = re.search(r"\\(\w+)", error)
                if match:
                    cmd = match.group(1)
                    known_packages = {
                        "textcolor": "xcolor",
                        "includegraphics": "graphicx",
                        "url": "hyperref",
                        "toprule": "booktabs",
                        "midrule": "booktabs",
                        "bottomrule": "booktabs",
                        "FloatBarrier": "placeins",
                        "subfloat": "subfig",
                    }
                    if cmd in known_packages:
                        pkg = known_packages[cmd]
                        use_line = f"\\usepackage{{{pkg}}}"
                        if use_line not in fixed:
                            fixed = fixed.replace(
                                "\\begin{document}",
                                f"{use_line}\n\\begin{{document}}",
                            )
                            changed = True

            # ---- Missing \begin{document} ----
            if "Missing \\begin{document}" in error:
                if "\\begin{document}" not in fixed:
                    preamble_end = fixed.rfind("\\usepackage")
                    if preamble_end != -1:
                        insert_pos = fixed.index("\n", preamble_end) + 1
                        fixed = (
                            fixed[:insert_pos]
                            + "\\begin{document}\n"
                            + fixed[insert_pos:]
                        )
                        changed = True

            # ---- Overfull \hbox (text overflow) ----
            if "Overfull \\hbox" in error:
                # Add \sloppy in the preamble once to allow line breaks
                if "\\sloppy" not in fixed and "\\begin{document}" in fixed:
                    fixed = fixed.replace(
                        "\\begin{document}",
                        "\\sloppy\n\\begin{document}",
                    )
                    changed = True
                # Also inject \emergencystretch as a softer fallback
                if "\\emergencystretch" not in fixed and "\\begin{document}" in fixed:
                    fixed = fixed.replace(
                        "\\begin{document}",
                        "\\setlength{\\emergencystretch}{3em}\n\\begin{document}",
                    )
                    changed = True

        return fixed if changed else None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _inject_package_if_missing(content: str, package: str) -> str:
        """Add \\usepackage{<package>} before \\begin{document} if absent.

        Fix 2a: Only match \\usepackage on non-commented lines (lines where no
        ``%`` character precedes the command on the same line).
        Fix 2b: The insertion anchor also uses the first non-commented
        \\usepackage line so we never inject inside a comment block.
        """
        # Fix 2a — detection: skip lines where % appears before \usepackage
        detect_pattern = (
            r"^(?:[^%\n]*?)\\usepackage\s*(?:\[[^\]]*\])?\s*\{"
            + re.escape(package)
            + r"\}"
        )
        if re.search(detect_pattern, content, re.MULTILINE):
            return content

        # Fix 2b — insertion anchor: find the first non-commented \usepackage
        insert_pattern = re.compile(r"^(?:[^%\n]*?)\\usepackage", re.MULTILINE)
        match = insert_pattern.search(content)
        if match:
            insert_pos = match.start()
            return content[:insert_pos] + f"\\usepackage{{{package}}}\n" + content[insert_pos:]

        # No non-commented \usepackage found — insert before \begin{document}
        doc_start = content.find("\\begin{document}")
        if doc_start != -1:
            return content[:doc_start] + f"\\usepackage{{{package}}}\n" + content[doc_start:]

        # Last resort — append at end
        return content + f"\n\\usepackage{{{package}}}"

    @staticmethod
    def _ensure_balance(content: str) -> str:
        """Guarantee \\balance appears immediately before \\bibliographystyle.

        Three cases:
          1. No \\balance at all → inject before \\bibliographystyle.
          2. \\balance exists AND precedes \\bibliographystyle/\\bibliography → nothing to do.
          3. \\balance exists but is AFTER \\bibliographystyle/\\bibliography (misplaced)
             → strip the stray \\balance and re-inject in the correct position.
        """
        balance_match = re.search(r"\\balance\b", content)
        anchor_match = re.search(r"\\bibliographystyle\b|\\bibliography\b", content)

        if balance_match:
            if anchor_match and balance_match.start() > anchor_match.start():
                # Misplaced — remove the stray \balance (including any trailing newline)
                content = re.sub(r"\\balance\b\n?", "", content)
            else:
                # Correctly placed (or no bib anchor to compare against) — leave as-is
                return content

        # Insert \balance on the line immediately before \bibliographystyle
        return re.sub(
            r"(\\bibliographystyle\b)",
            r"\\balance\n\1",
            content,
        )

    @staticmethod
    def _fix_figure_placement(content: str) -> str:
        r"""Upgrade weak/missing figure placement specifiers.

        - ``\begin{figure}`` (no specifier) → ``\begin{figure}[!htbp]``
        - ``\begin{figure}[h]`` → ``\begin{figure}[!htbp]``
        - ``\begin{figure}[H]`` is left as-is (explicit [H] is intentional).
        """
        # \begin{figure} with no specifier
        content = re.sub(
            r"\\begin\{figure\}(?!\s*\[)",
            r"\\begin{figure}[!htbp]",
            content,
        )
        # \begin{figure}[h] only (the bare 'h' specifier)
        content = re.sub(
            r"\\begin\{figure\}\[h\]",
            r"\\begin{figure}[!htbp]",
            content,
        )
        return content

    @staticmethod
    def _fix_missing_figures(content: str, tmpdir: Path) -> str:
        r"""Replace \\includegraphics refs to absent files with a fbox placeholder."""
        resolved_tmpdir = Path(tmpdir).resolve()

        def _replace(match: re.Match) -> str:  # type: ignore[type-arg]
            opts = match.group(1) or ""
            filename = match.group(2).strip()
            # Check in tmpdir root and common sub-directories
            for search_dir in [resolved_tmpdir, resolved_tmpdir / "figures"]:
                candidate = (search_dir / filename).resolve()
                try:
                    candidate.relative_to(resolved_tmpdir)  # raises ValueError if outside
                    if candidate.exists():
                        return match.group(0)  # file found – keep original
                except ValueError:
                    continue  # path escape attempt — skip silently
            # File missing – substitute a visible placeholder box.
            # BUG-001: use only the basename and strip suspicious chars so that
            # path-traversal strings (../../etc/passwd) are never echoed into
            # the PDF body.
            safe_display = os.path.basename(filename.replace("\\", "/"))
            safe_display = re.sub(r"[^\w\s.\-]", "_", safe_display)[:80]
            return rf"\fbox{{Figure not found: {safe_display}}}"

        return re.sub(
            r"\\includegraphics(\[[^\]]*\])?\{([^}]+)\}",
            _replace,
            content,
        )

    def _wrap_bare_math_cmds(self, content: str) -> str:
        r"""Wrap Greek letters / math commands that appear outside math mode in $...$."""
        # Build a pattern that matches \cmd (with optional braced arg) outside math
        # We operate line-by-line and skip lines that already contain math delimiters
        # or that are inside a math environment.
        lines = content.split("\n")
        result_lines: list[str] = []
        in_math_env = False
        math_env_names = (
            "equation", "equation*", "align", "align*", "gather", "gather*",
            "multline", "multline*", "flalign", "flalign*", "math", "displaymath",
        )

        for line in lines:
            stripped = line.strip()

            # Track math environments
            for env in math_env_names:
                if f"\\begin{{{env}}}" in line:
                    in_math_env = True
                if f"\\end{{{env}}}" in line:
                    in_math_env = False

            # Skip comment lines, lines with existing math delimiters, verbatim, etc.
            if (
                in_math_env
                or stripped.startswith("%")
                or "$" in line
                or "\\[" in line
                or "\\]" in line
                or "\\(" in line
                or "\\)" in line
                or "begin{equation" in line
                or "begin{align" in line
            ):
                result_lines.append(line)
                continue

            # For each bare math command, wrap standalone occurrences in $...$
            for cmd in self._BARE_MATH_CMDS:
                # Match \cmd or \cmd{...} when not already preceded by $ or \
                pattern = (
                    r"(?<![\\$])"      # not preceded by \ or $
                    r"(\\" + cmd + r")"
                    r"(\{[^}]*\})?"    # optional braced argument
                    r"(?![a-zA-Z}])"   # not followed by letters or }
                )
                def _wrap(m: re.Match) -> str:  # type: ignore[type-arg]
                    return f"${m.group(0)}$"

                line = re.sub(pattern, _wrap, line)

            result_lines.append(line)

        return "\n".join(result_lines)
