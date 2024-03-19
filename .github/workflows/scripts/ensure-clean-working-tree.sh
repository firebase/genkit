#!/bin/bash

if [ "$(git status --short)" ]
then
    echo "Unclean git status"
    git status --short
    exit 1
else 
    echo "Git status is clean"
    exit 0
fi