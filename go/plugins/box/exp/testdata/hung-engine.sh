#!/bin/sh
# A container engine that accepts every command and never starts anything:
# "run" hangs, everything else succeeds. Tests point PodmanOptions.Engine at it.
case "$1" in
  run) exec sleep 60 ;;
  info) echo arm64 ;;
  *) exit 0 ;;
esac
