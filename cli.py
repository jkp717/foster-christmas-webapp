from datetime import datetime, timezone
from flask import current_app

from webapp import create_app
from webapp.models import db

from flask.cli import FlaskGroup
import click


# To run in terminal, the following command;
# python cli.py hello [OPTIONS]

@click.group(cls=FlaskGroup, create_app=create_app)
def cli():
    """Management script for the My Flask application."""
    pass


# A simple example command that says hello to a user.
# The @app.cli.command() decorator registers the function as a CLI command.
@cli.command('hello')
@click.option('--name', default='World', help='The name to greet.')
def hello_command(name):
    """Greets the user with a friendly message."""
    click.echo(f"Hello, {name}!")


def get_orm_class_by_tablename(db, tablename: str):
    for mapper in db.Model.registry.mappers:
        if mapper.mapped_table.name == tablename:
            return mapper.class_
    return None


def _copy_columns(src_row, dest_cls, overrides=None):
    """
    Build a dest_cls instance from a source row, copying columns that exist on
    both. `overrides` replaces/sets specific columns (e.g. remapped FKs,
    archive_date). The primary key 'id' is never copied so the archive row gets
    its own fresh id.
    """
    overrides = overrides or {}
    dest_cols = {c.key for c in dest_cls.__table__.columns}
    data = {}
    for col in dest_cols:
        if col == 'id':
            continue
        if col in overrides:
            data[col] = overrides[col]
        elif hasattr(src_row, col):
            data[col] = getattr(src_row, col)
    # Make sure overrides that aren't real columns are ignored, but any override
    # naming a real column is applied even if missing on the source.
    for k, v in overrides.items():
        if k in dest_cols and k != 'id':
            data[k] = v
    return dest_cls(**data)


@cli.command('archive-season')
@click.option('--yes', is_flag=True, default=False,
              help='Skip the confirmation prompt (for non-interactive use).')
def archive_season_command(yes):
    """
    Archive the current season's data, then wipe the live tables for a new
    season.

    Copies child / parent / gift / sponsor / sponsor_request / gift_fulfillment
    rows into their *_archive tables (stamping archive_date), then deletes them
    from the live tables. Reference tables (gender, race, fav_color, shoe_size,
    clothing_size, dhs_office, church) and site_setting are left untouched.

    Foreign keys are remapped: parents and sponsors are archived first and their
    new archive ids are used when archiving children. Gifts and gift_fulfillment
    map to children by the business key child_id (a string), which is preserved.
    """
    # Delegate to the importable core so the same logic can be unit-tested
    # directly against a test app context (without the Click/FlaskGroup wrapper
    # building its own app).
    run_archive_season(skip_confirm=yes, echo=click.echo, confirm=click.confirm)


def run_archive_season(skip_confirm=False, echo=print, confirm=None):
    """
    Core season-archive routine. Returns the number of records archived.

    Parameters let it run both interactively (CLI) and non-interactively
    (tests): `echo` receives progress lines, and `confirm` (if provided and
    skip_confirm is False) is called for the yes/no prompt. Pass skip_confirm=
    True (the test default) to run without prompting.
    """
    from webapp.models import (
        db, Child, ChildArchive, Parent, ParentArchive, Gift, GiftArchive,
        Sponsor, SponsorArchive, SponsorRequest, SponsorRequestArchive,
        GiftFulfillment, GiftFulfillmentArchive,
    )

    counts = {
        'sponsors': Sponsor.query.count(),
        'parents': Parent.query.count(),
        'children': Child.query.count(),
        'gifts': Gift.query.count(),
        'gift_fulfillment': GiftFulfillment.query.count(),
        'sponsor_requests': SponsorRequest.query.count(),
    }
    total = sum(counts.values())

    echo("")
    echo("This will ARCHIVE and then DELETE the current season's data:")
    for name, n in counts.items():
        echo(f"  {name:>18}: {n}")
    echo(f"  {'TOTAL':>18}: {total}")
    echo("")
    echo("Reference tables (gender, race, fav_color, shoe_size, clothing_size,")
    echo("dhs_office, church) and site_setting are NOT touched.")
    echo("")

    if total == 0:
        echo("Nothing to archive. Exiting.")
        return 0

    if not skip_confirm:
        if confirm is None or not confirm("Proceed with archive + wipe?", default=False):
            echo("Aborted. No changes made.")
            return 0

    run_ts = datetime.now(timezone.utc)

    try:
        # Determine the season year for this run FIRST so every archive row can
        # be stamped with the same value. Derived from the children's
        # registration year (latest create_date year present); falls back to the
        # run timestamp's year if there are no children.
        child_years = [c.create_date.year for c in Child.query.all() if c.create_date]
        season_year = max(child_years) if child_years else run_ts.year
        echo(f"Season year for this archive run: {season_year}")

        # 1) Sponsors -> SponsorArchive, capturing live_id -> archive obj
        sponsor_map = {}
        for s in Sponsor.query.all():
            arc = _copy_columns(s, SponsorArchive,
                                overrides={'archive_date': run_ts,
                                           'archive_year': season_year})
            db.session.add(arc)
            sponsor_map[s.id] = arc

        # 2) Parents -> ParentArchive
        parent_map = {}
        for p in Parent.query.all():
            arc = _copy_columns(p, ParentArchive,
                                overrides={'archive_date': run_ts,
                                           'archive_year': season_year})
            db.session.add(arc)
            parent_map[p.id] = arc

        # Flush so the archive parents/sponsors get their new ids for FK remap.
        db.session.flush()

        # 3) Children -> ChildArchive, remapping parent_id / sponsor_id to the
        #    NEW archive ids. child_id (business key string) is preserved, and
        #    archive_year stamps the season so child_id is unique per season.
        for c in Child.query.all():
            overrides = {'archive_date': run_ts, 'archive_year': season_year}
            if c.parent_id is not None and c.parent_id in parent_map:
                overrides['parent_id'] = parent_map[c.parent_id].id
            else:
                overrides['parent_id'] = None
            if c.sponsor_id is not None and c.sponsor_id in sponsor_map:
                overrides['sponsor_id'] = sponsor_map[c.sponsor_id].id
            else:
                overrides['sponsor_id'] = None
            arc = _copy_columns(c, ChildArchive, overrides=overrides)
            db.session.add(arc)

        # 4) Gifts -> GiftArchive (child_id + archive_year link to the child)
        for g in Gift.query.all():
            arc = _copy_columns(g, GiftArchive,
                                overrides={'archive_date': run_ts,
                                           'archive_year': season_year})
            db.session.add(arc)

        # 5) GiftFulfillment -> GiftFulfillmentArchive (child_id + archive_year).
        #    The live table has no create_date, so stamp it with the run time.
        for gf in GiftFulfillment.query.all():
            arc = _copy_columns(gf, GiftFulfillmentArchive,
                                overrides={'archive_date': run_ts,
                                           'archive_year': season_year,
                                           'create_date': run_ts})
            db.session.add(arc)

        # 6) SponsorRequests -> SponsorRequestArchive (independent)
        for sr in SponsorRequest.query.all():
            arc = _copy_columns(sr, SponsorRequestArchive,
                                overrides={'archive_date': run_ts,
                                           'archive_year': season_year})
            db.session.add(arc)

        # Flush all archive inserts before deleting the live rows.
        db.session.flush()

        # 7) Wipe live tables in FK-safe order: dependent rows first.
        #    gift + gift_fulfillment reference child; child references parent +
        #    sponsor. sponsor_request is independent.
        Gift.query.delete()
        GiftFulfillment.query.delete()
        Child.query.delete()
        Parent.query.delete()
        Sponsor.query.delete()
        SponsorRequest.query.delete()

        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        echo(f"ERROR: archive failed and was rolled back. No data changed.\n  {exc}")
        raise

    echo("")
    echo(f"Archived {total} record(s) with archive_date {run_ts.isoformat()} "
         f"and wiped the live tables. Ready for a new season.")
    echo("")
    return total

@cli.command('db-create-all')
def db_create_all():
    db.create_all()


@cli.command('db-update-schema')
@click.option('--apply', 'do_apply', is_flag=True, default=False,
              help='Apply the additive changes. Without this, runs as a '
                   'dry-run report (the default).')
@click.option('--drop', 'do_drop', is_flag=True, default=False,
              help='Also DROP orphan tables/columns (present in the DB but not '
                   'in the models). Requires --apply and a typed confirmation.')
def db_update_schema(do_apply, do_drop):
    """
    Sync the database schema to the SQLAlchemy models (the single source of
    truth). Run this once on deploy after pulling code that changed models.

    What it does:
      * MISSING TABLES   -> created.
      * MISSING COLUMNS  -> added (ALTER TABLE ADD COLUMN); if the model column
                            has a scalar default, existing rows are backfilled.
      * ORPHANS          -> columns/tables in the DB but not in the models are
                            REPORTED. They are only dropped with --drop (plus
                            --apply and a typed confirmation).
      * RENAMES / TYPE CHANGES -> reflection cannot tell a rename from a
                            drop+add, and SQLite cannot ALTER a column type in
                            place, so these are only REPORTED, never auto-applied.
                            Handle them with a deliberate, manual migration.

    Default run is a DRY RUN: it prints the diff and changes nothing. Add
    --apply to perform the additive changes. ALWAYS back up the database before
    applying changes to production.
    """
    from sqlalchemy import inspect as sa_inspect, text as sa_text

    engine = db.engine
    insp = sa_inspect(engine)
    dialect = engine.dialect

    db_tables = set(insp.get_table_names())
    model_tables = dict(db.metadata.tables)  # name -> Table (model truth)

    missing_tables = []      # (table_name, Table)
    missing_columns = []     # (table_name, Column)
    orphan_tables = []       # table_name
    orphan_columns = []      # (table_name, column_name)
    type_mismatches = []     # (table_name, column_name, db_type, model_type)

    # --- Tables in the models but not in the DB -> need creation.
    for name, table in model_tables.items():
        if name not in db_tables:
            missing_tables.append((name, table))

    # --- Tables in the DB but not in the models -> orphans.
    for name in db_tables:
        if name not in model_tables and name != 'sqlite_sequence':
            orphan_tables.append(name)

    # --- Column-level diff for tables that exist in BOTH.
    for name, table in model_tables.items():
        if name not in db_tables:
            continue
        db_cols = {c['name']: c for c in insp.get_columns(name)}
        model_cols = {c.name: c for c in table.columns}

        for col_name, col in model_cols.items():
            if col_name not in db_cols:
                missing_columns.append((name, col))
            else:
                # Best-effort type comparison (string form). SQLite is loosely
                # typed, so treat this as advisory only.
                try:
                    model_type = col.type.compile(dialect=dialect).upper()
                    db_type = str(db_cols[col_name]['type']).upper()
                    base_model = model_type.split('(')[0]
                    base_db = db_type.split('(')[0]
                    if base_model and base_db and base_model != base_db:
                        type_mismatches.append((name, col_name, db_type, model_type))
                except Exception:
                    pass

        for col_name in db_cols:
            if col_name not in model_cols:
                orphan_columns.append((name, col_name))

    # ---------------------------------------------------------------- report
    def _bullet(items, fmt):
        for it in items:
            click.echo("    " + fmt(it))

    click.echo("")
    click.echo("Schema comparison (database vs. models):")
    click.echo("")

    if missing_tables:
        click.echo(f"  Missing tables ({len(missing_tables)}) -- will be CREATED:")
        _bullet(missing_tables, lambda t: t[0])
    if missing_columns:
        click.echo(f"  Missing columns ({len(missing_columns)}) -- will be ADDED:")
        _bullet(missing_columns, lambda c: f"{c[0]}.{c[1].name}")
    if orphan_tables:
        click.echo(f"  Orphan tables ({len(orphan_tables)}) -- in DB, not in models:")
        _bullet(orphan_tables, lambda t: t)
    if orphan_columns:
        click.echo(f"  Orphan columns ({len(orphan_columns)}) -- in DB, not in models:")
        _bullet(orphan_columns, lambda c: f"{c[0]}.{c[1]}")
    if type_mismatches:
        click.echo(f"  Type differences ({len(type_mismatches)}) -- REPORTED ONLY "
                   f"(handle manually; SQLite can't ALTER type in place):")
        _bullet(type_mismatches, lambda t: f"{t[0]}.{t[1]}: db={t[2]} model={t[3]}")

    nothing_additive = not missing_tables and not missing_columns
    nothing_at_all = (nothing_additive and not orphan_tables
                      and not orphan_columns and not type_mismatches)
    if nothing_at_all:
        click.echo("  Schema is already in sync with the models. Nothing to do.")
        click.echo("")
        return

    click.echo("")
    if not do_apply:
        click.echo("DRY RUN -- no changes made. Re-run with --apply to perform the")
        click.echo("additive changes above (missing tables/columns).")
        if orphan_tables or orphan_columns:
            click.echo("To also drop the orphan items, add --drop as well.")
        click.echo("")
        return

    # ---------------------------------------------------------------- apply
    # 1) Create missing tables. create_all() only builds what's absent, so it
    #    safely creates the missing ones and leaves existing tables alone.
    if missing_tables:
        db.create_all()
        for tname, _ in missing_tables:
            click.echo(f"  created table: {tname}")

    # 2) Add missing columns, backfilling scalar model defaults.
    for tname, col in missing_columns:
        col_type = col.type.compile(dialect=dialect)
        ddl = f'ALTER TABLE {tname} ADD COLUMN {col.name} {col_type}'
        db.session.execute(sa_text(ddl))
        click.echo(f"  added column: {tname}.{col.name} ({col_type})")

        default_value = _scalar_default(col)
        if default_value is not None:
            db.session.execute(
                sa_text(f'UPDATE {tname} SET {col.name} = :v '
                        f'WHERE {col.name} IS NULL').bindparams(v=default_value),
            )
            click.echo(f"      backfilled default: {default_value!r}")
    db.session.commit()

    # 3) Drops (only with --drop + typed confirmation).
    if orphan_tables or orphan_columns:
        if not do_drop:
            click.echo("")
            click.echo("Orphan items were NOT dropped (re-run with --drop to remove "
                       "them).")
        else:
            click.echo("")
            click.echo("About to DROP the following (data will be lost):")
            for t in orphan_tables:
                click.echo(f"    table  {t}")
            for tname, cname in orphan_columns:
                click.echo(f"    column {tname}.{cname}")
            typed = click.prompt('Type DROP to confirm', default='', show_default=False)
            if typed.strip() != 'DROP':
                click.echo("Confirmation not received; nothing dropped.")
            else:
                for tname, cname in orphan_columns:
                    # Modern SQLite (3.35+) supports DROP COLUMN; fall back
                    # gracefully if the engine refuses.
                    try:
                        db.session.execute(
                            sa_text(f'ALTER TABLE {tname} DROP COLUMN {cname}')
                        )
                        click.echo(f"  dropped column: {tname}.{cname}")
                    except Exception as exc:
                        db.session.rollback()
                        click.echo(f"  could NOT drop {tname}.{cname}: {exc}")
                for t in orphan_tables:
                    db.session.execute(sa_text(f'DROP TABLE {t}'))
                    click.echo(f"  dropped table: {t}")
                db.session.commit()

    click.echo("")
    click.echo("Schema update complete.")
    click.echo("")


def _scalar_default(col):
    """Return a column's scalar default value if it has a simple one, else None.

    Only plain literal defaults are backfilled (e.g. default='...', default=0,
    default=True). Callable/server-side/SQL defaults are skipped -- they're
    applied by the app at insert time, not retroactively here.
    """
    default = getattr(col, 'default', None)
    if default is None:
        return None
    arg = getattr(default, 'arg', None)
    if arg is None:
        return None
    if callable(arg):
        return None  # don't evaluate callable defaults during migration
    return arg


@cli.command('rebuild-archive-tables')
@click.option('--yes', is_flag=True, default=False,
              help='Skip the confirmation prompt.')
def rebuild_archive_tables(yes):
    """
    Drop and recreate the archive tables so they pick up the current schema
    (string child_id, archive_year, composite (child_id, archive_year) unique
    constraint and composite foreign keys, plus archive_date).

    SAFE ONLY WHEN THE ARCHIVE TABLES ARE EMPTY -- this DROPS them. It never
    touches live tables, reference tables, or site_setting. Run once when
    upgrading to the new archive schema.
    """
    from sqlalchemy import inspect as sa_inspect, text as sa_text
    from webapp.models import (
        ChildArchive, ParentArchive, GiftArchive, SponsorArchive,
        SponsorRequestArchive, GiftFulfillmentArchive,
    )

    # Drop order respects FKs: dependents (gift/fulfillment -> child) first,
    # child before parent/sponsor.
    ordered = [
        GiftArchive, GiftFulfillmentArchive, ChildArchive,
        ParentArchive, SponsorArchive, SponsorRequestArchive,
    ]

    insp = sa_inspect(db.engine)
    existing = set(insp.get_table_names())

    # Safety check: refuse if any archive table has rows. Use raw SQL for the
    # count -- an ORM query would reference new-schema columns (e.g.
    # archive_year) that the OLD table on disk doesn't have yet, which would
    # crash this very check.
    nonempty = []
    for model in ordered:
        table = model.__tablename__
        if table in existing:
            count = db.session.execute(
                sa_text(f"SELECT COUNT(*) FROM {table}")
            ).scalar()
            if count:
                nonempty.append((table, count))
    if nonempty:
        click.echo("Refusing to rebuild: these archive tables contain data:")
        for name, n in nonempty:
            click.echo(f"  {name}: {n} row(s)")
        click.echo("Back up and clear them first, or migrate manually.")
        return

    click.echo("This will DROP and recreate these (empty) archive tables:")
    for model in ordered:
        click.echo(f"  {model.__tablename__}")
    if not yes and not click.confirm("Proceed?", default=False):
        click.echo("Aborted.")
        return

    # Drop (ignore those that don't exist yet), then recreate everything.
    # Raw DROP TABLE is schema-agnostic, so it works even though the model
    # metadata no longer matches the old table on disk.
    for model in ordered:
        table = model.__tablename__
        if table in existing:
            db.session.execute(sa_text(f"DROP TABLE {table}"))
            click.echo(f"  dropped {table}")
    db.session.commit()
    db.create_all()
    click.echo("")
    click.echo("Done. Archive tables recreated with the current schema.")


@cli.command('create-admin-hash')
@click.option('--password', prompt=True, hide_input=True,
              confirmation_prompt=True,
              help='The admin password to hash (input hidden).')
def create_admin_hash(password):
    """
    Generate a password hash for the admin login. Paste the printed value into
    your .env file as ADMIN_PASSWORD_HASH (the plaintext is never stored).
    """
    from werkzeug.security import generate_password_hash
    pw_hash = generate_password_hash(password)
    click.echo("")
    click.echo("Add this line to your .env file:")
    click.echo("")
    click.echo(f"ADMIN_PASSWORD_HASH={pw_hash}")
    click.echo("")


if __name__ == '__main__':
    cli()