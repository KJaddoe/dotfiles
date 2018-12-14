# docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
# yarn
curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | sudo apt-key add -
echo "deb https://dl.yarnpkg.com/debian/ stable main" | sudo tee /etc/apt/sources.list.d/yarn.list

# install necessary applications
apt-get update && apt-get install -y \
  vim \
  wget \
  curl \
  git \
  zsh \
  build-essential \
  libssl-dev \
  apt-transport-https \
  ca-certificates \
  software-properties-common \
  yarn \
  docker-ce

# install NVM and nodejs
curl-o-https://raw.githubusercontent.com/creationix/nvm/v0.33.11/install.sh | bash
nvm install --lts
nvm use --lts

# change default shell to zsh
chsh -s $(which zsh)

# install oh-my-zsh
wget https://github.com/robbyrussell/oh-my-zsh/raw/master/tools/install.sh -O - | zsh
# install nvm
wget -qO- https://raw.githubusercontent.com/creationix/nvm/v0.33.11/install.sh | zsh

# export docker host to .zshrc
echo "export DOCKER_HOST=localhost:2375" >> ~/.zshrc
# export yarn global path
echo "export PATH="$(yarn global bin):$PATH" >> ~/.zshrc

# ------------------------ setup dotfiles ------------------------------------------

mkdir -p ~/.vim
mkdir -p ~/.vim/plugins
mkdir -p ~/.vim/colors

# move all dot files to home directory
cp .bashrc ~
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
apt-get update
apt-get install build-essential cmake
apt-get install python-dev
pip2 install neovim
pip3 install neovim

# install vim plugins
git clone https://github.com/VundleVim/Vundle.vim.git ~/.vim/bundle/vundle
vim +PluginInstall +qall

cd ~/.vim/bundle/YouCompleteMe
./install.py --clang-completer
