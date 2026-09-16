#!/usr/bin/env python3
"""Static page generator for montmejat.github.io.

Reads Markdown articles (with YAML front matter) from ``content/`` and renders
them into ``pages/<slug>.html`` using the Jinja2 template in ``templates/``.

Front matter fields (all optional except ``title``):

    title:           Article heading (also used as <h1>).
    slug:            Output filename stem (defaults to the source filename).
    page_title:      <title> tag (defaults to the site name).
    hljs_theme:      highlight.js theme name (default: vs2015).
    code:            Force-include highlight.js even if no code is detected.
    math:            Force-include MathJax even if no math is detected.
    container_style: Inline style applied to the main .container.
    head:            Raw HTML injected at the end of <head> (extra styles/links).
    scripts:         Raw HTML injected before </body> (custom/interactive JS).
    tree:            Metadata for the tech-tree (parent/blurb/code link); not
                     used for article rendering, reserved for tree generation.

Code highlighting and MathJax are auto-enabled when fenced code blocks or math
are present, so most articles need no flags at all.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import frontmatter
import markdown
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = ROOT / "content"
TEMPLATES_DIR = ROOT / "templates"
OUTPUT_DIR = ROOT / "pages"
SITE_NAME = "Aurélien Montmejat"
DEFAULT_HLJS_THEME = "vs2015"

MARKDOWN_EXTENSIONS = [
    "tables",
    "attr_list",
    "sane_lists",
    "md_in_html",
    "pymdownx.arithmatex",
    "pymdownx.highlight",
    "pymdownx.superfences",
]
MARKDOWN_EXTENSION_CONFIGS = {
    "pymdownx.arithmatex": {"generic": True},
    # Emit plain `<pre><code class="language-...">` so highlight.js can colorize
    # client-side (matching the existing pages) instead of server-side Pygments.
    "pymdownx.highlight": {"use_pygments": False},
}


def _display(path: Path) -> str:
    """Show a path relative to the repo root when possible, else as-is."""
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def build_environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(enabled_extensions=()),
        trim_blocks=False,
        lstrip_blocks=False,
        keep_trailing_newline=True,
    )


def render_markdown(text: str) -> str:
    md = markdown.Markdown(
        extensions=MARKDOWN_EXTENSIONS,
        extension_configs=MARKDOWN_EXTENSION_CONFIGS,
        output_format="html5",
    )
    return md.convert(text)


def build_article(source: Path, env: Environment) -> Path:
    post = frontmatter.load(str(source))
    meta = post.metadata
    body_html = render_markdown(post.content)

    has_code = 'class="language-' in body_html
    has_math = "arithmatex" in body_html

    context = {
        "title": meta.get("title", source.stem.replace("-", " ").title()),
        "page_title": meta.get("page_title", SITE_NAME),
        "content": body_html.rstrip("\n"),
        "include_hljs": bool(meta.get("code", has_code)),
        "include_mathjax": bool(meta.get("math", has_math)),
        "hljs_theme": meta.get("hljs_theme", DEFAULT_HLJS_THEME),
        "container_style": meta.get("container_style"),
        "head_extra": meta.get("head"),
        "scripts": meta.get("scripts"),
    }

    template = env.get_template("article.html.j2")
    html = template.render(**context)

    slug = meta.get("slug", source.stem)
    output_path = OUTPUT_DIR / f"{slug}.html"
    output_path.write_text(html, encoding="utf-8")
    return output_path


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Generate article pages from Markdown.")
    parser.add_argument(
        "files",
        nargs="*",
        help="Specific markdown files to build (defaults to every file in content/).",
    )
    args = parser.parse_args(argv)

    if not CONTENT_DIR.exists():
        print(f"No content directory found at {CONTENT_DIR}", file=sys.stderr)
        return 1

    sources = (
        [Path(f).resolve() for f in args.files]
        if args.files
        else sorted(CONTENT_DIR.glob("*.md"))
    )
    if not sources:
        print("No markdown sources to build.", file=sys.stderr)
        return 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    env = build_environment()

    for source in sources:
        if not source.exists():
            print(f"  skip (missing): {source}", file=sys.stderr)
            continue
        output_path = build_article(source, env)
        print(f"  {_display(source)} -> {_display(output_path)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
