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
- `Remove nvm/pyenv/openjdk@17/pipx from Brewfile` — dropped those 4 lines; `brew uninstall`ed them
  (+pyenv-virtualenv; rbenv/ruby-build were never brew-installed on this machine). Also removed pipx
  (superseded by uv). KEPT `brew "ruby"` — vim depends on it (`brew uses --installed ruby`→vim).
  Autoremove cleared 19 transitive orphans (~1.7GB). All 4 runtimes re-verified → mise installs.
- `Migrate ruby to mise` — `ruby@3.3.0` via mise (compiles via ruby-build; kept apt build-deps on
  ubuntu, swapped mac brew rbenv/ruby-build → openssl@3/readline/libyaml). gems bundler rake rubocop
  solargraph via `mise exec -- gem install`. Kept `.gemrc` symlink + `ruby/aliases.zsh`. Removed
  `ruby/path.zsh` (rbenv lazy-load). Used `mise current` guard. Verified: `which ruby`→mise install.
- `Add mise` — role `_system/roles/mise` (brew on mac, apt-repo+GPG on ubuntu like `gh`), hook
  `mise/init.zsh` (`eval "$(mise activate zsh)"`, auto-sourced by zshrc `*/*.zsh` glob), Brewfile.
- `Migrate java to mise` — `java@temurin-17` (resolves 17.0.19). mise sets JAVA_HOME automatically
  (Gradle picks it up). Dropped brew openjdk + /Library/Java symlink.
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

## Remaining (next session)
1. **Android CLI + watchman** (task #7): convert Linux-only `_system/tasks/android.yml` into
   cross-platform `_system/roles/android` (download commandlinetools-{mac,linux} to
   `~/Android/cmdline-tools/latest`, sdkmanager: platform-tools, platforms;android-35,
   build-tools;35.0.0, ndk;25.1.8937393, cmdline-tools;latest, then `yes | sdkmanager --licenses`).
   Add `_system/roles/watchman` + `brew "watchman"`. Fix `android/config.zsh` bug (`$OS`→`$OS_TYPE`).
   NDK is ~1GB (long download).
2. **RN device verify** (task #8): pin client-rn-app to java17/node20 (`mise.toml`); `npm install`;
   connect phone (USB debugging); `adb devices`; `npx react-native run-android`. Needs the phone.

## State safety
Shell working: java/node/python/ruby all on mise, dotnet untouched. Old managers
(nvm/pyenv/pyenv-virtualenv/openjdk@17/pipx) fully uninstalled + dropped from Brewfile; all their
shell hooks removed. rbenv/ruby-build were never brew-installed here. `brew "ruby"` intentionally
kept (vim dep). Leftover cosmetic: p10k prompt still lists pyenv/nvm/rbenv segments (no-op when
binaries absent) — harmless, trim later if desired.
