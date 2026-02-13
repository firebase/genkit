# Releasekit — Distribution Packaging

This directory contains packaging files for building native OS packages
from the releasekit Python project.

## Debian / Ubuntu

The `debian/` directory follows the standard Debian packaging layout
and uses `pybuild` with the `pyproject` plugin (PEP 517/518).

### Prerequisites

```bash
sudo apt install debhelper dh-python pybuild-plugin-pyproject python3-all
```

### Building

From the releasekit source root:

```bash
# Copy debian/ into the source tree (if building out-of-tree)
cp -r packaging/debian .

# Build the .deb
dpkg-buildpackage -us -uc -b
```

The resulting `python3-releasekit_0.1.0-1_all.deb` will be in the
parent directory.

### Installing

```bash
sudo dpkg -i ../python3-releasekit_0.1.0-1_all.deb
sudo apt-get install -f   # resolve any missing dependencies
```

## Fedora / RHEL / CentOS

The `fedora/` directory contains an RPM spec file that follows Fedora's
Python packaging guidelines using `pyproject-rpm-macros`.

### Fedora Prerequisites

```bash
sudo dnf install python3-devel pyproject-rpm-macros rpm-build
```

### Fedora Building

```bash
# Create the sdist first
cd /path/to/releasekit
python3 -m build --sdist

# Build the RPM from the spec
rpmbuild -ba packaging/fedora/python-releasekit.spec \
    --define "_sourcedir $(pwd)/dist"
```

The resulting RPM will be in `~/rpmbuild/RPMS/noarch/`.

### Fedora Installing

```bash
sudo dnf install ~/rpmbuild/RPMS/noarch/python3-releasekit-0.1.0-1.*.noarch.rpm
```

## Homebrew (macOS / Linux)

The `homebrew/` directory contains a Homebrew formula that installs
releasekit into a Python virtualenv using `virtualenv_install_with_resources`.

### Homebrew Prerequisites

```bash
brew install python@3.13
```

### Homebrew Installing (from local formula)

```bash
brew install --formula packaging/homebrew/releasekit.rb
```

### Homebrew Installing (from tap)

Once published to a tap:

```bash
brew tap firebase/genkit
brew install releasekit
```

## Package contents

All packages install:

- **`/usr/bin/releasekit`** — CLI entry point
- **Python library** — `releasekit` package under the system site-packages
- **Dependencies** — declared as native package dependencies where available

## Updating versions

When releasing a new version:

1. Update `version` in `pyproject.toml`
2. **Debian**: Add a new entry at the top of `debian/changelog`
   (use `dch -v <version>-1` if available)
3. **Fedora**: Update `Version:` in the spec and add a `%changelog` entry
4. **Homebrew**: Update `url` and `sha256` in the formula; resource
   sha256 values can be updated with `brew fetch --retry`

## Dependency sync

Run `releasekit check --fix` to automatically synchronise dependency
lists in all three packaging formats against `pyproject.toml`.
