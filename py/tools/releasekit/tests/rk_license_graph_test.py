# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for the license compatibility graph."""

from __future__ import annotations

from pathlib import Path

import pytest
from releasekit.checks._license_graph import LicenseDataError, LicenseGraph
from releasekit.spdx_expr import LicenseId, LicenseRef


@pytest.fixture()
def graph() -> LicenseGraph:
    """Load the built-in license graph."""
    return LicenseGraph.load()


# ── Loading ──────────────────────────────────────────────────────────


class TestLoading:
    """Tests for loading."""

    def test_loads_licenses(self, graph: LicenseGraph) -> None:
        """Test loads licenses."""
        assert len(graph.nodes) >= 40

    def test_loads_rules(self, graph: LicenseGraph) -> None:
        """Test loads rules."""
        assert len(graph.edges) >= 30

    def test_mit_exists(self, graph: LicenseGraph) -> None:
        """Test mit exists."""
        assert graph.known('MIT')

    def test_apache_exists(self, graph: LicenseGraph) -> None:
        """Test apache exists."""
        assert graph.known('Apache-2.0')

    def test_unknown_license(self, graph: LicenseGraph) -> None:
        """Test unknown license."""
        assert not graph.known('NoSuchLicense-99.0')

    def test_license_info_fields(self, graph: LicenseGraph) -> None:
        """Test license info fields."""
        info = graph.nodes['MIT']
        assert info.spdx_id == 'MIT'
        assert info.name == 'MIT License'
        assert info.category == 'permissive'
        assert info.osi_approved is True
        assert len(info.aliases) > 0


# ── Categories ───────────────────────────────────────────────────────


class TestCategories:
    """Tests for categories."""

    def test_permissive(self, graph: LicenseGraph) -> None:
        """Test permissive."""
        assert graph.category('MIT') == 'permissive'
        assert graph.category('Apache-2.0') == 'permissive'
        assert graph.category('BSD-3-Clause') == 'permissive'

    def test_weak_copyleft(self, graph: LicenseGraph) -> None:
        """Test weak copyleft."""
        assert graph.category('LGPL-3.0-only') == 'weak-copyleft'
        assert graph.category('MPL-2.0') == 'weak-copyleft'
        assert graph.category('EPL-2.0') == 'weak-copyleft'

    def test_strong_copyleft(self, graph: LicenseGraph) -> None:
        """Test strong copyleft."""
        assert graph.category('GPL-2.0-only') == 'strong-copyleft'
        assert graph.category('GPL-3.0-only') == 'strong-copyleft'

    def test_network_copyleft(self, graph: LicenseGraph) -> None:
        """Test network copyleft."""
        assert graph.category('AGPL-3.0-only') == 'network-copyleft'

    def test_source_available(self, graph: LicenseGraph) -> None:
        """Test source available."""
        assert graph.category('SSPL-1.0') == 'source-available'
        assert graph.category('BUSL-1.1') == 'source-available'

    def test_proprietary(self, graph: LicenseGraph) -> None:
        """Test proprietary."""
        assert graph.category('Proprietary') == 'proprietary'

    def test_unknown_category(self, graph: LicenseGraph) -> None:
        """Test unknown category."""
        assert graph.category('NoSuchLicense') == 'unknown'


# ── Permissive ↔ Permissive ─────────────────────────────────────────


class TestPermissiveCompat:
    """Tests for permissive Compat."""

    @pytest.mark.parametrize(
        'project,dep',
        [
            ('MIT', 'ISC'),
            ('MIT', 'BSD-3-Clause'),
            ('MIT', 'Apache-2.0'),
            ('Apache-2.0', 'MIT'),
            ('BSD-3-Clause', 'BSD-2-Clause'),
            ('0BSD', 'CC0-1.0'),
            ('Zlib', 'BSL-1.0'),
        ],
    )
    def test_permissive_mutual_compat(self, graph: LicenseGraph, project: str, dep: str) -> None:
        """Test permissive mutual compat."""
        assert graph.is_compatible(project, LicenseId(dep))


# ── The #1 Gotcha: Apache-2.0 vs GPL-2.0-only ───────────────────────


class TestApacheGplGotcha:
    """Tests for apache Gpl Gotcha."""

    def test_gpl2_only_cannot_depend_on_apache(self, graph: LicenseGraph) -> None:
        """GPL-2.0-only CANNOT depend on Apache-2.0 (patent clause conflict)."""
        assert not graph.is_compatible('GPL-2.0-only', LicenseId('Apache-2.0'))

    def test_gpl3_can_depend_on_apache(self, graph: LicenseGraph) -> None:
        """GPL-3.0-only CAN depend on Apache-2.0 (designed for this)."""
        assert graph.is_compatible('GPL-3.0-only', LicenseId('Apache-2.0'))

    def test_gpl2_or_later_can_depend_on_apache(self, graph: LicenseGraph) -> None:
        """GPL-2.0-or-later CAN depend on Apache-2.0 (upgrade to v3)."""
        assert graph.is_compatible('GPL-2.0-or-later', LicenseId('Apache-2.0'))


# ── GPL version incompatibility ─────────────────────────────────────


class TestGplVersionCompat:
    """Tests for gpl Version Compat."""

    def test_gpl2_only_cannot_depend_on_gpl3(self, graph: LicenseGraph) -> None:
        """Test gpl2 only cannot depend on gpl3."""
        assert not graph.is_compatible('GPL-2.0-only', LicenseId('GPL-3.0-only'))

    def test_gpl3_cannot_depend_on_gpl2_only(self, graph: LicenseGraph) -> None:
        """Test gpl3 cannot depend on gpl2 only."""
        assert not graph.is_compatible('GPL-3.0-only', LicenseId('GPL-2.0-only'))

    def test_gpl3_can_depend_on_gpl2_or_later(self, graph: LicenseGraph) -> None:
        """Test gpl3 can depend on gpl2 or later."""
        assert graph.is_compatible('GPL-3.0-only', LicenseId('GPL-2.0-or-later'))


# ── AGPL compatibility ──────────────────────────────────────────────


class TestAgplCompat:
    """Tests for agpl Compat."""

    def test_agpl3_cannot_depend_on_gpl2_only(self, graph: LicenseGraph) -> None:
        """Test agpl3 cannot depend on gpl2 only."""
        assert not graph.is_compatible('AGPL-3.0-only', LicenseId('GPL-2.0-only'))

    def test_agpl3_can_depend_on_gpl3(self, graph: LicenseGraph) -> None:
        """Test agpl3 can depend on gpl3."""
        assert graph.is_compatible('AGPL-3.0-only', LicenseId('GPL-3.0-only'))

    def test_gpl3_can_depend_on_agpl3(self, graph: LicenseGraph) -> None:
        """Test gpl3 can depend on agpl3."""
        assert graph.is_compatible('GPL-3.0-only', LicenseId('AGPL-3.0-only'))


# ── Copyleft → Permissive (one-way) ─────────────────────────────────


class TestCopyleftToPermissive:
    """Tests for copyleft To Permissive."""

    def test_gpl3_can_depend_on_mit(self, graph: LicenseGraph) -> None:
        """Test gpl3 can depend on mit."""
        assert graph.is_compatible('GPL-3.0-only', LicenseId('MIT'))

    def test_mit_cannot_depend_on_gpl3(self, graph: LicenseGraph) -> None:
        """Test mit cannot depend on gpl3."""
        assert not graph.is_compatible('MIT', LicenseId('GPL-3.0-only'))

    def test_lgpl3_can_depend_on_mit(self, graph: LicenseGraph) -> None:
        """Test lgpl3 can depend on mit."""
        assert graph.is_compatible('LGPL-3.0-only', LicenseId('MIT'))

    def test_mit_cannot_depend_on_lgpl3(self, graph: LicenseGraph) -> None:
        """Test mit cannot depend on lgpl3."""
        assert not graph.is_compatible('MIT', LicenseId('LGPL-3.0-only'))


# ── GPL-incompatible free licenses ───────────────────────────────────


class TestGplIncompatible:
    """Tests for gpl Incompatible."""

    def test_gpl3_cannot_depend_on_cddl(self, graph: LicenseGraph) -> None:
        """Test gpl3 cannot depend on cddl."""
        assert not graph.is_compatible('GPL-3.0-only', LicenseId('CDDL-1.0'))

    def test_gpl3_cannot_depend_on_epl1(self, graph: LicenseGraph) -> None:
        """Test gpl3 cannot depend on epl1."""
        assert not graph.is_compatible('GPL-3.0-only', LicenseId('EPL-1.0'))

    def test_cddl_can_depend_on_mit(self, graph: LicenseGraph) -> None:
        """Test cddl can depend on mit."""
        assert graph.is_compatible('CDDL-1.0', LicenseId('MIT'))


# ── Source-available / proprietary ───────────────────────────────────


class TestSourceAvailable:
    """Tests for source Available."""

    def test_sspl_has_no_compat_edges(self, graph: LicenseGraph) -> None:
        """Test sspl has no compat edges."""
        assert not graph.is_compatible('MIT', LicenseId('SSPL-1.0'))

    def test_bsl11_has_no_compat_edges(self, graph: LicenseGraph) -> None:
        """Test bsl11 has no compat edges."""
        assert not graph.is_compatible('MIT', LicenseId('BUSL-1.1'))

    def test_proprietary_has_no_compat_edges(self, graph: LicenseGraph) -> None:
        """Test proprietary has no compat edges."""
        assert not graph.is_compatible('MIT', LicenseId('Proprietary'))


# ── or_later (+) expansion ───────────────────────────────────────────


class TestOrLaterExpansion:
    """Tests for or Later Expansion."""

    def test_gpl2_plus_compat_with_gpl3_project(self, graph: LicenseGraph) -> None:
        """A dep licensed GPL-2.0+ can be used by a GPL-3.0 project."""
        dep = LicenseId('GPL-2.0-only', or_later=True)
        assert graph.is_compatible('GPL-3.0-only', dep)

    def test_gpl2_only_not_compat_with_gpl3_project(self, graph: LicenseGraph) -> None:
        """A dep licensed GPL-2.0-only (no +) cannot be used by GPL-3.0."""
        dep = LicenseId('GPL-2.0-only', or_later=False)
        assert not graph.is_compatible('GPL-3.0-only', dep)

    def test_lgpl21_plus_compat_with_lgpl3_project(self, graph: LicenseGraph) -> None:
        """Test lgpl21 plus compat with lgpl3 project."""
        dep = LicenseId('LGPL-2.1-only', or_later=True)
        assert graph.is_compatible('LGPL-3.0-only', dep)

    def test_agpl3_plus_stays_agpl3(self, graph: LicenseGraph) -> None:
        """Test agpl3 plus stays agpl3."""
        dep = LicenseId('AGPL-3.0-only', or_later=True)
        assert graph.is_compatible('AGPL-3.0-only', dep)


# ── LicenseRef handling ──────────────────────────────────────────────


class TestLicenseRef:
    """Tests for license Ref."""

    def test_license_ref_always_incompatible(self, graph: LicenseGraph) -> None:
        """Test license ref always incompatible."""
        ref = LicenseRef(ref='LicenseRef-Custom')
        assert not graph.is_compatible('MIT', ref)

    def test_string_dep(self, graph: LicenseGraph) -> None:
        """Test string dep."""
        assert graph.is_compatible('MIT', 'ISC')

    def test_unknown_project_license(self, graph: LicenseGraph) -> None:
        """Test unknown project license."""
        assert not graph.is_compatible('NoSuchLicense', LicenseId('MIT'))


# ── incompatible_deps() ─────────────────────────────────────────────


class TestIncompatibleDeps:
    """Tests for incompatible Deps."""

    def test_finds_violations(self, graph: LicenseGraph) -> None:
        """Test finds violations."""
        deps: dict[str, LicenseId | LicenseRef | str] = {
            'good-pkg': LicenseId('MIT'),
            'bad-pkg': LicenseId('GPL-3.0-only'),
        }
        violations = graph.incompatible_deps('MIT', deps)
        assert 'bad-pkg' in violations
        assert 'good-pkg' not in violations

    def test_no_violations(self, graph: LicenseGraph) -> None:
        """Test no violations."""
        deps: dict[str, LicenseId | LicenseRef | str] = {
            'a': LicenseId('MIT'),
            'b': LicenseId('ISC'),
            'c': LicenseId('BSD-3-Clause'),
        }
        violations = graph.incompatible_deps('Apache-2.0', deps)
        assert violations == {}

    def test_string_deps(self, graph: LicenseGraph) -> None:
        """Test string deps."""
        deps: dict[str, LicenseId | LicenseRef | str] = {
            'ok': 'MIT',
            'bad': 'SSPL-1.0',
        }
        violations = graph.incompatible_deps('Apache-2.0', deps)
        assert 'bad' in violations
        assert 'ok' not in violations


# ── all_aliases() ────────────────────────────────────────────────────


class TestAliases:
    """Tests for aliases."""

    def test_spdx_id_is_alias(self, graph: LicenseGraph) -> None:
        """Test spdx id is alias."""
        aliases = graph.all_aliases()
        assert aliases['mit'] == 'MIT'
        assert aliases['apache-2.0'] == 'Apache-2.0'

    def test_common_alias(self, graph: LicenseGraph) -> None:
        """Test common alias."""
        aliases = graph.all_aliases()
        assert aliases['the mit license'] == 'MIT'
        assert aliases['apache 2.0'] == 'Apache-2.0'

    def test_pypi_classifier_alias(self, graph: LicenseGraph) -> None:
        """Test pypi classifier alias."""
        aliases = graph.all_aliases()
        key = 'license :: osi approved :: mit license'
        assert aliases[key] == 'MIT'


# ── User overrides ───────────────────────────────────────────────────


class TestUserOverrides:
    """Tests for user Overrides."""

    def test_merge_new_license(self, tmp_path: Path) -> None:
        """Test merge new license."""
        user_toml = tmp_path / 'user.toml'
        user_toml.write_text(
            '[licenses.MyCustom-1]\n'
            'name = "My Custom License"\n'
            'category = "permissive"\n'
            'osi_approved = false\n'
            'aliases = ["my custom"]\n'
            '\n'
            '[[rule]]\n'
            'from = "MyCustom-1"\n'
            'to = ["MIT", "Apache-2.0"]\n'
        )
        graph = LicenseGraph.load(user_toml=user_toml)
        assert graph.known('MyCustom-1')
        assert graph.category('MyCustom-1') == 'permissive'
        assert graph.is_compatible('MyCustom-1', LicenseId('MIT'))
        assert graph.is_compatible('MyCustom-1', LicenseId('Apache-2.0'))

    def test_merge_extends_aliases(self, tmp_path: Path) -> None:
        """Test merge extends aliases."""
        user_toml = tmp_path / 'user.toml'
        user_toml.write_text('[licenses.MIT]\naliases = ["my-mit-variant"]\n')
        graph = LicenseGraph.load(user_toml=user_toml)
        aliases = graph.all_aliases()
        # User alias added.
        assert aliases['my-mit-variant'] == 'MIT'
        # Built-in aliases preserved.
        assert aliases['the mit license'] == 'MIT'

    def test_nonexistent_user_toml_ignored(self) -> None:
        """Test nonexistent user toml ignored."""
        graph = LicenseGraph.load(user_toml=Path('/nonexistent/user.toml'))
        assert graph.known('MIT')

    def test_merge_appends_rules(self, tmp_path: Path) -> None:
        """Test merge appends rules."""
        user_toml = tmp_path / 'user.toml'
        user_toml.write_text('[[rule]]\nfrom = "MIT"\nto = ["SSPL-1.0"]\n')
        graph = LicenseGraph.load(user_toml=user_toml)
        # User override: MIT can now depend on SSPL-1.0.
        assert graph.is_compatible('MIT', LicenseId('SSPL-1.0'))


# ── MPL-2.0 compatibility ───────────────────────────────────────────


class TestMplCompat:
    """Tests for mpl Compat."""

    def test_gpl3_can_depend_on_mpl2(self, graph: LicenseGraph) -> None:
        """GPL-3.0 can depend on MPL-2.0 via §3.3."""
        assert graph.is_compatible('GPL-3.0-only', LicenseId('MPL-2.0'))

    def test_mpl2_can_depend_on_mit(self, graph: LicenseGraph) -> None:
        """Test mpl2 can depend on mit."""
        assert graph.is_compatible('MPL-2.0', LicenseId('MIT'))

    def test_mpl2_can_depend_on_apache(self, graph: LicenseGraph) -> None:
        """Test mpl2 can depend on apache."""
        assert graph.is_compatible('MPL-2.0', LicenseId('Apache-2.0'))


# ── TOML validation ──────────────────────────────────────────────────


class TestBuiltinDataValidation:
    """Ensure the shipped TOML files pass validation."""

    def test_builtin_data_is_valid(self) -> None:
        """Test builtin data is valid."""
        graph = LicenseGraph.load()
        # If we get here without LicenseDataError, the data is valid.
        assert len(graph.nodes) >= 40
        assert len(graph.edges) >= 30


class TestLicenseTomlValidation:
    """Tests for license Toml Validation."""

    def test_missing_name(self, tmp_path: Path) -> None:
        """Test missing name."""
        lic = tmp_path / 'licenses.toml'
        lic.write_text('[BadLicense]\ncategory = "permissive"\nosi_approved = true\naliases = []\n')
        compat = tmp_path / 'compat.toml'
        compat.write_text('')
        with pytest.raises(LicenseDataError, match='missing required field "name"'):
            LicenseGraph.load(licenses_toml=lic, compat_toml=compat)

    def test_missing_category(self, tmp_path: Path) -> None:
        """Test missing category."""
        lic = tmp_path / 'licenses.toml'
        lic.write_text('[BadLicense]\nname = "Bad"\nosi_approved = true\naliases = []\n')
        compat = tmp_path / 'compat.toml'
        compat.write_text('')
        with pytest.raises(LicenseDataError, match='missing required field "category"'):
            LicenseGraph.load(licenses_toml=lic, compat_toml=compat)

    def test_invalid_category(self, tmp_path: Path) -> None:
        """Test invalid category."""
        lic = tmp_path / 'licenses.toml'
        lic.write_text('[BadLicense]\nname = "Bad"\ncategory = "super-free"\nosi_approved = true\naliases = []\n')
        compat = tmp_path / 'compat.toml'
        compat.write_text('')
        with pytest.raises(LicenseDataError, match='not a valid category'):
            LicenseGraph.load(licenses_toml=lic, compat_toml=compat)

    def test_osi_approved_wrong_type(self, tmp_path: Path) -> None:
        """Test osi approved wrong type."""
        lic = tmp_path / 'licenses.toml'
        lic.write_text('[BadLicense]\nname = "Bad"\ncategory = "permissive"\nosi_approved = "yes"\naliases = []\n')
        compat = tmp_path / 'compat.toml'
        compat.write_text('')
        with pytest.raises(LicenseDataError, match='osi_approved.*expected bool'):
            LicenseGraph.load(licenses_toml=lic, compat_toml=compat)

    def test_aliases_wrong_type(self, tmp_path: Path) -> None:
        """Test aliases wrong type."""
        lic = tmp_path / 'licenses.toml'
        lic.write_text(
            '[BadLicense]\nname = "Bad"\ncategory = "permissive"\nosi_approved = true\naliases = "not-a-list"\n'
        )
        compat = tmp_path / 'compat.toml'
        compat.write_text('')
        with pytest.raises(LicenseDataError, match='aliases.*expected list'):
            LicenseGraph.load(licenses_toml=lic, compat_toml=compat)

    def test_name_wrong_type(self, tmp_path: Path) -> None:
        """Test name wrong type."""
        lic = tmp_path / 'licenses.toml'
        lic.write_text('[BadLicense]\nname = 42\ncategory = "permissive"\nosi_approved = true\naliases = []\n')
        compat = tmp_path / 'compat.toml'
        compat.write_text('')
        with pytest.raises(LicenseDataError, match='name.*expected string'):
            LicenseGraph.load(licenses_toml=lic, compat_toml=compat)

    def test_multiple_errors_collected(self, tmp_path: Path) -> None:
        """Test multiple errors collected."""
        lic = tmp_path / 'licenses.toml'
        lic.write_text(
            '[Bad1]\n'
            'category = "permissive"\n'
            'osi_approved = true\n'
            'aliases = []\n'
            '\n'
            '[Bad2]\n'
            'name = "Bad Two"\n'
            'osi_approved = true\n'
            'aliases = []\n'
        )
        compat = tmp_path / 'compat.toml'
        compat.write_text('')
        with pytest.raises(LicenseDataError) as exc_info:
            LicenseGraph.load(licenses_toml=lic, compat_toml=compat)
        assert len(exc_info.value.errors) >= 2


class TestCompatTomlValidation:
    """Tests for compat Toml Validation."""

    def test_rule_missing_from(self, tmp_path: Path) -> None:
        """Test rule missing from."""
        lic = tmp_path / 'licenses.toml'
        lic.write_text('[MIT]\nname = "MIT License"\ncategory = "permissive"\nosi_approved = true\naliases = []\n')
        compat = tmp_path / 'compat.toml'
        compat.write_text('[[rule]]\nto = ["MIT"]\n')
        with pytest.raises(LicenseDataError, match='missing required field "from"'):
            LicenseGraph.load(licenses_toml=lic, compat_toml=compat)

    def test_rule_missing_to(self, tmp_path: Path) -> None:
        """Test rule missing to."""
        lic = tmp_path / 'licenses.toml'
        lic.write_text('[MIT]\nname = "MIT License"\ncategory = "permissive"\nosi_approved = true\naliases = []\n')
        compat = tmp_path / 'compat.toml'
        compat.write_text('[[rule]]\nfrom = "MIT"\n')
        with pytest.raises(LicenseDataError, match='missing required field "to"'):
            LicenseGraph.load(licenses_toml=lic, compat_toml=compat)

    def test_rule_from_wrong_type(self, tmp_path: Path) -> None:
        """Test rule from wrong type."""
        lic = tmp_path / 'licenses.toml'
        lic.write_text('[MIT]\nname = "MIT License"\ncategory = "permissive"\nosi_approved = true\naliases = []\n')
        compat = tmp_path / 'compat.toml'
        compat.write_text('[[rule]]\nfrom = 42\nto = ["MIT"]\n')
        with pytest.raises(LicenseDataError, match='from.*expected string'):
            LicenseGraph.load(licenses_toml=lic, compat_toml=compat)

    def test_rule_to_wrong_type(self, tmp_path: Path) -> None:
        """Test rule to wrong type."""
        lic = tmp_path / 'licenses.toml'
        lic.write_text('[MIT]\nname = "MIT License"\ncategory = "permissive"\nosi_approved = true\naliases = []\n')
        compat = tmp_path / 'compat.toml'
        compat.write_text('[[rule]]\nfrom = "MIT"\nto = "MIT"\n')
        with pytest.raises(LicenseDataError, match='to.*expected list'):
            LicenseGraph.load(licenses_toml=lic, compat_toml=compat)


class TestGraphValidation:
    """Tests for graph Validation."""

    def test_dangling_from_reference(self, tmp_path: Path) -> None:
        """Test dangling from reference."""
        lic = tmp_path / 'licenses.toml'
        lic.write_text('[MIT]\nname = "MIT License"\ncategory = "permissive"\nosi_approved = true\naliases = []\n')
        compat = tmp_path / 'compat.toml'
        compat.write_text('[[rule]]\nfrom = "NoSuchLicense"\nto = ["MIT"]\n')
        with pytest.raises(LicenseDataError, match='unknown.*NoSuchLicense'):
            LicenseGraph.load(licenses_toml=lic, compat_toml=compat)

    def test_dangling_to_reference(self, tmp_path: Path) -> None:
        """Test dangling to reference."""
        lic = tmp_path / 'licenses.toml'
        lic.write_text('[MIT]\nname = "MIT License"\ncategory = "permissive"\nosi_approved = true\naliases = []\n')
        compat = tmp_path / 'compat.toml'
        compat.write_text('[[rule]]\nfrom = "MIT"\nto = ["NoSuchLicense"]\n')
        with pytest.raises(LicenseDataError, match='unknown.*to.*NoSuchLicense'):
            LicenseGraph.load(licenses_toml=lic, compat_toml=compat)

    def test_duplicate_alias_across_licenses(self, tmp_path: Path) -> None:
        """Test duplicate alias across licenses."""
        lic = tmp_path / 'licenses.toml'
        lic.write_text(
            '[LicA]\n'
            'name = "License A"\n'
            'category = "permissive"\n'
            'osi_approved = true\n'
            'aliases = ["shared alias"]\n'
            '\n'
            '[LicB]\n'
            'name = "License B"\n'
            'category = "permissive"\n'
            'osi_approved = true\n'
            'aliases = ["Shared Alias"]\n'
        )
        compat = tmp_path / 'compat.toml'
        compat.write_text('')
        with pytest.raises(LicenseDataError, match='Duplicate alias'):
            LicenseGraph.load(licenses_toml=lic, compat_toml=compat)

    def test_error_message_lists_all_errors(self, tmp_path: Path) -> None:
        """Test error message lists all errors."""
        lic = tmp_path / 'licenses.toml'
        lic.write_text('[MIT]\nname = "MIT License"\ncategory = "permissive"\nosi_approved = true\naliases = []\n')
        compat = tmp_path / 'compat.toml'
        compat.write_text('[[rule]]\nfrom = "Ghost1"\nto = ["Ghost2"]\n')
        with pytest.raises(LicenseDataError) as exc_info:
            LicenseGraph.load(licenses_toml=lic, compat_toml=compat)
        err = exc_info.value
        assert len(err.errors) >= 2
        msg = str(err)
        assert 'Ghost1' in msg
        assert 'Ghost2' in msg
        assert 'validation error' in msg


# ── Google category ──────────────────────────────────────────────────


class TestGoogleCategory:
    """Tests for google Category."""

    def test_mit_is_notice(self, graph: LicenseGraph) -> None:
        """Test mit is notice."""
        assert graph.google_category('MIT') == 'notice'

    def test_apache_is_notice(self, graph: LicenseGraph) -> None:
        """Test apache is notice."""
        assert graph.google_category('Apache-2.0') == 'notice'

    def test_gpl3_is_restricted(self, graph: LicenseGraph) -> None:
        """Test gpl3 is restricted."""
        assert graph.google_category('GPL-3.0-only') == 'restricted'

    def test_agpl3_is_forbidden(self, graph: LicenseGraph) -> None:
        """Test agpl3 is forbidden."""
        assert graph.google_category('AGPL-3.0-only') == 'forbidden'

    def test_mpl2_is_reciprocal(self, graph: LicenseGraph) -> None:
        """Test mpl2 is reciprocal."""
        assert graph.google_category('MPL-2.0') == 'reciprocal'

    def test_unlicense_is_unencumbered(self, graph: LicenseGraph) -> None:
        """Test unlicense is unencumbered."""
        assert graph.google_category('Unlicense') == 'unencumbered'

    def test_cc0_is_unencumbered(self, graph: LicenseGraph) -> None:
        """Test cc0 is unencumbered."""
        assert graph.google_category('CC0-1.0') == 'unencumbered'

    def test_json_is_by_exception_only(self, graph: LicenseGraph) -> None:
        """Test json is by exception only."""
        assert graph.google_category('JSON') == 'by_exception_only'

    def test_unknown_returns_empty(self, graph: LicenseGraph) -> None:
        """Test unknown returns empty."""
        assert graph.google_category('NoSuchLicense-99') == ''

    def test_invalid_google_category_rejected(self, tmp_path: Path) -> None:
        """Test invalid google category rejected."""
        lic = tmp_path / 'licenses.toml'
        lic.write_text(
            '[MIT]\n'
            'name = "MIT License"\n'
            'category = "permissive"\n'
            'google_category = "invalid_category"\n'
            'osi_approved = true\n'
            'aliases = []\n'
        )
        compat = tmp_path / 'compat.toml'
        compat.write_text('')
        with pytest.raises(LicenseDataError) as exc_info:
            LicenseGraph.load(licenses_toml=lic, compat_toml=compat)
        assert 'invalid_category' in str(exc_info.value)

    def test_new_cc_licenses_loaded(self, graph: LicenseGraph) -> None:
        """Verify some of the new CC licenses from the expansion."""
        assert graph.known('CC-BY-4.0')
        assert graph.known('CC-BY-SA-4.0')
        assert graph.known('CC-BY-NC-4.0')
        assert graph.google_category('CC-BY-4.0') == 'notice'
        assert graph.google_category('CC-BY-NC-4.0') == 'forbidden'

    def test_new_misc_licenses_loaded(self, graph: LicenseGraph) -> None:
        """Verify some of the new misc licenses from the expansion."""
        assert graph.known('OFL-1.1')
        assert graph.known('WTFPL')
        assert graph.known('W3C')
        assert graph.google_category('OFL-1.1') == 'by_exception_only'
        assert graph.google_category('WTFPL') == 'forbidden'


# ── Or-later chains from TOML ────────────────────────────────────────


class TestOrLaterChains:
    """Tests for or Later Chains."""

    def test_gpl2_only_chain(self, graph: LicenseGraph) -> None:
        """Test gpl2 only chain."""
        info = graph.nodes['GPL-2.0-only']
        assert info.or_later_chain == (
            'GPL-2.0-only',
            'GPL-2.0-or-later',
            'GPL-3.0-only',
            'GPL-3.0-or-later',
        )

    def test_gpl2_or_later_chain(self, graph: LicenseGraph) -> None:
        """Test gpl2 or later chain."""
        info = graph.nodes['GPL-2.0-or-later']
        assert info.or_later_chain == (
            'GPL-2.0-or-later',
            'GPL-3.0-only',
            'GPL-3.0-or-later',
        )

    def test_gpl3_only_chain(self, graph: LicenseGraph) -> None:
        """Test gpl3 only chain."""
        info = graph.nodes['GPL-3.0-only']
        assert info.or_later_chain == ('GPL-3.0-only', 'GPL-3.0-or-later')

    def test_gpl3_or_later_chain(self, graph: LicenseGraph) -> None:
        """Test gpl3 or later chain."""
        info = graph.nodes['GPL-3.0-or-later']
        assert info.or_later_chain == ('GPL-3.0-or-later',)

    def test_lgpl21_only_chain(self, graph: LicenseGraph) -> None:
        """Test lgpl21 only chain."""
        info = graph.nodes['LGPL-2.1-only']
        assert info.or_later_chain == (
            'LGPL-2.1-only',
            'LGPL-2.1-or-later',
            'LGPL-3.0-only',
            'LGPL-3.0-or-later',
        )

    def test_agpl3_only_chain(self, graph: LicenseGraph) -> None:
        """Test agpl3 only chain."""
        info = graph.nodes['AGPL-3.0-only']
        assert info.or_later_chain == ('AGPL-3.0-only', 'AGPL-3.0-or-later')

    def test_mit_has_no_chain(self, graph: LicenseGraph) -> None:
        """Test mit has no chain."""
        info = graph.nodes['MIT']
        assert info.or_later_chain == ()

    def test_apache_has_no_chain(self, graph: LicenseGraph) -> None:
        """Test apache has no chain."""
        info = graph.nodes['Apache-2.0']
        assert info.or_later_chain == ()

    def test_lgpl20_only_chain(self, graph: LicenseGraph) -> None:
        """Test lgpl20 only chain."""
        info = graph.nodes['LGPL-2.0-only']
        assert 'LGPL-2.1-only' in info.or_later_chain


# ── Google licenseclassifier coverage ────────────────────────────────


class TestGoogleClassifierCoverage:
    """Verify every license from Google's licenseclassifier is present."""

    # -- restricted --
    @pytest.mark.parametrize(
        'spdx_id',
        [
            'BCL',
            'GPL-1.0-only',
            'GPL-2.0-only',
            'GPL-2.0-or-later',
            'GPL-3.0-only',
            'GPL-3.0-or-later',
            'GPL-2.0-with-autoconf-exception',
            'GPL-2.0-with-bison-exception',
            'GPL-2.0-with-classpath-exception',
            'GPL-2.0-with-font-exception',
            'GPL-2.0-with-GCC-exception',
            'GPL-3.0-with-autoconf-exception',
            'GPL-3.0-with-GCC-exception',
            'LGPL-2.0-only',
            'LGPL-2.0-or-later',
            'LGPL-2.1-only',
            'LGPL-2.1-or-later',
            'LGPL-3.0-only',
            'LGPL-3.0-or-later',
            'LGPLLR',
            'NPL-1.0',
            'NPL-1.1',
            'OSL-1.0',
            'OSL-1.1',
            'OSL-2.0',
            'OSL-2.1',
            'OSL-3.0',
            'QPL-1.0',
            'Sleepycat',
            'CC-BY-ND-1.0',
            'CC-BY-ND-2.0',
            'CC-BY-ND-2.5',
            'CC-BY-ND-3.0',
            'CC-BY-ND-4.0',
            'CC-BY-SA-1.0',
            'CC-BY-SA-2.0',
            'CC-BY-SA-2.5',
            'CC-BY-SA-3.0',
            'CC-BY-SA-4.0',
        ],
    )
    def test_restricted_licenses(self, graph: LicenseGraph, spdx_id: str) -> None:
        """Test restricted licenses."""
        assert graph.known(spdx_id), f'{spdx_id} not in graph'
        assert graph.google_category(spdx_id) == 'restricted'

    # -- reciprocal --
    @pytest.mark.parametrize(
        'spdx_id',
        [
            'APSL-1.0',
            'APSL-1.1',
            'APSL-1.2',
            'APSL-2.0',
            'CDDL-1.0',
            'CDDL-1.1',
            'CPL-1.0',
            'EPL-1.0',
            'EPL-2.0',
            'FreeImage',
            'IPL-1.0',
            'MPL-1.0',
            'MPL-1.1',
            'MPL-2.0',
            'Ruby',
        ],
    )
    def test_reciprocal_licenses(self, graph: LicenseGraph, spdx_id: str) -> None:
        """Test reciprocal licenses."""
        assert graph.known(spdx_id), f'{spdx_id} not in graph'
        assert graph.google_category(spdx_id) == 'reciprocal'

    # -- notice --
    @pytest.mark.parametrize(
        'spdx_id',
        [
            'AFL-1.1',
            'AFL-1.2',
            'AFL-2.0',
            'AFL-2.1',
            'AFL-3.0',
            'Apache-1.0',
            'Apache-1.1',
            'Apache-2.0',
            'Artistic-1.0',
            'Artistic-1.0-cl8',
            'Artistic-1.0-Perl',
            'Artistic-2.0',
            'BSL-1.0',
            'BSD-2-Clause',
            'BSD-2-Clause-FreeBSD',
            'BSD-2-Clause-NetBSD',
            'BSD-3-Clause',
            'BSD-3-Clause-Attribution',
            'BSD-3-Clause-Clear',
            'BSD-3-Clause-LBNL',
            'BSD-4-Clause',
            'BSD-4-Clause-UC',
            'BSD-Protection',
            'CC-BY-1.0',
            'CC-BY-2.0',
            'CC-BY-2.5',
            'CC-BY-3.0',
            'CC-BY-4.0',
            'FTL',
            'ISC',
            'ImageMagick',
            'Libpng',
            'Lil-1.0',
            'Linux-OpenIB',
            'LPL-1.0',
            'LPL-1.02',
            'MS-PL',
            'MIT',
            'NCSA',
            'OpenSSL',
            'PHP-3.0',
            'PHP-3.01',
            'PIL',
            'Python-2.0',
            'Python-2.0-complete',
            'PostgreSQL',
            'SGI-B-1.0',
            'SGI-B-1.1',
            'SGI-B-2.0',
            'Unicode-DFS-2015',
            'Unicode-DFS-2016',
            'Unicode-TOU',
            'UPL-1.0',
            'W3C',
            'W3C-19980720',
            'W3C-20150513',
            'X11',
            'Xnet',
            'Zend-2.0',
            'zlib-acknowledgement',
            'Zlib',
            'ZPL-1.1',
            'ZPL-2.0',
            'ZPL-2.1',
        ],
    )
    def test_notice_licenses(self, graph: LicenseGraph, spdx_id: str) -> None:
        """Test notice licenses."""
        assert graph.known(spdx_id), f'{spdx_id} not in graph'
        assert graph.google_category(spdx_id) == 'notice'

    # -- unencumbered --
    @pytest.mark.parametrize('spdx_id', ['CC0-1.0', 'Unlicense', '0BSD'])
    def test_unencumbered_licenses(self, graph: LicenseGraph, spdx_id: str) -> None:
        """Test unencumbered licenses."""
        assert graph.known(spdx_id), f'{spdx_id} not in graph'
        assert graph.google_category(spdx_id) == 'unencumbered'

    # -- by_exception_only --
    @pytest.mark.parametrize('spdx_id', ['Beerware', 'OFL-1.1', 'OpenVision'])
    def test_by_exception_only_licenses(self, graph: LicenseGraph, spdx_id: str) -> None:
        """Test by exception only licenses."""
        assert graph.known(spdx_id), f'{spdx_id} not in graph'
        assert graph.google_category(spdx_id) == 'by_exception_only'

    # -- forbidden --
    @pytest.mark.parametrize(
        'spdx_id',
        [
            'AGPL-1.0-only',
            'AGPL-3.0-only',
            'AGPL-3.0-or-later',
            'CC-BY-NC-1.0',
            'CC-BY-NC-2.0',
            'CC-BY-NC-2.5',
            'CC-BY-NC-3.0',
            'CC-BY-NC-4.0',
            'CC-BY-NC-ND-1.0',
            'CC-BY-NC-ND-2.0',
            'CC-BY-NC-ND-2.5',
            'CC-BY-NC-ND-3.0',
            'CC-BY-NC-ND-4.0',
            'CC-BY-NC-SA-1.0',
            'CC-BY-NC-SA-2.0',
            'CC-BY-NC-SA-2.5',
            'CC-BY-NC-SA-3.0',
            'CC-BY-NC-SA-4.0',
            'Commons-Clause',
            'Facebook-2-Clause',
            'Facebook-3-Clause',
            'Facebook-Examples',
            'WTFPL',
        ],
    )
    def test_forbidden_licenses(self, graph: LicenseGraph, spdx_id: str) -> None:
        """Test forbidden licenses."""
        assert graph.known(spdx_id), f'{spdx_id} not in graph'
        assert graph.google_category(spdx_id) == 'forbidden'

    def test_total_license_count(self, graph: LicenseGraph) -> None:
        """We should have at least 130 licenses (all Google classifier + extras)."""
        assert len(graph.nodes) >= 130


# ── Patent clause queries ────────────────────────────────────────────


class TestPatentClauses:
    """Verify patent_grant / patent_retaliation flags from licenses.toml."""

    def test_patent_grant_includes_expected(self, graph: LicenseGraph) -> None:
        """Test patent grant includes expected."""
        grant = graph.patent_grant_licenses()
        for spdx_id in ('Apache-2.0', 'MPL-2.0', 'EPL-1.0', 'EPL-2.0', 'CDDL-1.0', 'CDDL-1.1', 'CPL-1.0'):
            assert spdx_id in grant, f'{spdx_id} should have patent_grant=true'

    def test_patent_retaliation_includes_expected(self, graph: LicenseGraph) -> None:
        """Test patent retaliation includes expected."""
        retaliation = graph.patent_retaliation_licenses()
        for spdx_id in ('Apache-2.0', 'MPL-2.0', 'EPL-1.0', 'EPL-2.0', 'CPL-1.0'):
            assert spdx_id in retaliation, f'{spdx_id} should have patent_retaliation=true'

    def test_mit_has_no_patent_clauses(self, graph: LicenseGraph) -> None:
        """Test mit has no patent clauses."""
        assert 'MIT' not in graph.patent_grant_licenses()
        assert 'MIT' not in graph.patent_retaliation_licenses()

    def test_bsd3_has_no_patent_clauses(self, graph: LicenseGraph) -> None:
        """Test bsd3 has no patent clauses."""
        assert 'BSD-3-Clause' not in graph.patent_grant_licenses()
        assert 'BSD-3-Clause' not in graph.patent_retaliation_licenses()

    def test_cddl_grant_only(self, graph: LicenseGraph) -> None:
        """CDDL has patent grant but no retaliation clause."""
        assert 'CDDL-1.0' in graph.patent_grant_licenses()
        assert 'CDDL-1.0' not in graph.patent_retaliation_licenses()
        assert 'CDDL-1.1' in graph.patent_grant_licenses()
        assert 'CDDL-1.1' not in graph.patent_retaliation_licenses()

    def test_license_info_fields(self, graph: LicenseGraph) -> None:
        """LicenseInfo dataclass exposes the boolean fields."""
        apache = graph.nodes['Apache-2.0']
        assert apache.patent_grant is True
        assert apache.patent_retaliation is True

        mit = graph.nodes['MIT']
        assert mit.patent_grant is False
        assert mit.patent_retaliation is False
