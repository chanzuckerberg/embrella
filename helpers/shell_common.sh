#!/bin/bash
set -euo pipefail

export RED='\033[0;31m'
export GREEN='\033[0;32m'
export NC='\033[0m'

function echocolor() {
  COLOR=$1
  MSG=$2
  echo -e "${COLOR}${MSG}${NC}"
}

function ask_yes_or_no() {
  read -p "$1 ([y]es or [N]o): "
  case $(echo $REPLY | tr '[A-Z]' '[z-z]') in
    y|yes) echo "yes" ;;
    *)     echo "no" ;;
  esac
}

function ask_if_really_sure() {
  if [[ "no" == $(ask_yes_or_no "Are you sure?") || \
    "no" == $(ask_yes_or_no "Are you *really* sure?") ]]
  then
    echo "no"
  else
    echo "yes"
  fi
}

# Print a SQL dump, decompressing .gz. Picks by extension, not gzip -f, for BSD/GNU parity.
function cat_dump() {
  case "$1" in
    *.gz) gunzip -c "$1" ;;
    *)    cat "$1" ;;
  esac
}

function encrypt_file() {
  password=$1
  filepath=$2
  VK=$password openssl enc -aes-256-cbc -pbkdf2 -a -in $filepath -pass env:VK
}

function decrypt_stdin() {
  password=$1
  VK=$password openssl enc -d -aes-256-cbc -pbkdf2 -a -in /dev/stdin -pass env:VK
}

# This checks if ./.scratch/<tmp file derived from passed filename> exists
# and whether its contents match the sha1sum of the contents of the passed file
# If not exists, or contents changed. returns "yes"
# Else no.
function check_filechanged() {
  filetocheck=$1
  cached_hash="./.scratch/$(echo $filetocheck | sha1sum | cut -d " " -f 1)"
  if [ ! -f $cached_hash ]; then
    cat $filetocheck | sha1sum | cut -d " " -f 1 > $cached_hash
    echo "yes"
    exit 0
  fi
  oldhash=$(<$cached_hash)
  newhash=$(cat $filetocheck | sha1sum | cut -d " " -f 1)
  if [ "$oldhash" != "$newhash" ]; then
    echo "yes"
  else
    echo "no"
  fi
}

function set_filechanged() {
  filetocheck=$1
  cached_hash="./.scratch/$(echo $filetocheck | sha1sum | cut -d " " -f 1)"
  cat $filetocheck | sha1sum | cut -d " " -f 1 > $cached_hash
}

function export_env() {
  unamestr=$(uname)
  if [ "$unamestr" = 'Linux' ]; then
    export $(grep -v '^#' .env | xargs -d '\n')
  elif [ "$unamestr" = 'FreeBSD' ] || [ "$unamestr" = 'Darwin' ]; then
    export $(grep -v '^#' .env | xargs -0)
  fi
}