# montmejat.github.io

Personal site, served as static HTML via GitHub Pages.

## Article pages

Note/article pages under `pages/` are generated from Markdown so I don't have to
hand-write the boilerplate (navbar, dark mode, MathJax, syntax highlighting).

```
content/      Markdown sources (one file per article)
templates/    Jinja2 layout (article.html.j2)
tools/        The generator (generate.py) + build helper
pages/        Generated HTML output (committed, served by Pages)
```

### Writing a new article

1. Create `content/<slug>.md` with front matter:

   ```markdown
   ---
   title: My New Article
   ---

   Write Markdown here. Code blocks and math are detected automatically:

   ```python
   print("hello")
   ```

   $$ e = mc^2 $$
   ```

2. Build it:

   ```bash
   tools/build.sh              # build everything
   tools/build.sh content/my-new-article.md   # or just one file
   ```

   The first run creates a local `.venv` and installs the dependencies in
   `tools/requirements.txt`.

3. Commit the `content/*.md` source **and** the generated `pages/*.html`, then push.

### Front matter reference

All fields are optional except `title`.

| Field             | Purpose                                                        |
| ----------------- | -------------------------------------------------------------- |
| `title`           | Article heading and `<h1>`.                                    |
| `slug`            | Output filename stem (defaults to the source filename).        |
| `page_title`      | `<title>` tag (defaults to the site name).                     |
| `hljs_theme`      | highlight.js theme name (default `vs2015`).                    |
| `code`            | Force-include highlight.js even if no code is detected.        |
| `math`            | Force-include MathJax even if no math is detected.             |
| `container_style` | Inline style for the main `.container` (e.g. bottom spacing).  |
| `head`            | Raw HTML injected at the end of `<head>` (extra styles/links). |
| `scripts`         | Raw HTML injected before `</body>` (custom/interactive JS).    |
| `tree`            | Tech-tree metadata (`parent`, `blurb`, `github`). Reserved.    |

Code highlighting and MathJax turn on automatically when fenced code blocks or
math are present, so most articles need no flags at all.

Interactive widgets (e.g. `<canvas>` demos) are just raw HTML in the Markdown
body, with their JavaScript supplied via the `scripts` front matter field.
