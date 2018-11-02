# install necessary applications
apt-get update && apt-get install -y \
  vim \
  wget \
  git \
  zsh 

# change default shell to zsh
chsh -s $(which zsh)

# install oh-my-zsh
wget https://github.com/robbyrussell/oh-my-zsh/raw/master/tools/install.sh -O - | zsh
# install nvm
wget -qO- https://raw.githubusercontent.com/creationix/nvm/v0.33.11/install.sh | zsh

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
