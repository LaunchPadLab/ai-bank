# TDD Refactoring Domain Patterns

## Refactoring Philosophy

```
┌──────────────────────────────────────────────────────────────┐
│  1. RED        │  Write a failing test                       │
├──────────────────────────────────────────────────────────────┤
│  2. GREEN      │  Write minimum code to pass                 │
├──────────────────────────────────────────────────────────────┤
│  3. REFACTOR   │  Improve code without breaking tests       │ ← YOU ARE HERE
└──────────────────────────────────────────────────────────────┘
```

### Golden Rules

1. **Tests must be green before starting** — never refactor failing code
2. **One change at a time** — small, incremental improvements
3. **Run tests after each change** — verify behavior is preserved
4. **Stop if tests fail** — revert and understand why
5. **Behavior must not change** — refactoring is structure, not functionality
6. **Improve readability** — code should be easier to understand after refactoring

### What is Refactoring?

**✅ Refactoring IS:**
- Extracting methods
- Renaming variables/methods for clarity
- Removing duplication
- Simplifying conditionals
- Improving structure
- Reducing complexity
- Following SOLID principles

**❌ Refactoring IS NOT:**
- Adding new features
- Changing behavior
- Fixing bugs (that changes behavior)
- Optimizing performance (unless proven bottleneck)
- Modifying tests to make them pass

## Refactoring Workflow

### Step 1: Verify Tests Pass

**CRITICAL:** Always start with green tests.

```bash
bin/rails test
```

If any tests fail:
- ❌ **STOP** — don't refactor failing code
- ✅ Fix tests first or ask for help

### Step 2: Identify Refactoring Opportunities

Use analysis tools and code review:
```bash
bundle exec flog app/ | head -20   # Find complex methods
bundle exec flay app/              # Find duplicated code
bundle exec rubocop                # Check style issues
```

Look for these code smells:
- Long methods (> 10 lines)
- Deeply nested conditionals (> 3 levels)
- Duplicated code blocks
- Unclear variable names
- Complex boolean logic
- Violations of SOLID principles

### Step 3: Make ONE Small Change

Pick the simplest refactoring first. Examples:
- Extract one method
- Rename one variable
- Remove one duplication
- Simplify one conditional

### Step 4: Run Tests Immediately

```bash
bin/rails test
```

**If tests pass (green ✅):**
- Continue to next refactoring
- Commit the change

**If tests fail (red ❌):**
- Revert the change immediately
- Analyze why it failed
- Try a smaller change

### Step 5: Repeat Until Code is Clean

Continue the cycle: refactor → test → refactor → test

### Step 6: Final Verification

```bash
bin/rails test              # All tests
bin/rails test:system       # System tests
bundle exec rubocop -a      # Code style
bin/brakeman                # Security
bundle exec flog app/ | head -20  # Complexity check
```

## Code Smell Detection

### Indicators to Look For

| Code Smell | Threshold | Action |
|---|---|---|
| Long method | > 10 lines | Extract Method |
| Deep nesting | > 3 levels | Guard Clauses, Decompose Conditional |
| Duplicated code | 2+ occurrences | DRY / Extract shared method |
| Long parameter list | > 3 params | Introduce Parameter Object |
| Magic numbers | Any literal | Named Constants |
| Fat model | > 100 lines | Extract Service |
| Case/when branching | 3+ branches | Polymorphism |
| Unclear naming | Any | Rename for clarity |

### Analysis Commands

```bash
bundle exec flog app/              # Identify complex methods (score > 20 = concern)
bundle exec flay app/              # Find duplicated code
bundle exec rubocop                # Style and convention violations
```

## Refactoring Checklist

### Before starting:
- [ ] All tests are passing (green ✅)
- [ ] You understand the code you're refactoring
- [ ] You have identified specific refactoring goals

### During refactoring:
- [ ] Make one small change at a time
- [ ] Run tests after each change
- [ ] Keep behavior exactly the same
- [ ] Improve readability and structure
- [ ] Follow SOLID principles
- [ ] Remove duplication
- [ ] Simplify complex logic

### After refactoring:
- [ ] All tests still pass (green ✅)
- [ ] Code is more readable
- [ ] Code is better structured
- [ ] Complexity is reduced
- [ ] No new RuboCop offenses
- [ ] No new Brakeman warnings
- [ ] Commit the changes

## When to Stop Refactoring

**Stop immediately if:**
- ❌ Any test fails
- ❌ Behavior changes
- ❌ You're adding new features (not refactoring)
- ❌ You're fixing bugs (not refactoring)
- ❌ Tests need modification to pass (red flag!)

**You can stop when:**
- ✅ Code follows SOLID principles
- ✅ Methods are short and focused
- ✅ Names are clear and descriptive
- ✅ Duplication is eliminated
- ✅ Complexity is reduced
- ✅ Code is easy to understand
- ✅ All tests pass

## Common Refactoring Patterns

Eight proven patterns with full before/after examples are in the parent [SKILL.md](../SKILL.md):

1. **Extract Method** — decompose long methods into focused private helpers
2. **Replace Conditional with Polymorphism** — eliminate `case` branching with strategy classes
3. **Introduce Parameter Object** — wrap long parameter lists in a value object
4. **Replace Magic Numbers with Named Constants** — improve readability with descriptive constants
5. **Decompose Conditional** — name complex boolean expressions as predicate methods
6. **Remove Duplication (DRY)** — extract repeated logic into shared private methods
7. **Simplify Guard Clauses** — flatten nested conditionals with early returns
8. **Extract Service from Fat Model** — move business logic out of ActiveRecord models
