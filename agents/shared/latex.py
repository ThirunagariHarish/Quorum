"""LaTeX compilation utilities using Tectonic."""

from __future__ import annotations

import logging
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CompilationResult:
    success: bool
    pdf_bytes: bytes | None = None
    log: str = ""
    errors: list[str] = field(default_factory=list)


class LaTeXCompiler:
    """Compile LaTeX documents to PDF using the Tectonic engine."""

    def __init__(self, tectonic_path: str = "tectonic") -> None:
        self.tectonic_path = tectonic_path

    def compile(
        self,
        tex_content: str,
        bib_content: str | None = None,
        figures: dict[str, bytes] | None = None,
    ) -> CompilationResult:
        with tempfile.TemporaryDirectory(prefix="quorum_") as tmpdir:
            tex_path = Path(tmpdir) / "paper.tex"
            tex_path.write_text(tex_content, encoding="utf-8")

            if bib_content:
                bib_path = Path(tmpdir) / "references.bib"
                bib_path.write_text(bib_content, encoding="utf-8")

            if figures:
                fig_dir = Path(tmpdir) / "figures"
                fig_dir.mkdir(exist_ok=True)
                for name, data in figures.items():
                    (fig_dir / name).write_bytes(data)

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

    @staticmethod
    def parse_errors(log: str) -> list[str]:
        error_patterns = [
            re.compile(r"^! (.+)$", re.MULTILINE),
            re.compile(r"^l\.\d+ (.+)$", re.MULTILINE),
            re.compile(r"error: (.+)$", re.MULTILINE),
            re.compile(r"Error: (.+)$", re.MULTILINE),
        ]
        errors: list[str] = []
        for pattern in error_patterns:
            errors.extend(pattern.findall(log))
        return errors

    @staticmethod
    def attempt_auto_fix(tex_content: str, errors: list[str]) -> str | None:
        """Try to auto-fix common LaTeX errors. Returns fixed content or None."""
        fixed = tex_content
        changed = False

        for error in errors:
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

            if "Missing $ inserted" in error:
                pass  # Too risky to auto-fix math mode issues

            if "Missing \\begin{document}" in error:
                if "\\begin{document}" not in fixed:
                    preamble_end = fixed.rfind("\\usepackage")
                    if preamble_end != -1:
                        insert_pos = fixed.index("\n", preamble_end) + 1
                        fixed = fixed[:insert_pos] + "\\begin{document}\n" + fixed[insert_pos:]
                        changed = True

        return fixed if changed else None
