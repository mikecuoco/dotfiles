	#!/bin/bash

# Install command-line tools using Homebrew

# (Optionally) Turn off brew's analytics https://docs.brew.sh/Analytics
# brew analytics off

# Make sure we’re using the latest Homebrew
brew update

# Upgrade any already-installed formulae
brew upgrade

# GNU core utilities (those that come with OS X are outdated)
brew install coreutils
brew install moreutils
# GNU `find`, `locate`, `updatedb`, and `xargs`, `g`-prefixed
brew install findutils
# GNU `sed`
brew install gnu-sed

# Updated shells
# Note: don’t forget to add `/usr/local/bin/<EACHSHELL>` to `/etc/shells` before running `chsh`.
brew install bash
brew install zsh
brew install fish
brew install bash-completion

# Install wget
brew install wget

# Install more recent versions of some OS X tools
brew install vim
brew install nano
brew install grep
brew install openssh

# z hopping around folders
brew install z

# better ls 
brew install exa

# better cat
brew install bat

# run this script when this file changes guy.
brew install entr

# git stuff
brew install svn
brew install git
brew install gh # github cli
# nicer git diffs
brew install git-delta
brew install lazygit

# better `top`
brew install glances

# linting for .sh files
brew install shellcheck 

# mtr - ping & traceroute. best.
brew install mtr

    # allow mtr to run without sudo
    mtrlocation=$(brew info mtr | grep Cellar | sed -e 's/ (.*//') #  e.g. `/Users/paulirish/.homebrew/Cellar/mtr/0.86`
    sudo chmod 4755 $mtrlocation/sbin/mtr
    sudo chown root $mtrlocation/sbin/mtr

# Install other useful binaries
brew install the_silver_searcher # ack is an alternative, tbh i forget which i like more.
brew install fzf
brew install imagemagick
brew install node # This installs `npm` too using the recommended installation method
brew install rename
brew install tree
brew install zopfli
brew install ffmpeg
brew install ncdu # find where your diskspace went
brew install tldr

# citations
brew install pandoc
brew install citeproc

# bioinfo / data science
brew install r
brew install samtools
brew install bcftools
brew install bedtools

#brew install scrcpy # control/view android phone from PC. amazing
brew install youtube-dl

# will probably need these at some point
brew install automake cmake go rust

# Remove outdated versions from the cellar
brew cleanup
