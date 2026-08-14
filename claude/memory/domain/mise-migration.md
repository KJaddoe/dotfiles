# Runtime migration to mise (+ uv) and CLI-only React Native Android

COMPLETE (2026-06-10 → 06-11). Migrated node/python/ruby/java off four managers
(NVM/pyenv/rbenv/fixed-brew-JDK) onto **mise**; Python global tooling onto **uv**; dotnet untouched.
Then enabled React Native Android dev CLI-only (no Android Studio, run on a USB phone). Per-commit
narrative lives in git history; only the durable don't-regress lessons are kept below.

## Decisions (from the user)

- All four runtimes → mise (one fast Rust binary, per-project pinning, asdf-compatible escape hatch).
  dotnet stays as-is (weakest fit, fine on its own install.sh + brew).
- Python *runtime* on mise, Python *global tooling* on **uv** (`uv tool install`) not pip — uv is the
  2026 default and far faster. Superseded pipx.
- Sequencing: full mise migration first (Java early = JDK-17 provider), RN Android second.

## mise gotchas (don't rediscover)

- mise verifies GitHub artifact attestations; old python 3.11.9 standalone build (2024-08) has none and
  fails. Fix = pin a current patch (e.g. 3.11.15) — keep verification on, don't disable it.
- Idempotent pin: guard `mise use -g` on `mise current <tool>` output, NOT `mise ls --installed`
  (installed ≠ pinned — the installed-list guard silently skipped the python pin and fell through to
  pyenv 3.11.9). java/node roles still use the older `mise ls --installed` guard; retrofit to
  `mise current` when touched.
- Each runtime migration removed its own old `path.zsh` hook in the same commit. The java migration
  MISSED this once — the stale `java/path.zsh` ran `/usr/libexec/java_home -v 17` at shell init and
  errored loudly ("Unable to locate a Java Runtime") on every new shell once brew-openjdk was removed.
  mise already exports JAVA_HOME + puts java on PATH, so the hook must be deleted.
- Run a single ansible role: temp playbook `{hosts: localhost, connection: local, roles: [X]}` +
  `ANSIBLE_ROLES_PATH=.../_system/roles ansible-playbook`. Verify in a real shell with `zsh -ic '...'`.
- `otool -L` is ground truth for native link deps, not `brew deps`: brew `vim`'s formula under-reported
  that the binary hard-links `libruby` via `+ruby`. Removing classic vim was what finally freed brew
  `ruby` (now 100% on mise). neovim links luajit + vendored LuaJIT, never brew ruby/lua — unaffected.

## Android SDK / RN gotchas

- `_system/roles/android` bootstraps cmdline-tools into `cmdline-tools/latest/` manually. Do NOT ALSO
  list `cmdline-tools;latest` in the sdkmanager package list — it installs a 2nd copy into `latest-2/`.
  Bootstrap into `latest/` manually XOR let sdkmanager manage it, never both. Run sdkmanager via
  `mise exec --` to give it mise's java17 (no JAVA_HOME plumbing).
- `android/config.zsh`: scope the WSL adb-socket override to real WSL (`grep -qi microsoft /proc/version`)
  so it doesn't clobber `ADB_SERVER_SOCKET` on native Linux.
- RN Android on a physical phone (CLI-only toolchain verified working):
  (1) phone shows `unauthorized` → tap "Allow USB debugging" on device.
  (2) app with productFlavors → plain `installDebug` is AMBIGUOUS; pass `--mode <flavor>Debug`.
  (3) a flavor with `applicationIdSuffix` makes RN CLI auto-launch target the base package and fail
      ("Activity does not exist") though install succeeds → launch manually with the suffixed id:
      `adb shell monkey -p <applicationId> -c android.intent.category.LAUNCHER 1`.
  A project `mise.toml` pins the RN app's toolchain (`java=temurin-17`, `node=20`); it stays UNTRACKED
  in the client repo (user commits/gitignores it).

## End state

node/python/ruby/java all on mise, dotnet untouched. Old managers (nvm/pyenv/pyenv-virtualenv/
openjdk@17/pipx) uninstalled + dropped from Brewfile, all their shell hooks removed. classic vim +
brew ruby removed (neovim provisioned on both OSes via a neovim role). p10k dead segments
(pyenv/nvm/rbenv/jenv) commented out. zsh startup later sped ~2.1s→~0.32s (see tools/zsh-startup.md).
