#!/bin/bash
# docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"

# install necessary applications
apt-get update && apt-get install -y \
  vim \
  wget \
  curl \
  git \
  zsh \
  build-essential \
  cmake \
  python-dev
  libssl-dev \
  apt-transport-https \
  ca-certificates \
  software-properties-common \
  docker-ce

# install oh-my-zsh
wget https://github.com/robbyrussell/oh-my-zsh/raw/master/tools/install.sh -O - | zsh
# install nvm
wget -qO- https://raw.githubusercontent.com/creationix/nvm/v0.34.00/install.sh | zsh
# change default shell to zsh
chsh -s $(which zsh) | zsh
# set node installation
nvm install --lts | zsh
nvm use --lts | zsh
nvm alias default lts/* | zsh
# global install prettier
npm i -g prettier | zsh


# export docker host to .zshrc
grep -q -x -F 'export DOCKER_HOST=localhost:2375' ~/.zshrc || echo 'export DOCKER_HOST=localhost:2375' >> ~/.zshrc
# windows hostfile alias
grep -q -x -F 'alias hostfile="vim /mnt/c/Windows/System32/drivers/etc/hosts"' ~/.zshrc || echo 'alias hostfile="vim /mnt/c/Windows/System32/drivers/etc/hosts"' >> ~/.zshrc

cp wsl.conf /etc

# ------------------------ setup dotfiles ------------------------------------------

mkdir -p ~/.vim
mkdir -p ~/.vim/plugins
mkdir -p ~/.vim/colors

# move all dot files to home directory
cp .vimrc ~
cp .inputrc ~

# vim settings
cp .vim/.mappings ~/.vim
cp .vim/.projectmappings  ~/.vim
cp .vim/.plugins ~/.vim
cp .vim/.settings ~/.vim
cp .vim/.ycm_extra_conf.py ~/.vim

cp .vim/colors/ir_black.vim ~/.vim/colors
cp .vim/plugins/cscope_maps.vim ~/.vim/plugins

# nvim symlinks
cp .config/nvim ~.config/nvim

# install stuff

# dependencies
pip2 install neovim
pip3 install neovim

# install vim plugins
git clone https://github.com/VundleVim/Vundle.vim.git ~/.vim/bundle/vundle
vim +PluginInstall +qall

cd ~/.vim/bundle/YouCompleteMe
./install.py --clang-completer
