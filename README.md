# hookrunner

> Lightweight Git hook manager that supports shareable hook configs across teams.

---

## Installation

```bash
pip install hookrunner
```

Or with pipx for isolated installs:

```bash
pipx install hookrunner
```

---

## Usage

Initialize hookrunner in your repository:

```bash
hookrunner init
```

Define your hooks in a `hooks.yaml` file at the root of your project:

```yaml
hooks:
  pre-commit:
    - run: ruff check .
    - run: pytest tests/ -q
  commit-msg:
    - run: hookrunner validate-msg
```

Install the hooks into `.git/hooks`:

```bash
hookrunner install
```

Share the `hooks.yaml` with your team by committing it to version control. Anyone who clones the repo can run `hookrunner install` to get the same hooks configured instantly.

To run a specific hook manually:

```bash
hookrunner run pre-commit
```

To uninstall all managed hooks:

```bash
hookrunner uninstall
```

---

## Configuration

Hook configs can also be loaded from a remote URL, allowing centralized hook management across multiple repositories:

```bash
hookrunner init --config https://your-org.example.com/hooks.yaml
```

---

## License

This project is licensed under the [MIT License](LICENSE).