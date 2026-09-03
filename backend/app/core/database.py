from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import DATABASE_URL

# Normalize database URL
db_url = DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

# Database Engine Configuration
if "sqlite" in db_url:
    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False},
    )
    # Enable WAL mode and foreign key constraints on SQLite connections
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
else:
    # PostgreSQL / Enterprise Multi-Workstation Pool
    engine = create_engine(
        db_url,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_db_type() -> str:
    """Returns database backend type: 'sqlite' or 'postgresql'."""
    return "sqlite" if "sqlite" in db_url.lower() else "postgresql"

def check_db_connection(db_session=None) -> tuple[bool, str]:
    """Probes active database connection readiness."""
    session = db_session or SessionLocal()
    try:
        session.execute(text("SELECT 1"))
        return True, "Connected"
    except Exception as e:
        return False, str(e)
    finally:
        if db_session is None:
            session.close()
