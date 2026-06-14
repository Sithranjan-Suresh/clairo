import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# ---------------------------------------------------------------------------
# InsForge Postgres Database
# ---------------------------------------------------------------------------
# CLAIRO uses InsForge as its agent-native cloud database backend.
# InsForge provides a fully managed Postgres database with built-in auth,
# row-level security, and a context-efficient MCP layer for AI agents.
#
# Set INSFORGE_DATABASE_URL in your .env to the connection string from:
#   npx @insforge/cli db connection-string
#
# Falls back to local SQLite for development without an InsForge account.
# ---------------------------------------------------------------------------

INSFORGE_DATABASE_URL = os.getenv("INSFORGE_DATABASE_URL")

if INSFORGE_DATABASE_URL:
    DATABASE_URL = INSFORGE_DATABASE_URL
    engine = create_engine(DATABASE_URL)
else:
    # Local SQLite fallback for development
    DATABASE_URL = "sqlite:///./clairo.db"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()
