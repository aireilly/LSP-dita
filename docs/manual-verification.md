# Manual verification

The Sublime Text API cannot be imported outside Sublime, so the logic in
`plugin/` is unit tested and the editor integration is checked by hand. Work
through this list after changing anything under `plugin/`, the syntax, or the
key bindings.

Set up a scratch DITA project first:

```bash
mkdir -p /tmp/dita-check/tasks
cd /tmp/dita-check

cat > main.ditamap <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE map PUBLIC "-//OASIS//DTD DITA Map//EN" "map.dtd">
<map>
  <title>Verification map</title>
  <keydef keys="install-topic" href="tasks/installing.dita"/>
  <topicref href="tasks/installing.dita"/>
  <topicref href="overview.dita"/>
</map>
EOF

cat > overview.dita <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE concept PUBLIC "-//OASIS//DTD DITA Concept//EN" "concept.dtd">
<concept id="overview">
  <title>Overview</title>
  <shortdesc>What this product does and why you would use it.</shortdesc>
  <conbody>
    <p>See <xref href="tasks/installing.dita#installing/step-2"/> to begin.</p>
    <p>Or follow <xref keyref="install-topic"/>.</p>
    <p>A broken one: <xref href="tasks/nowhere.dita"/>.</p>
    <p>External: <xref href="https://example.com" scope="external">docs</xref>.</p>
  </conbody>
</concept>
EOF

cat > tasks/installing.dita <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE task PUBLIC "-//OASIS//DTD DITA Task//EN" "task.dtd">
<task id="installing">
  <title>Installing the operator</title>
  <shortdesc>Install the operator from OperatorHub.</shortdesc>
  <taskbody>
    <steps>
      <step id="step-1"><cmd>Open the console.</cmd></step>
      <step id="step-2"><cmd>Select the operator.</cmd></step>
    </steps>
  </taskbody>
</task>
EOF
```

Open the folder in Sublime Text as a project.

## 1. Syntax resolves to `text.xml.dita`

Open `overview.dita`. Open the console with <kbd>Ctrl+`</kbd> and run:

```python
view.scope_name(0)
```

**Expected:** the result begins `text.xml.dita`.

**If it reports `text.xml` instead,** the `extends:` directive did not re-scope.
Replace `DITA.sublime-syntax` with a standalone syntax whose main context
includes the XML syntax by scope:

```yaml
%YAML 1.2
---
name: DITA
scope: text.xml.dita
version: 2
file_extensions: [dita, ditamap, ditaval]
first_line_match: '-//OASIS//DTD DITA'
contexts:
  main:
    - include: scope:text.xml
```

## 2. Both language servers attach

With `overview.dita` open, run `LSP: Troubleshoot Server`.

**Expected:** both `dita` and `lemminx` appear as active sessions. The `dita`
session is what supplies diagnostics; `lemminx` is what formats on save.

If `dita` is missing, check `LSP: Toggle Log Panel` for a Java version message.

## 3. Root map selection wakes up keyrefs

Before setting a root map, put the cursor inside the `keyref` value on the
`install-topic` line and press <kbd>Ctrl+Shift+H</kbd>.

**Expected:** nothing, or no key information. This is the inert state.

Now run `LSP-dita: Set Root Map` and choose `main.ditamap`.

**Expected:** a status message naming the map. Hover the same `keyref` again.

**Expected:** the server reports the key's target or navtitle.

## 4. Ctrl+click follows a file reference to the right element

Ctrl+click the `href` value `tasks/installing.dita#installing/step-2`.

**Expected:** `installing.dita` opens with the caret on the `step-2` line, not
at the top of the file and not on `step-1`.

## 5. Ctrl+click still reaches the server for keyrefs

Ctrl+click the `keyref` value `install-topic`.

**Expected:** `installing.dita` opens. This path goes through
`lsp_symbol_definition`, proving the fallback works.

## 6. References that opt out are left alone

Ctrl+click the `https://example.com` value, which carries `scope="external"`.

**Expected:** nothing opens and no error appears. The click is a plain click.

## 7. A broken reference reports itself

Ctrl+click `tasks/nowhere.dita`.

**Expected:** a status bar message saying the file does not exist. No new tab.

## 8. Hover shows title and short description

Hover the `href` value `tasks/installing.dita#installing/step-2`.

**Expected:** a popup with `installing.dita` as a clickable link, the title
`Installing the operator`, and the short description
`Install the operator from OperatorHub.` Clicking the link opens the file.

Hover `tasks/nowhere.dita`.

**Expected:** a popup saying the file does not exist.

## 9. Ctrl+S formats without reflowing mixed content

Collapse the indentation of the `<steps>` block in `installing.dita`, then
save with <kbd>Ctrl+S</kbd>.

**Expected:** the block is re-indented.

Now check the critical case. In `overview.dita`, confirm this line survives a
save with its spacing around the `<xref>` intact:

```xml
<p>See <xref href="tasks/installing.dita#installing/step-2"/> to begin.</p>
```

**Expected:** the words `See` and `to begin.` keep exactly one space against
the `<xref>`. If a newline appears inside the `<p>`, formatting is reflowing
mixed content and the rendered output would change. Report that against
LSP-lemminx, and turn `lsp_format_on_save` off for DITA meanwhile.

Open a Markdown or Python file and save it.

**Expected:** no formatting happens, confirming the setting is scoped to DITA.

## 10. The DITA-OT build streams and its errors are clickable

Press <kbd>Ctrl+Shift+B</kbd>.

**Expected:** a panel opens, the command line appears first, then output
streams as the build runs rather than arriving all at once when it finishes.

The scratch project has a deliberately broken `xref`, so the build logs errors.

**Expected:** the summary line reads
`LSP-dita: build finished with N errors, N warnings`, and the browser does
**not** open, even though DITA-OT exits 0.

Press <kbd>F4</kbd>.

**Expected:** the caret jumps to the file, line, and column of the first
positional diagnostic.

Fix the broken `xref` by pointing it at `overview.dita`, then build again.

**Expected:** `LSP-dita: build succeeded`, and `out/index.html` opens in a
browser.

## 11. Only one build runs at a time

Start a build, and while it runs press <kbd>Ctrl+Shift+B</kbd> again.

**Expected:** a status message saying a build is already running. Then run
`LSP-dita: Cancel DITA-OT Build`.

**Expected:** the build stops and the status bar confirms it.

## 12. Snippets expand in DITA files only

In `overview.dita`, type `xref` and press <kbd>Tab</kbd>.

**Expected:** the cross-reference snippet expands with the caret on the href
placeholder.

Type `xref` and <kbd>Tab</kbd> in a Markdown file.

**Expected:** no expansion, confirming the snippet scope.
