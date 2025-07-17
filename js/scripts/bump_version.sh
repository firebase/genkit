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
    shift
    PACKAGE_NAME=$1
    shift
    TAG_PREFIXES=()
    TAG_PREFIXES=$*
    echo TAG_PREFIXES "${TAG_PREFIXES[*]}"

    if [[ -z "${TAG_PREFIXES[*]}" ]]; then
        TAG_PREFIXES=()
    fi
    TAG_PREFIXES+=("$PACKAGE_NAME@")

    cd $PACKAGE_PATH
    OLD_VERSION=`node -p "require('./package.json').version"`

    npm version $RELEASE_TYPE --preid $PREID


    NEW_VERSION=`node -p "require('./package.json').version"`

    COMMIT_MSG="$COMMIT_MSG$PACKAGE_NAME version from $OLD_VERSION to $NEW_VERSION$NEWLINE"


    for TAG_PREFIX in "${TAG_PREFIXES[@]}"
    do
        TAG="$TAG_PREFIX$NEW_VERSION"
        echo "add tag: $TAG"
        TAGS+=("$TAG")
    done


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
