# nvim LSP

How code navigation, code actions and diagnostics are wired, and what to expect when a
request returns nothing.

Server configs, capabilities and diagnostic settings live in the `nvim-lspconfig` spec in
`nvim/config/lua/user/plugins/init.lua`, which loads on `BufReadPre`/`BufNewFile` rather than at
startup: none of it has an effect until a file is open, and `vim.lsp.enable` re-runs its own
`FileType` handler across buffers that already exist, so loading late still attaches.

Buffer-local maps, attached by `nvim/config/lua/lsp_keymaps.lua` on `LspAttach` for any client
that serves definitions, hover or code actions. Global maps live in
`nvim/config/lua/user/keymaps.lua`, and the telescope pickers in the plugin spec's `keys`.

## Keymaps

| Key          | Does                             | Backend             |
|--------------|----------------------------------|---------------------|
| `gd`         | Go to definition                 | telescope           |
| `grr`        | References                       | telescope           |
| `gri`        | Implementations                  | telescope           |
| `gy`         | Type definition                  | telescope           |
| `gD`         | Go to declaration                | `vim.lsp.buf`       |
| `gs`         | Signature help                   | `vim.lsp.buf`       |
| `K`          | Hover docs                       | `vim.lsp.buf`       |
| `<leader>li` | Incoming calls (who calls this)  | telescope           |
| `<leader>lo` | Outgoing calls (what this calls) | telescope           |
| `<leader>ls` | Document symbols                 | telescope           |
| `<leader>lS` | Workspace symbols                | telescope           |
| `<leader>cl` | Run the code lens on this line   | `vim.lsp.codelens`  |
| `<leader>v`  | Definition in a vertical split   | `vim.lsp.buf`       |

References and implementations use the `grr` / `gri` names rather than `gr` / `gi` because
nvim 0.11 owns the whole `gr` family globally: a bare `gr` would be a prefix of `grr`, `gri`,
`grn` and `gra` and would stall for `timeoutlen` before firing. The two maps above re-point
nvim's own names at telescope, which previews each result; `grn` and `gra` are left alone.

Call hierarchy sits under `<leader>l` rather than the `g` prefix on purpose: `gc` is the
built-in comment operator, so `gci` / `gco` would read as comment-a-textobject.

## Code actions

| Key          | Mode          | Does                                         |
|--------------|---------------|----------------------------------------------|
| `gra`        | normal-visual | Code actions for the cursor or the selection |
| `grn`        | normal        | Rename the symbol under the cursor           |
| `<leader>cf` | normal        | Fix all auto-fixable eslint problems         |
| `<leader>cm` | normal        | Add missing imports                          |
| `<leader>cu` | normal        | Remove unused imports                        |

`gra` and `grn` are nvim's own defaults, kept rather than rebound. `gra` covers visual mode as
well as normal, and that is the point: TypeScript offers its extract refactors (extract to
constant, to a method, to a function) only for a selected range. Cursor-only, ts_ls returns two
actions on a typical expression; over a selection of that same expression it returns five.

The other three request a single code-action *kind* and apply it. Source-kind actions never
appear in the `gra` list, which only offers what the cursor or selection resolves to, so they
need their own maps.

They bind only where a client advertises the kind, so they are absent in, say, a Lua buffer.
That gating is why `lsp_autocommands.lua` runs `on_attach` for clients offering `codeAction` as
well as definition or hover: eslint offers neither of those two and would otherwise never
trigger the attach that binds `<leader>cf`.

Organize-imports already runs on every save (`lsp_autocommands.lua`), so `<leader>cm` and
`<leader>cu` are for doing it mid-edit.

## "No implementations found" is usually correct

`textDocument/implementation` only resolves for interfaces and abstract or virtual members. On a
concrete class, a plain function or a local variable, having no answer is the right answer, not a
broken keymap. An empty result set is reported as an `INFO` notification naming the request.

References is the one request that drops a result: telescope filters out the line the cursor is
already on, so the count is other references, not including the symbol itself. Definitions, type
definitions and implementations keep everything the server returns, and a server answering a
location request on a concrete symbol with that symbol's own position is why `gri` can land you
back where you started rather than saying nothing was found.

## Single results jump

telescope's location pickers jump straight to the result when a request returns exactly one,
instead of opening a picker. A picker means there was more than one.

## Diagnostics

| Key          | Does                                          |
|--------------|-----------------------------------------------|
| `]d` / `[d`  | Next / previous diagnostic, centred           |
| `<leader>gl` | Full message for the current line in a float  |
| `<leader>xx` | Every diagnostic nvim holds, in a picker      |

Both inline forms are off: `virtual_text` and `virtual_lines` are `false`, so a file full of
diagnostics stays readable. The message lives in the bordered float instead, which `]d` and `[d`
open on arrival and `<leader>gl` opens on demand.

Navigation goes through `vim.diagnostic.jump()`. `goto_next`/`goto_prev` are deprecated and are
removed in nvim 0.13; `nvim/tests/test_lsp_keymaps.py` fails if they come back, and likewise if
`DiagnosticSign*` signs are defined through `sign_define` instead of `vim.diagnostic.config`.

## Discoverability

which-key's automatic trigger detection does not create a trigger for the `g` prefix here, so
`on_attach` registers the `Goto / LSP` group explicitly. Without it the popup lists none of these
maps. `nvim/tests/test_lsp_keymaps.py` guards this, along with the rule that no buffer-local map
may shadow the global `<leader>D` blackhole delete, that nothing buffer-local shadows `gra` and
that it still reaches visual mode, and that the source-action maps stay absent where no client
advertises their kind.

## Tests

    python3 nvim/tests/test_lsp_keymaps.py

Needs `nvim` and `lua-language-server` on PATH; the suite skips itself otherwise.
