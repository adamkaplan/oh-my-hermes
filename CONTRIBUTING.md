# Contributing to Oh My Hermes

## Local Development Setup

For active development, symlink the repo into `~/.hermes/` so edits go live
immediately without copy/sync drift:

```bash
mkdir -p ~/.hermes/plugins
ln -s "$PWD/plugins/omh" ~/.hermes/plugins/omh
ln -s "$PWD/plugins/omh/skills" ~/.hermes/skills/omh
```

Verify:

```bash
ls -la ~/.hermes/plugins/omh ~/.hermes/skills/omh
```

Then restart Hermes to load the plugin's tools and hooks. Skills are
discovered each session — no restart needed for skill-only edits.

### Requirements

- Hermes Agent v0.7.0+
- Python 3.10+ with `pyyaml` available in the Hermes venv
  (verify: `cd ~/.hermes/hermes-agent && uv run python -c "import yaml"`)

### Uninstall

```bash
rm ~/.hermes/plugins/omh ~/.hermes/skills/omh
```

(Symlinks only — your repo is untouched.)

## Testing

Plugin tests live in `plugins/omh/tests/`. Run from the repo root:

```bash
cd plugins/omh && python -m pytest tests/
```

## Style

- Skills follow Hermes SKILL.md format (YAML frontmatter + markdown body)
- Plugin code targets Python 3.10+
- Keep skills standalone-capable; plugin features should enhance, not gate
