from datetime import datetime
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


@cli.command('archive-data')
@click.argument('date_string')
@click.argument('table_name')
def archive_data_command(date_string: str, table_name: str):
    """
    Moves data older than a specified date to the archive table.
    Usage: flask archive-data YYYY-MM-DD
    """
    try:
        cutoff_date = datetime.strptime(date_string, '%Y-%m-%d')
    except ValueError:
        click.echo("Error: Invalid date format. Please use YYYY-MM-DD.")
        return

    with create_app().app_context():
        data_table = get_orm_class_by_tablename(db, table_name.lower())
        archive_table = get_orm_class_by_tablename(db, f"{table_name.lower()}_archive")

        source_columns = [c.key for c in data_table.__table__.columns]
        # click.echo(source_columns)
        result = db.session.execute(
            db.select(data_table).where(data_table.create_date < cutoff_date)
        ).all()

        for row in result:
            row_data = {col: getattr(row, col) for col in source_columns}
            new_row = archive_table(**row_data)
            db.session.add(new_row)
            # db.session.delete(row)

        db.session.commit()

    # Query for records to be archived
    # records_to_archive = UserData.query.filter(UserData.timestamp < cutoff_date).all()
    # count = len(records_to_archive)

    # if count == 0:
    #     click.echo("No records found to archive.")
    #     return
    #
    # click.echo(f"Found {count} record(s) to archive.")
    #
    # for record in records_to_archive:
    #     # Create a new record in the archive table
    #     archived_record = ArchivedUserData(
    #         username=record.username,
    #         timestamp=record.timestamp
    #     )
    #     db.session.add(archived_record)
    #     # Delete the old record
    #     db.session.delete(record)
    #
    # db.session.commit()
    # click.echo(f"Successfully archived {count} record(s) older than {date_string}.")

@cli.command('db-create-all')
def db_create_all():
    db.create_all()


if __name__ == '__main__':
    cli()