%global pypi_name releasekit

Name:           python-%{pypi_name}
Version:        0.1.0
Release:        1%{?dist}
Summary:        Release orchestration for polyglot monorepos

License:        Apache-2.0
URL:            https://github.com/firebase/genkit
Source0:        %{pypi_source %{pypi_name}}

BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  python3dist(hatchling)
BuildRequires:  pyproject-rpm-macros

%global _description %{expand:
Releasekit automates versioning, changelog generation, and publishing
for polyglot monorepos. It uses Conventional Commits to compute semver
bumps, generates per-package changelogs, and orchestrates multi-package
publishes with dependency-aware topological ordering.

Features:
- Conventional Commits parsing and semver bump computation
- Per-package CHANGELOG.md generation
- Async publish pipeline with retry and rollback
- Pluggable backends for VCS, package managers, and registries
- Support for Python/uv, JS/pnpm, and more}

%description %_description


%package -n python3-%{pypi_name}
Summary:        %{summary}
Requires:       python3dist(aiofiles) >= 24.1
Requires:       python3dist(packaging) >= 24
Requires:       python3dist(tomlkit) >= 0.13
Requires:       python3dist(structlog) >= 25.1
Requires:       python3dist(rich) >= 13
Requires:       python3dist(rich-argparse) >= 1.6
Requires:       python3dist(argcomplete) >= 3
Requires:       python3dist(jinja2) >= 3.1
Requires:       python3dist(diagnostic) >= 3
Requires:       python3dist(httpx) >= 0.27

%description -n python3-%{pypi_name} %_description


%prep
%autosetup -n %{pypi_name}-%{version}


%generate_buildrequires
%pyproject_buildrequires


%build
%pyproject_wheel


%install
%pyproject_install
%pyproject_save_files %{pypi_name}


%check
%pytest


%files -n python3-%{pypi_name} -f %{pyproject_files}
%license LICENSE
%doc README.md
%{_bindir}/releasekit


%changelog
* Wed Feb 12 2026 Google Genkit Team <https://github.com/firebase/genkit/issues> - 0.1.0-1
- Initial package
