# LSP-dita design

Date: 2026-09-25
Status: approved, ready for implementation planning

## Purpose

`LSP-dita` is a Sublime Text helper package that connects Sublime's
[LSP](https://packagecontrol.io/packages/LSP) package to the
[dita-language-server](https://github.com/aireilly/dita-language-server), a
Java LSP implementation for the DITA XML markup language.

The package follows the shape of the existing `LSP-mdita` package and targets a
single outcome: opening a `.dita` or `.ditamap` file in Sublime gives you
diagnostics, completion, ctrl+click navigation to referenced source files, hover
popups on references, prettyprinting on save, and a DITA-OT build you can
trigger without leaving the editor.

The primary user is the package author, working on Red Hat modular
documentation converted to DITA. Success means the editor is usable for daily
DITA authoring without dropping to a terminal for builds or to Oxygen for
formatting.

## What the language server provides

Established by reading `~/dita-language-server` at commit `fcc145a`.

| Capability | Present | Notes |
|---|---|---|
| Diagnostics | yes | Schematron, duplicate topic and element IDs, keyref and conkeyref resolution, cross-reference targets, profiling attribute values |
| Completion | yes | Topic and element IDs for `href`, keys for `keyref` and `conkeyref`, profiling values from the subject scheme |
| Go to definition | yes | `keyref` and `conkeyref` only |
| Hover | yes | `keyref` and `conkeyref` only |
| Code actions | yes | |
| `workspace/executeCommand` | yes | `dita.setRootMap` only |
| `dita/preview` custom request | yes | Returns rendered HTML |
| Document formatting | **no** | |
| DITA-OT build | **no** | |
| Document symbols, rename, references, code lens | **no** | |

Text document sync is `Full`. The main class is
`com.elovirta.dita.DitaLanguageServer`, launched as `java -jar`. Release
`v0.1.0` publishes `dita-language-server-0.1.0-all.jar` (11.5 MB) as a GitHub
release asset.

Two of the four requested features therefore have no server support, and
navigation and hover cover only half the reference kinds a DITA author uses.

## Decisions

These were settled during design and are not open questions.

1. **Prettyprint delegates to LSP-lemminx.** The DITA server has no formatting
   provider. Lemminx is already installed, its formatting is XML-aware, and it
   respects mixed content so it will not reflow text inside `<p>`. Shelling out
   to `xmllint --format` was rejected because it reflows mixed content and can
   change rendered output. Adding a formatter to the Java server was rejected
   as out of scope for this repository.
2. **`href` and `conref` navigation and hover are resolved client side** in
   Python, as an independent Sublime layer. Augmenting server responses through
   LSP internals was rejected: `ServerResponse` carries no request params, so
   position bookkeeping would be required, and the LSP plugin API has already
   changed shape once between `AbstractPlugin` and `LspPlugin`.
3. **The jar is downloaded from GitHub releases** by
   `AbstractPlugin.install_or_update`, with a settings override for local
   development.
4. **The DITA-OT build builds the root map**, runs asynchronously with output
   streamed to a panel, parses DITA-OT diagnostics into clickable results, and
   opens the output on success.
5. **In scope for the first version:** root map picker, DITA syntax definition,
   snippets.
6. **Out of scope for the first version:** the `dita/preview` panel. The server
   supports it and it is a good candidate for a later version.

## Architecture

The package uses the `boot.py` plus `plugin/` subpackage layout, as used by
`LSP-pyright`. Relative imports work under Sublime despite the hyphen in the
package directory name. Four distinct jobs get four modules rather than one
growing `plugin.py`.

```
LSP-dita/
  boot.py                  registers the plugin, re-exports commands
  plugin/
    __init__.py
    constants.py           package name, server version, jar URL and digest
    client.py              DitaLsp(AbstractPlugin): jar install, launch
    refs.py                parse and resolve href/conref under a point
    goto.py                LspDitaGotoCommand
    hover.py               DitaHoverListener
    build.py               LspDitaBuildCommand, output panel, error parsing
    rootmap.py             LspDitaSetRootMapCommand, quick panel
  tests/                   plain unittest, no Sublime required
  DITA.sublime-syntax
  DITA.sublime-settings    syntax-scoped lsp_format_on_save
  Default.sublime-keymap
  Default.sublime-mousemap
  LSP-dita.sublime-settings
  LSP-dita.sublime-commands
  Main.sublime-menu
  sublime-package.json
  snippets/*.sublime-snippet
  messages/install.txt
  messages.json
  README.md
  LICENSE.md
  pyproject.toml
  .github/workflows/ci.yaml
```

### Component boundaries

`refs.py` is the only module with reference parsing knowledge. `goto.py` and
`hover.py` both consume it and neither duplicates its logic. `build.py` and
`rootmap.py` share the root map lookup through a single function in
`rootmap.py`, so the build and the picker can never disagree about which map is
current. `client.py` owns everything about the server process and nothing else.

Each module splits pure logic from Sublime API calls, because the Sublime API
cannot be imported outside Sublime and the pure parts are where defects
concentrate.

## Component design

### 1. Server lifecycle: `client.py`, `constants.py`

`DitaLsp(AbstractPlugin)` with `name()` returning `"dita"`.

`constants.py` pins `SERVER_VERSION = "0.1.0"` and derives the release asset URL
from it, alongside the published sha256
(`e865acc51053b4158a4d7b200e97756433cb0477855f4476082489175f9d078c`). A server
version bump is a one-line change.

`needs_update_or_installation()` returns `True` when the jar is absent from
`<Package Storage>/LSP-dita/` or when a `VERSION` marker file beside it
disagrees with the pin.

`install_or_update()` downloads with `urllib.request`, verifies the sha256
before moving the file into place, then writes the marker. The method runs
blocking, as the LSP API requires, with no use of `threading`.

`can_start()` runs `java -version`, parses the major version, and returns an
error string naming the detected version when it is below 17 or when `java` is
absent. Without this check the failure surfaces as an opaque stack trace.

`additional_variables()` exposes `${java_bin}` and `${server_jar}`.

### 2. Syntax and server attachment: `DITA.sublime-syntax`

Scope `text.xml.dita`, file extensions `dita`, `ditamap`, `ditaval`, and a
`first_line_match` on `-//OASIS//DTD DITA`.

The `first_line_match` is a weak signal for `.xml` files, because the built-in
XML package already claims that extension and an explicit extension claim wins
over a first line match. A `.xml` file holding a DITA topic therefore needs its
syntax set manually. Claiming `.xml` outright is rejected: it would pull every
XML file in every project into the DITA server.

Sublime scope selectors match on dotted prefixes, so LSP-lemminx's existing
`text.xml` selector matches `text.xml.dita` with no configuration change. Both
servers attach to DITA files. The DITA server supplies semantics, lemminx
supplies formatting and DTD-driven element completion.

Implementation tries `extends: Packages/XML/XML.sublime-syntax` first. If the
extended syntax does not re-scope cleanly to `text.xml.dita`, the fallback is a
minimal syntax whose main context is `- include: scope:text.xml`.

### 3. Ctrl+S prettyprint

No Python code. The package ships `DITA.sublime-settings` containing
`{"lsp_format_on_save": true}`. Sublime merges syntax-specific settings from any
package, so format-on-save enables for DITA files only and leaves other syntaxes
untouched.

Ctrl+S then routes `textDocument/formatting` to lemminx, the only attached
server advertising that capability. The default Ctrl+S binding is not
overridden.

### 4. Reference resolution: `refs.py`

Pure core, Sublime adapter on top.

The pure function takes document text and a character offset and returns a
`Reference` dataclass or `None`. Fields: `raw`, `path`, `topic_id`,
`element_id`, `attribute`.

Recognised attributes: `href`, `conref`, `conrefend`, and `copy-to`. These are
the DITA attributes whose value is a resolvable address. `conaction` is
excluded because it carries a push directive rather than a target, and
`data-href` is excluded because it belongs to Markdown DITA rather than XML
DITA.

Parsing handles the DITA addressing form `path#topicid/elementid`. An empty path
with a fragment addresses the current file.

The function declines and returns `None` when the element carries
`scope="external"` or `format="html"`, or when the value has a URI scheme such
as `http://` or `mailto:`.

The Sublime adapter locates the attribute value with `view.extract_scope(point)`
against the `string.quoted.double` scope, then walks backwards for the attribute
name. This is sturdier than regexing a long line.

Fragment location in the target file finds the element carrying
`id="<topic_id>"`, then searches forward within that topic's extent for
`id="<element_id>"`.

Title and shortdesc extraction for hover uses targeted regex, not
`xml.etree.ElementTree`. DITA files reference external DTDs and `ElementTree`
raises on undefined entities such as `&nbsp;`.

Extraction results cache on `(path, mtime)`.

### 5. Navigation: `goto.py`

`LspDitaGotoCommand` resolves the reference under the first cursor.

A resolved reference opens the target with `sublime.ENCODED_POSITION`.
`side_by_side` opens it in the adjacent group.

No resolved reference delegates to `lsp_symbol_definition` with the same
`side_by_side` argument, so `keyref` and `conkeyref` continue through the
server.

A resolved reference whose file does not exist writes a status bar message
naming the missing path. Creating the missing file is deliberately not offered
in this version.

`is_enabled()` restricts the command to `text.xml.dita`.

Bound to Ctrl+Click, Ctrl+Shift+Click, and F12.

### 6. Hover: `hover.py`

`DitaHoverListener.on_hover` fires only for `HOVER_TEXT`, inside
`text.xml.dita`, and when `hover_file_references` is enabled.

File reads run on a worker thread through `sublime.set_timeout_async`, and the
popup shows on the main thread, so disk latency never stalls typing.

The popup shows the target filename as a clickable link that opens the file, the
topic title, and the shortdesc. A missing target renders in a warning style.

Positions the server already handles return `None` from `refs.py`, so the two
hover sources do not produce competing popups.

Popup CSS reuses LSP's popup variables so server hovers and file-reference
hovers look consistent.

### 7. DITA-OT build: `build.py`

Input map resolution order: the root map set by the picker, then the nearest
`.ditamap` found walking up from the active file, then the picker opens rather
than the command erroring.

Executable resolution order: the `dita_ot_path` setting, then
`shutil.which("dita")`. Neither found produces an error naming the setting to
configure.

The build runs
`[dita, "-i", map, "-f", transtype, "-o", output] + dita_ot_args` under
`subprocess.Popen` on a worker thread, with stdout and stderr merged and
streamed line by line into `window.create_output_panel("LSP-dita Build")`. A
relative `dita_ot_output` resolves against the map's directory.

The panel sets `result_file_regex` and `result_base_dir`, which makes DITA-OT
diagnostics clickable. DITA-OT emits several line shapes, including
`[DOTJ049E][ERROR] file:/path/topic.dita:14:5: message` and bare Ant-style
`path:line: message`. The regex is a pure function with unit tests against
captured real DITA-OT output.

One build per window at a time. A second invocation reports the running build in
the status bar. `LspDitaCancelBuildCommand` terminates the running build.

On exit code 0 with `dita_ot_open_output` enabled, `index.html` opens in a
browser when it exists, otherwise the output directory opens.

The status bar shows build progress while the process runs.

### 8. Root map: `rootmap.py`

Scans project folders for `*.ditamap`, excluding `out`, `temp`, `build`, and
`.git`, with a file-count cap so a large repository cannot hang the UI.

Selection dispatches through LSP's public `lsp_execute` command with
`session_name: "dita"` and `command_name: "dita.setRootMap"`, rather than
reaching into session internals.

The choice persists in window settings and re-sends on session initialization,
so a server restart does not silently drop the key space. This matters because
keyref completion, keyref hover, and profiling validation stay inert until a
root map is set.

### 9. Settings

All settings live in `LSP-dita.sublime-settings`, with `.sublime-project`
overrides merged on top for per-project values. `sublime-package.json`
documents every key for editor autocompletion.

```json
{
    "command": ["${java_bin}", "-jar", "${server_jar}"],
    "selector": "text.xml.dita",
    "auto_complete_selector": "text.xml.dita",
    "dita_ot_path": "",
    "dita_ot_transtype": "html5",
    "dita_ot_output": "out",
    "dita_ot_args": [],
    "dita_ot_open_output": true,
    "dita_root_map": "",
    "hover_file_references": true
}
```

### 10. Keymap and mousemap

All bindings scope to `text.xml.dita` and, where applicable, require the
corresponding LSP server capability.

| Binding | Command |
|---|---|
| Ctrl+Click | `lsp_dita_goto` |
| Ctrl+Shift+Click | `lsp_dita_goto` with `side_by_side: true` |
| F12 | `lsp_dita_goto` |
| Ctrl+Shift+A | `lsp_code_actions` |
| Ctrl+Shift+H | `lsp_hover` |
| Ctrl+Shift+B | `lsp_dita_build` |

Ctrl+S is not bound. Prettyprint arrives through `lsp_format_on_save`.

Ctrl+Shift+B overrides Sublime's default "Build With" binding. The override is
scoped to `text.xml.dita`, so it applies only inside DITA files, and running
DITA-OT there is what "build" means anyway. This is a deliberate override and
the README documents it.

### 11. Snippets and completions

Snippets cover concept, task, reference, and glossentry topic skeletons, plus
`xref`, `keyref`, `conref`, `conkeyref`, `keydef`, `note`, `codeblock`, `table`,
`mapref`, and `topicref`.

The completions file stays small and targeted. Element and attribute name
completion already arrives from lemminx's DTD awareness, and attribute value
completion arrives from the DITA server, so a large static completions file
would duplicate both.

## Testing

The Sublime API cannot be imported outside Sublime. The design pushes logic into
pure functions and keeps Sublime-facing shells thin, so the substance is
testable under plain `unittest` in CI with no editor involved.

Unit tested, under TDD:

- Reference parsing from text and offset, across every recognised attribute
- Declining `scope="external"`, `format="html"`, and URI schemes
- DITA fragment address parsing, including the empty-path same-file form
- Fragment location within a target file, including duplicate element IDs
  across different topics in one file
- Title and shortdesc extraction, including files with entity references and
  malformed markup
- Build argv construction, including relative and absolute output paths
- The DITA-OT error regex against captured real output
- Root map discovery, including the exclusion list and the file-count cap
- Java version parsing from `java -version` output

Manual verification, documented as a checklist in the repository, because these
need a running editor:

- Both servers attach to a `.dita` file and the LSP log shows two sessions
- Ctrl+S reformats through lemminx without reflowing mixed content
- Ctrl+Click on an `href` opens the target at the right element
- Ctrl+Click on a `keyref` still reaches the server definition
- Hover over an `href` shows title and shortdesc
- The root map picker sets the map and keyref completion starts working
- A DITA-OT build streams output and its errors are clickable

CI runs `ruff` and `mypy` alongside the unit tests, matching the `LSP-mdita`
configuration.

## Failure modes

| Condition | Behaviour |
|---|---|
| `java` absent | `can_start` returns a message pointing at the install docs |
| Java below 17 | Same path, naming the detected version |
| Jar download fails | `install_or_update` raises, LSP surfaces it, README documents manual jar placement |
| Jar sha256 mismatch | Download discarded, error names the expected digest |
| `dita` not found | Build command errors, naming the `dita_ot_path` setting |
| No root map set | Build opens the picker rather than failing |
| Unresolvable `href` | Status bar message, no popup |
| Target file missing | Status bar message on goto, warning style on hover |
| Target file unparseable | Hover shows the filename without title or shortdesc |
| Second build started | Status bar reports the running build, first build continues |

## Deferred

- The `dita/preview` panel, using the server's existing custom request
- Creating a missing target file from a broken `href`
- Contributing a DITA-aware formatting provider to the language server
- Contributing `href` and `conref` definition and hover to the language server,
  which would let the client-side layer in `refs.py` retire
