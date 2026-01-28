# Phase 2 Generic Action - Manual IDE Test

## Automated Verification: PASSED ✅

```
$ uv run pyright --project samples/typing-manual-test/pyrightconfig.json

Type of "result" is "UserOutput"                    ✅ Correct type inferred
Cannot access attribute "nonexistent" for UserOutput ✅ Typo caught
Argument "str" cannot be assigned to "UserInput"    ✅ Wrong input caught
```

## Your Manual Checks

Open `main.py` in Cursor/VS Code and verify:

| # | Test | How | Expected |
|---|------|-----|----------|
| 1 | **Autocomplete** | Put cursor after `result.` on line 44, press `Ctrl+Space` | Shows `greeting`, `birth_year` |
| 2 | **Hover type** | Hover over `result` on line 40 | Tooltip shows `UserOutput` |
| 3 | **Typo error** | Uncomment line 52 (`result.nonexistent`) | Red squiggly appears |
| 4 | **Wrong input** | Uncomment line 59 (`greet_user("wrong")`) | Red squiggly appears |

## Cleanup

Delete this folder when done:
```bash
rm -rf py/samples/typing-manual-test
```
