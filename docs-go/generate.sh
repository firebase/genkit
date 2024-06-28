#!/bin/sh -e

weave=$HOME/go/bin/weave
if [[ ! -f $weave ]]; then
  echo "installing weave"
  go -C ../go install ./internal/cmd/weave
fi

for file in flows models; do
  $weave $file.src > $file.md
done

