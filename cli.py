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