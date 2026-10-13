#!/bin/sh
# A container engine whose "run" fails right away, like a bad image.
case "$1" in
  run) echo "Error: image not known" >&2; exit 125 ;;
  info) echo x86_64 ;;
  *) exit 0 ;;
esac
