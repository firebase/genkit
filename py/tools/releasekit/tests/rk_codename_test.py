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

"""Tests for releasekit codename feature: schemas, config, prompts, resolve."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from releasekit._wordfilter import WordFilter
from releasekit.ai import resolve_ai_config
from releasekit.codename import (
    SAFE_BUILTIN_THEMES,
    _is_safe_codename,
    _load_previous_codenames,
    _save_codename,
)
from releasekit.config import AiConfig, AiFeaturesConfig, _parse_ai
from releasekit.errors import ReleaseKitError
from releasekit.prompts import CODENAME_SYSTEM_PROMPT, PROMPTS_DIR, build_codename_prompt
from releasekit.schemas_ai import ReleaseCodename


class TestReleaseCodenameSchema:
    """Tests for the ReleaseCodename Pydantic model."""

    def test_defaults(self) -> None:
        """Test defaults."""
        cn = ReleaseCodename()
        assert cn.codename == ''
        assert cn.theme == ''
        assert cn.tagline == ''

    def test_full_codename(self) -> None:
        """Test full codename."""
        cn = ReleaseCodename(
            codename='Denali',
            theme='mountains',
            tagline='Denali — towering performance improvements across all providers',
        )
        assert cn.codename == 'Denali'
        assert cn.theme == 'mountains'
        assert 'towering' in cn.tagline

    def test_json_roundtrip(self) -> None:
        """Test json roundtrip."""
        cn = ReleaseCodename(codename='Andromeda', theme='space', tagline='Reaching new galaxies.')
        data = json.loads(cn.model_dump_json())
        restored = ReleaseCodename.model_validate(data)
        assert restored == cn

    def test_json_schema_export(self) -> None:
        """Test json schema export."""
        schema = ReleaseCodename.model_json_schema()
        assert 'codename' in schema['properties']
        assert 'theme' in schema['properties']
        assert 'tagline' in schema['properties']

    def test_partial_output(self) -> None:
        """Test partial output."""
        data = {'codename': 'Zephyr'}
        cn = ReleaseCodename.model_validate(data)
        assert cn.codename == 'Zephyr'
        assert cn.theme == ''


class TestCodenameConfig:
    """Tests for codename_theme in AiConfig."""

    def test_default_theme(self) -> None:
        """Test default theme."""
        cfg = AiConfig()
        assert cfg.codename_theme == 'mountains'

    def test_custom_theme(self) -> None:
        """Test custom theme."""
        cfg = _parse_ai({'codename_theme': 'deep sea creatures'})
        assert cfg.codename_theme == 'deep sea creatures'

    def test_empty_theme_disables(self) -> None:
        """Test empty theme disables."""
        cfg = _parse_ai({'codename_theme': ''})
        assert cfg.codename_theme == ''

    def test_invalid_theme_type(self) -> None:
        """Test invalid theme type."""
        with pytest.raises(ReleaseKitError, match='codename_theme must be a string'):
            _parse_ai({'codename_theme': 42})

    def test_codename_feature_default_on(self) -> None:
        """Test codename feature default on."""
        cfg = AiFeaturesConfig()
        assert cfg.codename is True

    def test_codename_feature_disabled(self) -> None:
        """Test codename feature disabled."""
        cfg = _parse_ai({'features': {'codename': False}})
        assert cfg.features.codename is False


class TestCodenamePrompt:
    """Tests for build_codename_prompt()."""

    def test_basic_prompt(self) -> None:
        """Test basic prompt."""
        prompt = build_codename_prompt(theme='mountains')
        assert 'mountains' in prompt
        assert 'codename' in prompt.lower()

    def test_with_version(self) -> None:
        """Test with version."""
        prompt = build_codename_prompt(theme='animals', version='0.6.0')
        assert '0.6.0' in prompt

    def test_with_highlights(self) -> None:
        """Test with highlights."""
        prompt = build_codename_prompt(
            theme='space',
            highlights=['New plugin', 'Faster streaming'],
        )
        assert 'New plugin' in prompt
        assert 'Faster streaming' in prompt

    def test_with_previous_codenames(self) -> None:
        """Test with previous codenames."""
        prompt = build_codename_prompt(
            theme='gems',
            previous_codenames=['Topaz', 'Sapphire'],
        )
        assert 'Topaz' in prompt
        assert 'Sapphire' in prompt
        assert 'NOT reuse' in prompt

    def test_system_prompt_not_empty(self) -> None:
        """Test system prompt not empty."""
        assert len(CODENAME_SYSTEM_PROMPT) > 0
        assert 'codename' in CODENAME_SYSTEM_PROMPT.lower()

    def test_system_prompt_has_safety_rules(self) -> None:
        """Test system prompt has safety rules."""
        assert 'safe for all audiences' in CODENAME_SYSTEM_PROMPT
        assert 'NO violent' in CODENAME_SYSTEM_PROMPT
        assert 'Google product launch' in CODENAME_SYSTEM_PROMPT


class TestCodenameResolve:
    """Tests for codename_theme in resolve_ai_config()."""

    def test_no_override(self) -> None:
        """Test no override."""
        base = AiConfig(codename_theme='mountains')
        result = resolve_ai_config(base)
        assert result.codename_theme == 'mountains'

    def test_cli_override(self) -> None:
        """Test cli override."""
        base = AiConfig(codename_theme='mountains')
        result = resolve_ai_config(base, codename_theme='animals')
        assert result.codename_theme == 'animals'

    def test_cli_empty_string_override(self) -> None:
        """--codename-theme '' should disable codenames."""
        base = AiConfig(codename_theme='mountains')
        result = resolve_ai_config(base, codename_theme='')
        assert result.codename_theme == ''

    def test_cli_none_preserves_base(self) -> None:
        """Test cli none preserves base."""
        base = AiConfig(codename_theme='space')
        result = resolve_ai_config(base, codename_theme=None)
        assert result.codename_theme == 'space'


class TestCodenameHistory:
    """Tests for codename history file operations."""

    def test_load_empty(self, tmp_path: Path) -> None:
        """Test load empty."""
        assert _load_previous_codenames(tmp_path) == []

    def test_save_and_load(self, tmp_path: Path) -> None:
        """Test save and load."""
        _save_codename(tmp_path, 'Denali')
        _save_codename(tmp_path, 'Rainier')
        names = _load_previous_codenames(tmp_path)
        assert names == ['Denali', 'Rainier']

    def test_load_strips_whitespace(self, tmp_path: Path) -> None:
        """Test load strips whitespace."""
        path = tmp_path / '.releasekit' / 'codenames.txt'
        path.parent.mkdir(parents=True)
        path.write_text('  Denali  \n\n  Rainier \n', encoding='utf-8')
        names = _load_previous_codenames(tmp_path)
        assert names == ['Denali', 'Rainier']


class TestSafeBuiltinThemes:
    """Tests for SAFE_BUILTIN_THEMES."""

    def test_contains_default_theme(self) -> None:
        """Test contains default theme."""
        assert 'mountains' in SAFE_BUILTIN_THEMES

    def test_contains_documented_themes(self) -> None:
        """Test contains documented themes."""
        for theme in ('animals', 'space', 'mythology', 'gems', 'weather', 'cities'):
            assert theme in SAFE_BUILTIN_THEMES, f'{theme} missing'

    def test_is_frozenset(self) -> None:
        """Test is frozenset."""
        assert isinstance(SAFE_BUILTIN_THEMES, frozenset)

    def test_all_lowercase(self) -> None:
        """Test all lowercase."""
        for theme in SAFE_BUILTIN_THEMES:
            assert theme == theme.lower(), f'{theme} is not lowercase'


class TestIsSafeCodename:
    """Tests for _is_safe_codename() post-generation filter.

    Uses a patched WordFilter loaded with neutral test words (foo, bar,
    quux*) so the tests exercise the filter mechanics without requiring
    explicit content in the source.  The actual blocked-word list is
    maintained and reviewed separately.
    """

    @pytest.fixture(autouse=True)
    def _patch_filter(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Patch filter."""
        test_filter = WordFilter.from_lines(['foo', 'bar', 'quux*'])
        monkeypatch.setattr(
            'releasekit._wordfilter._default_filter',
            test_filter,
        )

    def test_safe_names_pass(self) -> None:
        """Test safe names pass."""
        for name in ('Denali', 'Rainier', 'Andromeda', 'Topaz', 'Zephyr', 'Bold Bison'):
            assert _is_safe_codename(name), f'{name} should be safe'

    def test_empty_string_fails(self) -> None:
        """Test empty string fails."""
        assert not _is_safe_codename('')

    def test_whitespace_only_fails(self) -> None:
        """Test whitespace only fails."""
        assert not _is_safe_codename('   ')

    def test_blocked_exact_words_fail(self) -> None:
        """Test blocked exact words fail."""
        for word in ('foo', 'Foo', 'FOO', 'bar', 'Bar', 'BAR'):
            assert not _is_safe_codename(word), f'{word} should be blocked'

    def test_blocked_words_in_phrase_fail(self) -> None:
        """Test blocked words in phrase fail."""
        assert not _is_safe_codename('Operation Foo Storm')
        assert not _is_safe_codename('The Bar Star')

    def test_blocked_prefix_words_fail(self) -> None:
        """Test blocked prefix words fail."""
        assert not _is_safe_codename('quuxing awesome')
        assert not _is_safe_codename('quuxed release')

    def test_safe_words_containing_blocked_substrings_pass(self) -> None:
        # Word-boundary patterns should not match substrings inside words.
        """Test safe words containing blocked substrings pass."""
        assert _is_safe_codename('Foobar')  # 'foo' not at word boundary (followed by 'b')
        assert _is_safe_codename('Rebar')  # 'bar' not at word boundary (preceded by 're')
        assert _is_safe_codename('Embargo')  # 'bar' embedded

    def test_standalone_blocked_word_in_multi_word(self) -> None:
        # Standalone blocked words within a multi-word phrase ARE caught.
        """Test standalone blocked word in multi word."""
        assert not _is_safe_codename('Project Foo')
        assert not _is_safe_codename('Bar Fire')


class TestPromptFiles:
    """Tests for .prompt file existence and content."""

    def test_prompts_dir_exists(self) -> None:
        """Test prompts dir exists."""
        assert PROMPTS_DIR.is_dir()

    def test_summarize_prompt_exists(self) -> None:
        """Test summarize prompt exists."""
        assert (PROMPTS_DIR / 'summarize.prompt').is_file()

    def test_codename_prompt_exists(self) -> None:
        """Test codename prompt exists."""
        assert (PROMPTS_DIR / 'codename.prompt').is_file()

    def test_codename_prompt_has_safety_rules(self) -> None:
        """Test codename prompt has safety rules."""
        content = (PROMPTS_DIR / 'codename.prompt').read_text(encoding='utf-8')
        assert 'safe for all audiences' in content
        assert 'NO violent' in content
        assert 'Google product launch' in content

    def test_codename_prompt_has_handlebars_template(self) -> None:
        """Test codename prompt has handlebars template."""
        content = (PROMPTS_DIR / 'codename.prompt').read_text(encoding='utf-8')
        assert '{{theme}}' in content
        assert '{{#if version}}' in content
        assert '{{#if highlights}}' in content
        assert '{{#if previous_codenames}}' in content

    def test_summarize_prompt_has_handlebars_template(self) -> None:
        """Test summarize prompt has handlebars template."""
        content = (PROMPTS_DIR / 'summarize.prompt').read_text(encoding='utf-8')
        assert '{{changelog_text}}' in content
        assert '{{#if package_count}}' in content
