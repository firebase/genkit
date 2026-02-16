# Supported Commit Message Formats

ReleaseKit uses structured commit messages to automate version bumping and
changelog generation.  Two built-in parsers ship out of the box:

| Parser | Module | Accepts any type? |
|--------|--------|-------------------|
| **Conventional Commits v1.0.0** | `commit_parsing.ConventionalCommitParser` | Yes |
| **Angular Commit Convention** | `commit_parsing.AngularCommitParser` | No (strict allowlist) |

Both parsers share the same subject-line syntax:

```
type(scope)!: description
```

The differences are in which `type` values are accepted and how unknown
types are handled.

---

## Side-by-Side Comparison

### Accepted vs rejected types

The key difference: Conventional Commits accepts **any** word as a type,
while Angular only accepts its fixed allowlist.

<table>
<tr><th>Commit message</th><th>Conventional Commits</th><th>Angular</th></tr>
<tr>
  <td><code>feat: add streaming</code></td>
  <td>✅ MINOR</td>
  <td>✅ MINOR</td>
</tr>
<tr>
  <td><code>fix: null pointer</code></td>
  <td>✅ PATCH</td>
  <td>✅ PATCH</td>
</tr>
<tr>
  <td><code>perf: optimize loop</code></td>
  <td>✅ PATCH</td>
  <td>✅ PATCH</td>
</tr>
<tr>
  <td><code>docs: update README</code></td>
  <td>✅ NONE</td>
  <td>✅ NONE</td>
</tr>
<tr>
  <td><code>refactor: extract helper</code></td>
  <td>✅ NONE</td>
  <td>✅ NONE</td>
</tr>
<tr>
  <td><code>chore: update deps</code></td>
  <td>✅ NONE</td>
  <td>❌ Rejected</td>
</tr>
<tr>
  <td><code>release: v1.0.0</code></td>
  <td>✅ NONE</td>
  <td>❌ Rejected</td>
</tr>
<tr>
  <td><code>wip: work in progress</code></td>
  <td>✅ NONE</td>
  <td>❌ Rejected</td>
</tr>
</table>

### Breaking changes (identical behaviour)

Both parsers handle breaking changes identically:

<table>
<tr><th>Format</th><th>Example</th><th>Both parsers</th></tr>
<tr>
  <td><code>!</code> indicator</td>
  <td><code>feat!: redesign API</code></td>
  <td>✅ MAJOR</td>
</tr>
<tr>
  <td><code>!</code> with scope</td>
  <td><code>feat(api)!: new endpoints</code></td>
  <td>✅ MAJOR</td>
</tr>
<tr>
  <td>Footer</td>
  <td><code>feat: new API\n\nBREAKING CHANGE: removed v1</code></td>
  <td>✅ MAJOR</td>
</tr>
<tr>
  <td>Hyphen footer</td>
  <td><code>feat: new API\n\nBREAKING-CHANGE: removed v1</code></td>
  <td>✅ MAJOR</td>
</tr>
</table>

### Revert commits (identical behaviour)

<table>
<tr><th>Format</th><th>Example</th><th>Both parsers</th></tr>
<tr>
  <td>GitHub default</td>
  <td><code>Revert "feat: add streaming"</code></td>
  <td>✅ revert (reverted_bump=MINOR)</td>
</tr>
<tr>
  <td>Conventional</td>
  <td><code>revert: feat: add streaming</code></td>
  <td>✅ revert (reverted_bump=MINOR)</td>
</tr>
</table>

### Full multi-line message (identical behaviour)

Both parsers support the full Conventional Commits message structure:

```
fix: prevent racing of requests

Introduce a request id and a reference to latest request. Dismiss
incoming responses other than from latest request.

Remove timeouts which were used to mitigate the racing issue but are
obsolete now.

Reviewed-by: Z
Refs: #123
```

Parsed result (both parsers):

| Field | Value |
|-------|-------|
| `type` | `fix` |
| `description` | `prevent racing of requests` |
| `body` | `Introduce a request id...obsolete now.` |
| `footers` | `[("Reviewed-by", "Z"), ("Refs", "#123")]` |
| `bump` | PATCH |

---

## Conventional Commits v1.0.0

**Spec**: <https://www.conventionalcommits.org/en/v1.0.0/>

### Subject line

```
<type>[(scope)][!]: <description>
```

- **type** — any word (case-insensitive, normalised to lowercase).
- **scope** — optional noun in parentheses, e.g. `(auth)`.
- **`!`** — optional breaking change indicator.
- **description** — short summary (required, after `: `).

### Body (optional)

Free-form text separated from the subject by one blank line.  May consist
of multiple paragraphs.

### Footers (optional)

Git trailer lines at the end of the message.  Two separator styles:

```
token: value         # colon separator
token #value         # hash separator (e.g. "Fixes #42")
```

Footer tokens use `-` in place of spaces, except the special token
`BREAKING CHANGE` (with a literal space).

### Version bump rules

| Condition | Bump |
|-----------|------|
| Breaking change (`!` or footer) | **MAJOR** |
| `feat` type | **MINOR** |
| `fix` or `perf` type | **PATCH** |
| Any other type | NONE |

---

## Angular Commit Convention

**Spec**: <https://github.com/angular/angular/blob/main/CONTRIBUTING.md#commit>

Same syntax as Conventional Commits, but with a strict type allowlist.

### Allowed types

| Type | Purpose | Bump |
|------|---------|------|
| `feat` | New feature | **MINOR** |
| `fix` | Bug fix | **PATCH** |
| `perf` | Performance improvement | **PATCH** |
| `build` | Build system / dependencies | NONE |
| `ci` | CI configuration | NONE |
| `docs` | Documentation only | NONE |
| `refactor` | Code refactoring (no feature/fix) | NONE |
| `style` | Formatting, whitespace | NONE |
| `test` | Adding / fixing tests | NONE |

Types not in this list (e.g. `chore`, `release`, `wip`) are rejected.

### Custom type allowlists

Use the `allowed_types` parameter to extend or replace the default set:

```python
from releasekit.commit_parsing import AngularCommitParser, ANGULAR_TYPES

parser = AngularCommitParser(
    allowed_types=frozenset({*ANGULAR_TYPES, 'chore'}),
)
```

---

## Choosing a parser

| Use case | Parser |
|----------|--------|
| Accept any commit type (maximum flexibility) | `ConventionalCommitParser` |
| Enforce Angular's type discipline | `AngularCommitParser` |
| Custom format entirely | Implement the `CommitParser` protocol |

### CommitParser protocol

Any class with a `.parse(message, sha='') -> ParsedCommit | None` method
satisfies the protocol and can be used as a drop-in replacement:

```python
from releasekit.commit_parsing import CommitParser, ParsedCommit

class MyParser:
    def parse(self, message: str, sha: str = '') -> ParsedCommit | None:
        ...  # custom parsing logic
```

---

## ParsedCommit fields

| Field | Type | Description |
|-------|------|-------------|
| `sha` | `str` | Full commit SHA |
| `type` | `str` | Commit type (normalised to lowercase) |
| `scope` | `str` | Optional scope (empty string if absent) |
| `description` | `str` | Subject line after `type:` |
| `body` | `str` | Free-form body text (empty if absent) |
| `footers` | `tuple[tuple[str, str], ...]` | Parsed git trailers as `(token, value)` |
| `breaking` | `bool` | Whether this is a breaking change |
| `breaking_description` | `str` | Reason for breaking (from footer or description) |
| `bump` | `BumpType` | Computed semver bump |
| `raw` | `str` | Original unparsed message |
| `is_revert` | `bool` | Whether this reverts another commit |
| `reverted_bump` | `BumpType` | Bump of the reverted commit |
