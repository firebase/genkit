# Copyright 2025 Google LLC
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

"""Tests for deprecation helpers."""

import sys
import unittest
import warnings

import pytest

if sys.version_info < (3, 11):
    from strenum import StrEnum
else:
    from enum import StrEnum

from genkit.lang.deprecations import (
    DeprecationInfo,
    DeprecationStatus,
    deprecated_enum_metafactory,
)

TEST_DEPRECATED_MODELS = {
    'GEMINI_1_0_PRO': DeprecationInfo(recommendation='GEMINI_2_0_PRO', status=DeprecationStatus.LEGACY),
    'GEMINI_1_5_PRO': DeprecationInfo(recommendation='GEMINI_2_0_PRO', status=DeprecationStatus.DEPRECATED),
    'GEMINI_1_5_FLASH': DeprecationInfo(recommendation='GEMINI_2_0_FLASH', status=DeprecationStatus.DEPRECATED),
    'GEMINI_1_5_FLASH_8B': DeprecationInfo(recommendation=None, status=DeprecationStatus.DEPRECATED),
}


class GeminiVersionTest(StrEnum, metaclass=deprecated_enum_metafactory(TEST_DEPRECATED_MODELS)):
    """Test Gemini models enum."""

    GEMINI_1_0_PRO = 'gemini-1.0-pro'
    GEMINI_1_5_PRO = 'gemini-1.5-pro'
    GEMINI_1_5_FLASH = 'gemini-1.5-flash'
    GEMINI_1_5_FLASH_8B = 'gemini-1.5-flash-8b'
    GEMINI_2_0_FLASH = 'gemini-2.0-flash'
    GEMINI_2_0_PRO = 'gemini-2.0-pro'  # Added for recommendation


class TestDeprecatedEnum(unittest.TestCase):
    """Test deprecated enum members."""

    def test_legacy_member_warning(self):
        """Verify warning for legacy member with recommendation."""
        expected_regex = (
            r'GeminiVersionTest\.GEMINI_1_0_PRO is legacy; '
            r'use GeminiVersionTest\.GEMINI_2_0_PRO instead'
        )
        warnings.simplefilter('always', DeprecationWarning)
        try:
            with self.assertWarnsRegex(DeprecationWarning, expected_regex):
                member = GeminiVersionTest.GEMINI_1_0_PRO
            self.assertEqual(member, GeminiVersionTest.GEMINI_1_0_PRO)
            self.assertEqual(member.value, 'gemini-1.0-pro')
        finally:
            warnings.simplefilter('default', DeprecationWarning)

    def test_deprecated_member_with_recommendation_warning(self):
        """Verify warning for deprecated member with recommendation."""
        expected_regex = (
            r'GeminiVersionTest\.GEMINI_1_5_PRO is deprecated; '
            r'use GeminiVersionTest\.GEMINI_2_0_PRO instead'
        )
        warnings.simplefilter('always', DeprecationWarning)
        try:
            with self.assertWarnsRegex(DeprecationWarning, expected_regex):
                member = GeminiVersionTest.GEMINI_1_5_PRO
            self.assertEqual(member, GeminiVersionTest.GEMINI_1_5_PRO)
            self.assertEqual(member.value, 'gemini-1.5-pro')
        finally:
            warnings.simplefilter('default', DeprecationWarning)

    def test_deprecated_member_without_recommendation_warning(self):
        """Verify warning for deprecated member without recommendation."""
        expected_regex = r'GeminiVersionTest\.GEMINI_1_5_FLASH_8B is deprecated'
        warnings.simplefilter('always', DeprecationWarning)
        try:
            with self.assertWarnsRegex(DeprecationWarning, expected_regex) as cm:
                member = GeminiVersionTest.GEMINI_1_5_FLASH_8B
                self.assertTrue(
                    hasattr(cm, 'warnings') and cm.warnings,
                    'Warning was not captured by assertWarnsRegex',
                )
                self.assertNotIn('instead', str(cm.warnings[0].message))
            self.assertEqual(member, GeminiVersionTest.GEMINI_1_5_FLASH_8B)
            self.assertEqual(member.value, 'gemini-1.5-flash-8b')
        finally:
            warnings.simplefilter('default', DeprecationWarning)

    def test_supported_member_no_warning(self):
        """Verify no warning for a supported member."""
        member_to_test = GeminiVersionTest.GEMINI_2_0_FLASH
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            member = getattr(GeminiVersionTest, member_to_test.name)
            self.assertEqual(
                len(w),
                0,
                f'Expected no warnings for {member_to_test.name}, but got {len(w)}: {[warn.message for warn in w]}',
            )
        self.assertEqual(member, member_to_test)
        self.assertEqual(member.value, member_to_test.value)

    def test_recommended_member_no_warning(self):
        """Verify no warning for a member used as a recommendation."""
        member_to_test = GeminiVersionTest.GEMINI_2_0_PRO
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            member = getattr(GeminiVersionTest, member_to_test.name)
            self.assertEqual(
                len(w),
                0,
                f'Expected no warnings for {member_to_test.name}, but got {len(w)}: {[warn.message for warn in w]}',
            )
        self.assertEqual(member, member_to_test)
        self.assertEqual(member.value, member_to_test.value)

    def test_access_via_value_no_warning(self):
        """Verify no warning when accessing members via value lookup."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            member_dep = GeminiVersionTest('gemini-1.5-pro')
            member_leg = GeminiVersionTest('gemini-1.0-pro')
            member_sup = GeminiVersionTest('gemini-2.0-flash')
            self.assertEqual(
                len(w),
                0,
                f'Expected no warnings for value lookup, but got {len(w)}: {[warn.message for warn in w]}',
            )
        self.assertEqual(member_dep, GeminiVersionTest.GEMINI_1_5_PRO)
        self.assertEqual(member_leg, GeminiVersionTest.GEMINI_1_0_PRO)
        self.assertEqual(member_sup, GeminiVersionTest.GEMINI_2_0_FLASH)

    def test_iteration_no_warning(self):
        """Verify no warning when iterating over enum members."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            members = list(GeminiVersionTest)
            self.assertEqual(
                len(w),
                0,
                f'Expected no warnings during iteration, but got {len(w)}: {[warn.message for warn in w]}',
            )
        self.assertEqual(len(members), len(GeminiVersionTest.__members__))
        self.assertIn(GeminiVersionTest.GEMINI_1_5_FLASH_8B, members)
        self.assertIn(GeminiVersionTest.GEMINI_2_0_FLASH, members)


if __name__ == '__main__':
    unittest.main()
