# KJaddoe's dotfiles

## Before installation

## After installation

1. Change the default shell to zsh using `chsh -s ($which zsh)`
2. Change your shell to zsh (`zsh`) or restart your terminal
3. Install node using nvm and set to use as default using the snippet below
4. Install prettier using npm `npm i -g prettier`

```bash
nvm install --lts
nvm use --lts
nvm alias default lts/*
```

## Node packages used for vim
```bash
npm install -g \
  eslint \
  neovim \
  prettier \
  tern \
  typescript
```
