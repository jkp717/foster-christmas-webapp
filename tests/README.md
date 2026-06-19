# Tests

Automated test suite for the Holiday Hope Tree app, using **pytest** against a
throwaway temp-file SQLite database (one per test, auto-deleted).

## Running

From the project root, in the virtualenv that has the app installed:

```bash
pip install -r requirements-dev.txt
pytest
```

Useful variations:

```bash
pytest -v                     # verbose: one line per test
pytest tests/test_archive_cli.py   # a single module
pytest -k archive             # only tests matching "archive"
pytest -x                     # stop at first failure
```

## Layout

| File | Covers |
|------|--------|
| `conftest.py` | Fixtures: `app`, `client`, `db_session`, and `login_admin` / `login_readonly` / `logout` helpers. Seeds reference data from `config.db_defaults`. |
| `factories.py` | `make_parent / make_child / make_sponsor / make_sponsor_request / make_gift` — valid records with keyword overrides. |
| `test_models.py` | child_id auto-assignment, the auto-created gift_fulfillment row, validators, hybrids, SiteSetting formatting. |
| `test_auth.py` | `AdminUser.verify`, roles, login/logout, anonymous gating. |
| `test_security.py` | role-based create/delete permissions, archive read-only enforcement, CSRF, the child IDOR ownership check. |
| `test_public_forms.py` | public page rendering, the child-signup gate, a sponsor submission. |
| `test_admin_views.py` | every live + archive admin list view loads (smoke), data shows up. |
| `test_archive_cli.py` | `run_archive_season()`: copy + wipe, FK remapping, composite-key gift linkage, reference tables untouched, multi-season coexistence. |

## Adding tests later

* **New model** → add a `make_<model>()` to `factories.py`; everything else can build on it.
* **New endpoint** → add a path to the relevant list in `test_admin_views.py` (admin) or a render check in `test_public_forms.py` (public).
* **New archive table** → add its `(Model, View)` pair to the `ARCHIVE_VIEWS` list in `test_security.py` and the path list in `test_admin_views.py`; the parametrized tests pick it up automatically.

## Notes

* The test config disables CSRF and rate limiting so forms can be POSTed
  directly. `test_security.py` spins up its own app with CSRF **on** to verify
  that protection separately.
* The suite calls `run_archive_season()` directly (imported from `cli.py`)
  rather than through the Click command, so it runs against the test database.
