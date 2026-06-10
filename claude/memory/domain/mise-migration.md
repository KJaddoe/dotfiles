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
1. **ruby → mise** (task #5): rewrite `_system/roles/ruby` to `mise use -g ruby@3.3.0` + `gem install`
   globals (bundler rake rubocop solargraph), keep `.gemrc` symlink, remove the rbenv lazy-load
   functions in `ruby/path.zsh`. Lowest value (iOS-only here). Use the `mise current` guard pattern.
2. **Hook/Brewfile cleanup** (task #6): remove nvm/pyenv/rbenv/ruby-build/openjdk@17 from Brewfile;
   `brew uninstall` them only after all runtimes verified. rollback = git revert.
3. **Android CLI + watchman** (task #7): convert Linux-only `_system/tasks/android.yml` into
   cross-platform `_system/roles/android` (download commandlinetools-{mac,linux} to
   `~/Android/cmdline-tools/latest`, sdkmanager: platform-tools, platforms;android-35,
   build-tools;35.0.0, ndk;25.1.8937393, cmdline-tools;latest, then `yes | sdkmanager --licenses`).
   Add `_system/roles/watchman` + `brew "watchman"`. Fix `android/config.zsh` bug (`$OS`→`$OS_TYPE`).
   NDK is ~1GB (long download).
4. **RN device verify** (task #8): pin client-rn-app to java17/node20 (`mise.toml`); `npm install`;
   connect phone (USB debugging); `adb devices`; `npx react-native run-android`. Needs the phone.

## State safety
Shell is working: java/node/python on mise, ruby still on rbenv (untouched), dotnet untouched.
Old managers (nvm/pyenv/rbenv) still installed; their hooks for node/python removed, rbenv hook
still present. mise wins PATH precedence even when an old hook is still loaded.
