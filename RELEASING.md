# Releasing evo-skillopt

Short procedure. The release workflow at
[`.github/workflows/release.yml`](./.github/workflows/release.yml)
does the heavy lifting; this file documents what a maintainer does
by hand.

## One-time setup (only the first time)

### 1. Reserve the PyPI name

First commit must end up on PyPI before anyone else can claim the
name. You can either upload a `0.0.0` placeholder with an API token
once, or ship `0.1.0` straight through the OIDC flow below.

### 2. Configure Trusted Publishing on PyPI

Trusted Publishing lets GitHub Actions push to PyPI with no stored
token.

1. Log in to PyPI → <https://pypi.org/manage/account/publishing/>.
2. Add a **Pending Publisher** (if the project doesn't exist yet) or
   a **Publisher** (if it does):
   - **PyPI project name:** `evo-skillopt`
   - **Owner:** `dnzengou`
   - **Repository:** `evo-skillopt`
   - **Workflow name:** `release.yml`
   - **Environment:** `pypi`

### 3. Create the GitHub environment

In the GitHub repo → **Settings → Environments → New environment**:
- **Name:** `pypi`
- **Deployment branches:** limit to tags matching `v*.*.*` (optional
  but recommended).
- No secrets needed.

## Every release

Pick a version (`X.Y.Z`), then:

```bash
# 1. Bump version in pyproject.toml
$EDITOR pyproject.toml   # change [project].version to X.Y.Z

# 2. Fill in the CHANGELOG — move items from [Unreleased] to [X.Y.Z]
$EDITOR CHANGELOG.md

# 3. Tick any newly shipped capabilities in EvoSkillOpt_Blueprint.md § 5.

# 4. Verify locally
ruff check .
pytest -q
python -m py_compile worker/*.py
python -m build                # confirm sdist + wheel build
python -m twine check dist/*

# 5. Commit, tag, push
git add pyproject.toml CHANGELOG.md EvoSkillOpt_Blueprint.md
git commit -m "release: X.Y.Z"
git tag -a "vX.Y.Z" -m "evo-skillopt X.Y.Z"
git push origin main
git push origin "vX.Y.Z"
```

The workflow then:

1. Builds sdist + wheel with the `build` module.
2. `twine check --strict`s them.
3. Publishes to PyPI via OIDC (no API token).
4. Creates a GitHub Release at the tag with the dist files attached
   and the matching CHANGELOG section as release notes.

## After release

- Verify: `pip install evo-skillopt==X.Y.Z` in a fresh venv.
- Check the release page: <https://github.com/dnzengou/evo-skillopt/releases>.
- Check PyPI: <https://pypi.org/project/evo-skillopt/>.
- Announce on your usual channels (see [`GTM.md`](./GTM.md) § 4.2).

## Hotfixes / yanked releases

- To yank a bad release from PyPI (keeps the version number reserved
  but marks it as yanked), use the PyPI web UI or `twine` CLI.
- To fix forward, cut the next patch release (`X.Y.Z+1`) with the
  same procedure.
- Never delete tags on `main` — a yanked PyPI version + a new tag
  is always safer than rewriting history.

## Manual run (no tag yet)

Use **Actions → release → Run workflow** on GitHub. It builds and
uploads a dist artifact but **does not** publish to PyPI or create a
GitHub Release — those only fire on a `v*.*.*` tag push. Useful for
pre-release smoke tests.

## Related docs

- [`CONTRIBUTING.md`](./CONTRIBUTING.md) — PR process
- [`CHANGELOG.md`](./CHANGELOG.md) — the source of truth for release notes
- [`EvoSkillOpt_Blueprint.md`](./EvoSkillOpt_Blueprint.md) — capability
  tick-off and roadmap
