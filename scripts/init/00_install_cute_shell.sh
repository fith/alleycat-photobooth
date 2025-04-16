#!/bin/bash

# install oh-my-posh
curl -s https://ohmyposh.dev/install.sh | bash -s
# fix path
echo "# set PATH so it includes user's private bin if it exists
if [ -d "$HOME/.local/bin" ] ; then
    PATH="$HOME/.local/bin:$PATH"
fi" >> .bashrc
# install omp font
oh-my-posh font install meslo
# add oh-my-posh init to the .bashrc
echo 'eval "$(oh-my-posh init bash --config ~/.cache/oh-my-posh/themes/cert.omp.json)"' >> .bashrc