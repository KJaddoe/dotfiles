# Runtime migration to mise (+ uv) and CLI-only React Native Android

Started 2026-06-10. Full plan: `~/.claude/plans/mighty-enchanting-stallman.md` (read it to resume).

## Goal / why
Consolidate node/python/ruby/java off four separate managers (NVM/pyenv/rbenv/fixed-brew-JDK)
onto **mise** — one fast Rust binary, per-project pinning, asdf-compatible escape hatch (low
lock-in). Python *runtime* on mise, Python *global tooling* on **uv**. dotnet stays as-is.
Then enable React Native Android dev WITHOUT Android Studio (CLI only, run on a USB phone) to
unblock `/Users/karanjaddoe/Projects/client/client-rn-app` (RN 0.73.8, JDK 17, Gradle 8.3,
compileSdk/buildTools 35.0.0, NDK 25.1.8937393, Hermes, native modules reanimated+vision-camera).

## Decisions (from the user)
- Migrate all four runtimes to mise; dotnet untouched (weakest fit, fine on its own install.sh+brew).
- Python global tooling → uv (`uv tool install`), not pip. Why: uv is the 2026 default, far faster.
- Sequencing: full mise migration first, RN Android second. Java migrated early = JDK-17 provider.

## Done (committed on master, one commit per tool)
- `RN device verify` (task #8 — FINAL, migration complete) — pinned client-rn-app via project
  `mise.toml` (`java=temurin-17`, `node=20` → installed 20.20.2; engines wanted node>=18, plan said 20).
  `mise exec -- npm install` (1033 pkgs). `npx react-native run-android` built+deployed to a physical
  Android phone (Android 11) over USB — BUILD SUCCESSFUL, JS bundle loaded, app rendered, no crashes.
  Proves the CLI-only (no Android Studio) RN Android toolchain works on the mise env. GOTCHAS:
  (1) phone first showed `unauthorized` → tap "Allow USB debugging" on device.
  (2) app has productFlavors (development/staging/production) so plain `installDebug` is AMBIGUOUS →
      must pass `--mode developmentDebug`.
  (3) `applicationIdSuffix .client.development` means RN CLI auto-launch targets the wrong package
      (`com.example.app/.MainActivity` → "Activity does not exist"); the install still succeeds —
      launch manually: `adb shell monkey -p com.example.app.client.development.debug -c
      android.intent.category.LAUNCHER 1`.
  Project `mise.toml` is UNTRACKED in the client-rn-app repo — left for the user to commit/gitignore.
- `Add cross-platform android SDK + watchman roles` — new `_system/roles/android` (replaces
  Linux-only `_system/tasks/android.yml`): downloads cmdline-tools (mac/linux via os_family),
  moves to `cmdline-tools/latest`, `yes | sdkmanager --licenses`, installs platform-tools,
  platforms;android-35, build-tools;35.0.0, ndk;25.1.8937393, cmdline-tools;latest. Runs sdkmanager
  via `mise exec --` (gives it mise's java17 — no JAVA_HOME plumbing). New `_system/roles/watchman`
  (brew on mac; apt has no pkg → debug note on Debian) + `brew "watchman"`. Fixed `android/config.zsh`:
  `$OS`→`$OS_TYPE` AND scoped the WSL adb-socket override to real WSL (`grep -qi microsoft /proc/version`)
  so it no longer clobbers ADB_SERVER_SOCKET on native Linux. Installed+verified: adb 1.0.41,
  sdkmanager 12.0. Final SDK packages: platform-tools, platforms;android-35, build-tools;35.0.0,
  ndk;25.1.8937393 (4, NOT 5).
- `Drop redundant cmdline-tools;latest from android SDK packages` — keeping `cmdline-tools;latest`
  in the sdkmanager list made it install a 2nd copy into `cmdline-tools/latest-2` (latest/ was already
  occupied by our manual bootstrap). GOTCHA for any rebuild: bootstrap cmdline-tools into `latest/`
  manually XOR let sdkmanager manage it — not both. Cleaned ~/Android: removed `latest-2` AND the
  pre-existing 2025-05 stray root files (bin/lib/NOTICE.txt/source.properties). Re-ran role →
  idempotent (changed=0), only `latest/` remains.
- `Remove classic vim and brew ruby` — user runs neovim, not classic vim. brew `vim` was the ONLY
  consumer of brew `ruby` (formula declares ruby as build/test dep, but the vim *binary* hard-links
  `libruby.3.4.dylib` via `+ruby` — `otool -L` is ground truth, `brew deps` under-reports it).
  Removed both → ruby now 100% on mise. Autoremoved `lua` 5.4 (a vim `+lua` dep). Neovim UNAFFECTED:
  it links `luajit` (still installed) + vendored LuaJIT, never brew `lua`/`ruby`.
- `Remove nvm/pyenv/openjdk@17/pipx from Brewfile` — dropped those 4 lines; `brew uninstall`ed them
  (+pyenv-virtualenv; rbenv/ruby-build were never brew-installed on this machine). Also removed pipx
  (superseded by uv). Autoremove cleared 19 transitive orphans (~1.7GB). Runtimes re-verified → mise.
- `Migrate ruby to mise` — `ruby@3.3.0` via mise (compiles via ruby-build; kept apt build-deps on
  ubuntu, swapped mac brew rbenv/ruby-build → openssl@3/readline/libyaml). gems bundler rake rubocop
  solargraph via `mise exec -- gem install`. Kept `.gemrc` symlink + `ruby/aliases.zsh`. Removed
  `ruby/path.zsh` (rbenv lazy-load). Used `mise current` guard. Verified: `which ruby`→mise install.
- `Add mise` — role `_system/roles/mise` (brew on mac, apt-repo+GPG on ubuntu like `gh`), hook
  `mise/init.zsh` (`eval "$(mise activate zsh)"`, auto-sourced by zshrc `*/*.zsh` glob), Brewfile.
- `Migrate java to mise` — `java@temurin-17` (resolves 17.0.19). mise exports JAVA_HOME + puts java
  on PATH automatically (Gradle picks it up). Dropped brew openjdk + /Library/Java symlink.
- `Remove obsolete java/path.zsh` — the java migration MISSED deleting its old `java/path.zsh` (unlike
  node/python/ruby which deleted theirs in-commit). That hook ran `/usr/libexec/java_home -v 17` at
  shell init; once the brew-openjdk cleanup removed the last macOS-registered JDK it errored loudly
  ("Unable to locate a Java Runtime") on every new shell + tripped p10k instant-prompt's console-output
  warning. Fix = delete the file (mise already provides JAVA_HOME). java/ dir now empty.
- `Migrate node to mise` — `node@22`, npm globals reinstalled under mise node. Removed `node/path.zsh`.
- `Migrate python to mise and uv` — `python@3.11.15` (see gotcha), uv role added. uv tools:
  black isort pylint rshell jedi-language-server ansible-lint ansible-dev-tools. pynvim pip-installed
  into mise python (nvim finds python3 on PATH; no `g:python3_host_prog` set). Dropped `jedi`
  (bundled by jedi-language-server) and `powerline-status` (unused — they use p10k + shell
  tmux-powerline). Removed `python/path.zsh`.

## Gotchas learned (don't rediscover)
- mise verifies GitHub artifact attestations; old python 3.11.9 standalone build (2024-08) has none
  and fails. Fix = pin a current patch (3.11.15) — keep verification on, don't disable it.
- Idempotent pin pattern: guard `mise use -g` on `mise current <tool>` output, NOT `mise ls
  --installed` — installed≠pinned, and the installed-list guard silently skipped the python pin
  (fell through to pyenv 3.11.9). java/node roles still use the older `mise ls --installed` guard;
  works on fresh installs but retrofit them to the `mise current` compare for consistency.
- Each migration removes its own old `path.zsh` hook in the same commit (not deferred).
- Run a single role with: temp playbook `{hosts: localhost, connection: local, roles: [X]}` +
  `ANSIBLE_ROLES_PATH=.../_system/roles ansible-playbook`. Verify in real shell with `zsh -ic '...'`.

## Remaining
NONE — migration COMPLETE (all 8 tasks done, incl RN device verify on a physical phone).

## State safety
Shell working: java/node/python/ruby all on mise, dotnet untouched. Old managers
(nvm/pyenv/pyenv-virtualenv/openjdk@17/pipx) fully uninstalled + dropped from Brewfile; all their
shell hooks removed. rbenv/ruby-build were never brew-installed here. classic vim + brew ruby removed
(user uses neovim, now provisioned on both OSes via a neovim role). p10k dead segments
(pyenv/nvm/rbenv/jenv) commented out. zsh startup later sped up ~2.1s→~0.32s (see tools/zsh-startup.md).
