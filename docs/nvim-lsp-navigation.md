# nvim LSP navigation

Where each code-navigation request is bound, and what to expect when one returns nothing.

Buffer-local maps, attached by `nvim/config/lua/lsp_keymaps.lua` on `LspAttach` for any client
that serves definitions or hover. Global maps live in `nvim/config/lua/user/keymaps.lua`.

## Keymaps

| Key          | Does                                        | Backend               |
|--------------|---------------------------------------------|-----------------------|
| `gd`         | Go to definition                            | telescope             |
| `gr`         | References                                  | trouble               |
| `gi`         | Implementations                             | trouble               |
| `gy`         | Type definition                             | telescope             |
| `gD`         | Go to declaration                           | `vim.lsp.buf`         |
| `gs`         | Signature help                              | `vim.lsp.buf`         |
| `K`          | Hover docs                                  | `vim.lsp.buf`         |
| `<leader>li` | Incoming calls (who calls this)             | trouble               |
| `<leader>lo` | Outgoing calls (what this calls)            | trouble               |
| `<leader>lf` | Combined panel: all of the above at once    | trouble `lsp` mode    |
| `<leader>ls` | Document symbols                            | telescope             |
| `<leader>lS` | Workspace symbols                           | telescope             |
| `<leader>v`  | Definition in a vertical split              | `vim.lsp.buf`         |

Call hierarchy sits under `<leader>l` rather than the `g` prefix on purpose: `gc` is
Comment.nvim's operator, so `gci` / `gco` would break commenting.

## Code actions

| Key          | Mode          | Does                                             |
|--------------|---------------|--------------------------------------------------|
| `<leader>ca` | normal-visual | Code actions for the cursor or the selection     |
| `<leader>cf` | normal        | Fix all auto-fixable eslint problems             |
| `<leader>cm` | normal        | Add missing imports                              |
| `<leader>cu` | normal        | Remove unused imports                            |

`<leader>ca` is mapped in visual mode as well as normal, and that is the point: TypeScript
offers its extract refactors (extract to constant, to a method, to a function) only for a
selected range. Cursor-only, ts_ls returns two actions on a typical expression; over a
selection of that same expression it returns five.

The other three request a single code-action *kind* and apply it. Source-kind actions never
appear in the `<leader>ca` list, which only offers what the cursor or selection resolves to, so
they need their own maps.

They bind only where a client advertises the kind, so they are absent in, say, a Lua buffer.
That gating is why `lsp_autocommands.lua` runs `on_attach` for clients offering `codeAction` as
well as definition or hover: eslint offers neither of those two and would otherwise never
trigger the attach that binds `<leader>cf`.

Organize-imports already runs on every save (`lsp_autocommands.lua`), so `<leader>cm` and
`<leader>cu` are for doing it mid-edit.

## "No implementations found" is usually correct

`textDocument/implementation` only resolves for interfaces and abstract or virtual members. On a
concrete class, a plain function or a local variable, having no answer is the right answer, not a
broken keymap. `gi` therefore separates the two cases before opening a panel:

- no attached server serves the method: a warning naming the request
- served, but nothing to go to: a message saying only interfaces and abstract or virtual members
  have implementations

Servers answer a location request on a concrete symbol with that symbol's own position, so
`lsp_keymaps.lua` discards results that land on the cursor before deciding a request was empty.
That filter is for location requests only: `textDocument/prepareCallHierarchy` answers with the
symbol itself by design, so call hierarchy skips the check and lets trouble report its own
result.

## Single results jump

trouble sets `auto_jump` on its location modes, so a request with exactly one result jumps
straight there instead of opening a panel. A panel means there was more than one.

## Discoverability

which-key's automatic trigger detection does not create a trigger for the `g` prefix here, so
`on_attach` registers the `Goto / LSP` group explicitly. Without it the popup lists none of these
maps. `nvim/tests/test_lsp_keymaps.py` guards this, along with the rule that no buffer-local map
may shadow the global `<leader>D` blackhole delete, that `<leader>ca` reaches visual mode, and
that the source-action maps stay absent where no client advertises their kind.

## Tests

    python3 nvim/tests/test_lsp_keymaps.py

Needs `nvim` and `lua-language-server` on PATH; the suite skips itself otherwise.
