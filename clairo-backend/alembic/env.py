from alembic import context

from app.database import Base, engine
import app.models  # noqa: F401  (registers all tables on Base.metadata)

target_metadata = Base.metadata


def _configure_and_run(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,   # SQLite can't ALTER constraints in place
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # Tests inject their own connection to migrate throwaway databases.
    injected = context.config.attributes.get("connection")
    if injected is not None:
        _configure_and_run(injected)
        return
    with engine.connect() as connection:
        _configure_and_run(connection)


run_migrations_online()
