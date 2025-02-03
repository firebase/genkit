# Getting Started

!!! note

    If you're a user of Firebase Genkit and landed here,
    this is engineering documentation that someone contributing
    to Genkit would use, not necessarily only use it.

    For more information about how to get started with using
    Firebase Genkit, please see: [User Guide](.)

## Preparing your account

### Create a GitHub account

1. [Sign up](https://github.com/signup) for an account.

2. Please [enable 2 factor authentication
   (2FA)](https://docs.github.com/en/authentication/securing-your-account-with-two-factor-authentication-2fa)
   after having created a GitHub account.

    1.  Use the [Google Authenticator
        app](https://support.google.com/accounts/answer/1066447?hl=en&co=GENIE.Platform%3DAndroid)
        for your device.

        === "Android"

            [Google Authenticator app for Android](https://play.google.com/store/apps/details?id=com.google.android.apps.authenticator2&hl=en_US&pli=1)

        === "iOS"

            [Google Authenticator app for iOS](https://apps.apple.com/us/app/google-authenticator/id388497605)

    2.  Use a physical security key such as the [Google
        Titan](https://store.google.com/product/titan_security_key?hl=en-US).

4. [Generate an SSH
   key](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent)
   for your workstation to associate it with your GitHub account.

    !!! tip

        You can consider using a script such as the following to easily identify
        your key.

        ```bash
        #!/usr/bin/env bash

        UNAME_MRS=$(uname -mrs || echo 'unknown')
        UNAME_OS="$(uname -s | tr '[:upper:]' '[:lower:]' || echo 'unknown')"
        OS_TYPE="$(echo $OSTYPE | tr '[:upper:]' '[:lower:]' || echo 'unknown')"
        CPU_ARCH="$(uname -m || echo 'unknown')"
        OS_DISTRO="$(cat /etc/os-release 2>/dev/null | grep -E '^ID=.*' | sed -e 's/^ID=\(.*\)/\1/g')"

        ssh-keygen -vvvv -t ed25519 -C "ssh://${USER}@$(hostname)/?arch=${CPU_ARCH}&os=${OS_TYPE}&distro=${OS_DISTRO}&timestamp=$(date +'%Y-%m-%dT%H:%M:%S')"
        cat ~/.ssh/id_ed25519.pub >> "${HOME}/.ssh/authorized_keys"
        cat ~/.ssh/id_ed25519.pub
        ```

        Save this to a file called `gen_ssh_key.sh` and run it as follows after
        changing to its container directory:

        ```bash
        chmod a+x gen_ssh_key.sh
        ./gen_ssh_key.sh
        ```

5. [Associate your SSH key with your GitHub account](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/adding-a-new-ssh-key-to-your-github-account).

6. If you're a Googler, also [associate your `@google.com` email
   address](https://docs.github.com/en/account-and-profile/setting-up-and-managing-your-personal-account-on-github/managing-email-preferences/adding-an-email-address-to-your-github-account)
   with your GitHub account and follow any other requirements to complete this
   process.

### GitHub Organization Membership

Please talk to the Genkit Dec team (on [discord](https://discord.gg/qXt5zzQKpc))
to get yourself added to the appropriate groups for your GitHub organization
membership.

### CLA

* Ensure you have [signed the
CLA](https://github.com/firebase/genkit/blob/main/CONTRIBUTING.md#sign-our-contributor-license-agreement).

* For corporate CLAs, please ask the appropriate channels for help.

## Preparing your workstation

!!! note

    === "macOS"

        Install [Homebrew](https://brew.sh/) before proceeding.

    === "Debian"

        Your system should have the required software ready to go.

    === "Fedora"

        Your system should have the required software ready to go.

### Install the GitHub CLI tool

=== "macOS"

    We're assuming you have [Homebrew](https://brew.sh/) installed
    already.


    ```bash
    brew install gh
    ```

=== "Debian/Ubuntu"

    ```bash
    sudo apt install gh
    ```

=== "Fedora"

    ```bash
    sudo dnf install gh
    ```

### Authenticate the CLI with GitHub

```bash
gh auth login
```

### Check out project-related repositories

Consider setting up your workspace to mimic the paths found on GitHub for easier
disambiguation of forks:

```bash
mkdir -p $HOME/code/github.com/firebase/
cd $HOME/code/github.com/firebase

gh repo clone https://github.com/firebase/genkit.git
```

This should allow you to produce a directory structure similar to the following:

```bash
zsh❯ tree -L 3 code
 code
 └── github.com
     ├── firebase
     │   └── genkit
     ├── google
     │   └── dotprompt
     └── yesudeep
         ├── dotprompt
         └── genkit
```

### Configure Git with your legal name and email address.

!!! note inline end

    Googlers should use their `@google.com` email address
    to make commits.

```bash
git config user.email "{username}@domain.com"
git config user.Name "Your Legal Name."
```


### Engineering workstations

Run the following command from the `code/github.com/firebase/genkit` repository
working tree and it should install the required tools for you.

```bash
py/bin/setup
```

### CI/CD

The following is the equivalent used for CI/CD systems.

```bash
py/bin/setup -a ci
```
