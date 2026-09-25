# LSP-dita

![LICENSE](https://img.shields.io/badge/LICENSE-MIT-green?style=for-the-badge) ![Sublime Text](https://img.shields.io/badge/ST-Build%204132+-orange?style=for-the-badge&logo=sublime-text)

`LSP-dita` is an LSP helper package for the [dita-language-server](https://github.com/aireilly/dita-language-server), which implements the Language Server Protocol for DITA XML. It glues the server to Sublime Text's [LSP](https://packagecontrol.io/packages/LSP) package, manages the server JAR, and adds the editor features the server itself does not cover.

## What comes from where

The language server handles DITA semantics. Some things a DITA author expects are outside what it implements, and this package supplies those on the client side. Knowing which is which makes it obvious where to file a bug.

| Feature | Source |
|---|---|
| Diagnostics: Schematron, duplicate topic and element IDs, keyref and conkeyref resolution, cross-reference targets, profiling values | language server |
| Completion: topic and element IDs for `href`, keys for `keyref` and `conkeyref`, profiling values from the subject scheme | language server |
| Go to definition and hover for `keyref` and `conkeyref` | language server |
| Code actions | language server |
| Root map selection (`dita.setRootMap`) | language server, driven by this package |
| Go to definition and hover for `href`, `conref`, `conrefend`, `copy-to` | **this package** |
| DITA-OT build with clickable diagnostics | **this package** |
| Root map picker | **this package** |
| DITA syntax definition, key bindings, snippets | **this package** |
| Formatting on save | [LSP-lemminx](https://packagecontrol.io/packages/LSP-lemminx) |

Document symbols, rename, find references, and code lens are not available, because the server does not implement them.

## Prerequisites

1. **[LSP](https://packagecontrol.io/packages/LSP)**, from Package Control.
2. **[LSP-lemminx](https://packagecontrol.io/packages/LSP-lemminx)**, from Package Control. This is what formats your DITA on save. Without it, everything else still works and <kbd>Ctrl+S</kbd> simply saves.
3. **Java 17 or newer** on your `PATH`, or reachable through `JAVA_HOME`. The language server is a Java program. If Java is missing or too old, LSP-dita refuses to start the session and tells you which version it found rather than leaving a stack trace in the log.
4. **[DITA-OT](https://www.dita-ot.org/)**, only if you want to build from the editor. The `dita` executable needs to be on your `PATH`, or named in the `dita_ot_path` setting.

You do not need to download the language server yourself. On first use, LSP-dita fetches the pinned release JAR into its package storage directory and verifies it against a known SHA256 before running it.

## Installation

### Package Control

1. Open `Package Control: Add Repository` from the command palette.
2. Enter `https://github.com/aireilly/LSP-dita`.
3. Open `Package Control: Install Package` and choose `LSP-dita`.

### Manual

Clone into your Sublime `Packages` directory:

```bash
cd "$HOME/.config/sublime-text/Packages"     # Linux
git clone https://github.com/aireilly/LSP-dita
```

On macOS the path is `~/Library/Application Support/Sublime Text/Packages`, and on Windows `%APPDATA%\Sublime Text\Packages`.

## First run

Open a `.dita` or `.ditamap` file. The server downloads and starts.

**Then set a root map.** Run `LSP-dita: Set Root Map` from the command palette and pick your map.

This step is not optional decoration. The server builds its key space from the root map, so until one is set, keyref completion, keyref hover, and profiling validation all sit silent and look broken. The choice is remembered per window and re-sent if the server restarts.

## Formatting on save

The DITA language server has no formatting provider. LSP-lemminx does, it understands XML, and it preserves mixed content, so it will not reflow the text inside a `<p>` and quietly change what your topic renders as.

This package ships a `DITA.sublime-settings` file that switches on `lsp_format_on_save` for DITA files alone. Other syntaxes are untouched. Because `text.xml.dita` starts with `text.xml`, LSP-lemminx's default selector already matches DITA files and no configuration is needed.

<kbd>Ctrl+S</kbd> is never rebound. Saving formats because LSP formats on save, which means the usual save behaviour, undo, and every other package that hooks saving all keep working.

To turn it off, set `"lsp_format_on_save": false` in `Preferences: Settings – Syntax Specific` with a DITA file open.

## Key bindings

Everything is scoped to `text.xml.dita`, so no binding leaks into other file types.

| Shortcut | Command | Description |
|---|---|---|
| <kbd>Ctrl+Click</kbd> | Go to Definition | Follow an `href`, `conref`, `conrefend`, `copy-to`, `keyref`, or `conkeyref` |
| <kbd>Ctrl+Shift+Click</kbd> | Go to Definition, split | Open the target beside the current file |
| <kbd>F12</kbd> | Go to Definition | Same, from the keyboard |
| <kbd>Ctrl+Shift+A</kbd> | Code Actions | Trigger server code actions |
| <kbd>Ctrl+Shift+H</kbd> | Hover | Show server hover information |
| <kbd>Ctrl+Shift+B</kbd> | Build with DITA-OT | Build the root map |
| <kbd>Ctrl+Space</kbd> | Auto Complete | Keys, topic IDs, element IDs, profiling values |

<kbd>Ctrl+Shift+B</kbd> replaces Sublime's "Build With" inside DITA files. That is deliberate, since running DITA-OT is what building a DITA project means. Every other syntax keeps the stock binding.

## Navigation and hover

Go to definition is one command covering both halves. A direct file reference is resolved by this package against the filesystem, and anything else is handed to the language server, so `keyref` and `href` behave the same way under the same key.

Addresses parse the full DITA form, `path#topic-id/element-id`, and the jump lands on the addressed element rather than the top of the file. Element IDs are unique within a topic but not within a file, so a document holding several topics can define `step-1` more than once; the search is scoped to the addressed topic, and the right one wins.

References that point outside the project are left alone. An element carrying `scope="external"` or `format="html"`, or a value with a URI scheme such as `https:` or `mailto:`, is not treated as a file reference.

Navigable values carry a faint underline, so you can tell at a glance which attribute values will open something. The underline covers exactly the spans the goto command acts on, which keeps the hint honest: underlined means it will open. Turn it off with `underline_file_references`.

Hovering a file reference shows the target's filename, title, and short description. The filename is clickable. A target that does not exist says so instead.

## Building with DITA-OT

Run `LSP-dita: Build with DITA-OT`, or press <kbd>Ctrl+Shift+B</kbd>.

The build uses the root map you selected, falling back to the nearest `.ditamap` above the current file. If neither exists, the root map picker opens instead of the command failing.

Output streams into a panel as the build runs. Diagnostics carrying a file, line, and column become clickable, so <kbd>F4</kbd> walks you through them.

**A caveat worth knowing:** DITA-OT exits with status 0 even when it has logged errors. Trusting the exit code would report a broken build as a success. This package counts the error lines instead, and the summary tells you what it found:

```
LSP-dita: build finished with 3 errors, 1 warnings
```

The browser opens only on a genuinely clean build. One build runs per window at a time; `LSP-dita: Cancel DITA-OT Build` stops it.

## Configuration

Open `Preferences: LSP-dita Settings` from the command palette, or go to **Preferences > Package Settings > LSP > Servers > LSP-dita**.

| Setting | Default | Description |
|---|---|---|
| `dita_ot_path` | `""` | Absolute path to the `dita` executable. Empty means use `PATH`. |
| `dita_ot_transtype` | `"html5"` | Passed to `dita -f`. |
| `dita_ot_output` | `"out"` | Passed to `dita -o`. Relative paths resolve against the root map's directory. |
| `dita_ot_args` | `[]` | Extra DITA-OT arguments, for example `["--args.draft=yes"]`. |
| `dita_ot_open_output` | `true` | Open `index.html` after a clean build. |
| `hover_file_references` | `true` | Hover popups for `href` and `conref`. |
| `underline_file_references` | `true` | Faint underline under navigable values. |

Every one of these can be set per project, under `settings` → `LSP-dita` in a `.sublime-project` file, which is the natural home for a transtype or output directory that differs between repositories:

```json
{
    "folders": [{"path": "."}],
    "settings": {
        "LSP-dita": {
            "dita_ot_transtype": "pdf",
            "dita_ot_output": "build/pdf"
        }
    }
}
```

### Running a locally built server

Point `command` at your own JAR to test server changes without waiting for a release:

```json
{
    "command": ["java", "-jar", "/home/you/dita-language-server/build/libs/dita-language-server-0.1.0-all.jar"]
}
```

Build that JAR with `./gradlew clean shadowJar` in the server repository.

## Snippets

Tab triggers, available in DITA files:

| Trigger | Produces |
|---|---|
| `concept`, `task`, `reference`, `glossentry` | A complete topic with doctype, ID, title, and short description |
| `ditamap` | A map skeleton |
| `topicref`, `mapref`, `keydef` | Map entries |
| `xref`, `keyref` | Cross references |
| `conref`, `conkeyref` | Content references |
| `note`, `codeblock`, `table`, `ul` | Body elements |

Element and attribute name completion is not duplicated here, because LSP-lemminx already provides it from the DTD, and the language server completes attribute values.

## Troubleshooting

**The session will not start.** Check the LSP log with `LSP: Toggle Log Panel`. A Java problem reports the version it found. Run `java -version` and confirm it is 17 or newer.

**Keyref completion and hover do nothing.** No root map is set. Run `LSP-dita: Set Root Map`.

**A red banner about entity expansions in `svg11-flat-*.dtd`.** Lemminx validates a DITA topic by resolving its DTD chain, which reaches the SVG 1.1 DTD and exceeds the JAXP 64,000 entity expansion limit. The error names a DTD you never wrote.

Raising the limit does not help. LSP-lemminx runs a GraalVM native binary by default, so `java_vmargs` and `xml.server.vmargs` are both ignored.

Run `LSP-dita: Exclude DITA Files from LSP-lemminx Validation`, then restart the server. Nothing is lost: the DITA language server already validates these files with Schematron and its own DTD checks, so lemminx was duplicating work and only one of the two exploded. Formatting and DTD-driven completion carry on unaffected.

The command writes to your User layer, because a package cannot override another package's settings. `settings` is a top-level key in LSP-lemminx's defaults, Sublime merges top-level keys shallowly, and `LSP-lemminx` sorts after `LSP-dita`.

**Saving does not format.** Confirm LSP-lemminx is installed and enabled. `LSP: Troubleshoot Server` on an open DITA file lists the attached sessions; lemminx must be among them.

**A `.xml` file holding a DITA topic is not recognised.** The built-in XML package claims `.xml`, and an extension claim beats a first-line match. Set the syntax by hand with **View > Syntax > DITA**. This package deliberately does not claim `.xml`, which would drag every XML file in every project into the DITA server.

**Ctrl+click does nothing on a reference.** Check whether the element carries `scope="external"` or `format="html"`, both of which mark a target this package will not try to open.

## Reporting issues

Check first whether the behaviour reproduces with the language server alone. Diagnostics, completion, and keyref resolution belong to the server:

https://github.com/aireilly/dita-language-server/issues

Navigation on file references, hover popups, the DITA-OT build, syntax, key bindings, and snippets belong here:

https://github.com/aireilly/LSP-dita/issues

## Development

```bash
python3 -m unittest discover tests -v
ruff check .
```

Logic is kept in pure functions under `plugin/` so it can be tested without Sublime Text, and the modules that touch the Sublime API stay thin. The parts needing a running editor are covered by [docs/manual-verification.md](docs/manual-verification.md).

The design and implementation plan are in [docs/superpowers/](docs/superpowers/).

## Acknowledgements

Built on [LSP](https://packagecontrol.io/packages/LSP) for Sublime Text, [dita-language-server](https://github.com/aireilly/dita-language-server) for DITA semantics, and [LSP-lemminx](https://packagecontrol.io/packages/LSP-lemminx) for XML formatting. Modelled on [LSP-mdita](https://github.com/aireilly/LSP-mdita).

## License

MIT. See [LICENSE.md](LICENSE.md).
