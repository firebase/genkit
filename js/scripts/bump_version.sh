#!/bin/bash

set -e

echo RELEASE_TYPE=$RELEASE_TYPE
echo PREID=$PREID

ROOT=`pwd`
echo ROOT=$ROOT

TAGS=()
NEWLINE=$'\n'
COMMIT_MSG="chore: version bump$NEWLINE$NEWLINE"

bump_version() {
    PACKAGE_PATH=$1
    PACKAGE_NAME=$2

    cd $PACKAGE_PATH
    OLD_VERSION=`node -p "require('./package.json').version"`

    npm version $RELEASE_TYPE --preid $PREID


    NEW_VERSION=`node -p "require('./package.json').version"`

    COMMIT_MSG="$COMMIT_MSG$PACKAGE_NAME version from $OLD_VERSION to $NEW_VERSION$NEWLINE"

    TAG="$PACKAGE_NAME@$NEW_VERSION"
    TAGS+=("$TAG")

    echo " - bumped $PACKAGE_PATH $PACKAGE_NAME $OLD_VERSION -> $NEW_VERSION tag $TAG"

    cd $ROOT
}

commit_and_tag() {
    git status
    git commit -a -m "$COMMIT_MSG"

    for TAG in "${TAGS[@]}"
    do
        echo "tag with $TAG"
        git tag $TAG
    done
}
