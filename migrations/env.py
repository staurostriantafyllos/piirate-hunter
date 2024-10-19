import sys
from logging.config import fileConfig

from alembic import context
from sqlmodel import SQLModel

from app.db.factories import get_session_ctx
from app.models.database import Matches

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here for 'autogenerate' support
target_metadata = SQLModel.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to associate a connection with the context.

    """
    with get_session_ctx() as session:
        connection = session.connection()

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


def prompt_for_downgrade():
    if 'downgrade' in sys.argv:
        confirmation = input(
            "Are you sure you want to downgrade the database? (yes/no): "
        )
        if confirmation.lower() != 'yes':
            print("Downgrade aborted.")
            sys.exit(1)


prompt_for_downgrade()

run_migrations_online()
