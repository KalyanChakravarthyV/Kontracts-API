from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv


load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://leaseuser:leasepass@localhost:5432/leasedb")
SSL_CA_CERT_PATH = os.getenv("DB_SSL_CERT_PATH")

# Configure SSL for database connection if certificate path is provided
connect_args = {}
if SSL_CA_CERT_PATH:
    # Resolve relative path to absolute path
    cert_path = os.path.abspath(SSL_CA_CERT_PATH)

    if os.path.exists(cert_path):

        connect_args = {
            "sslmode": "require",
            "sslrootcert": SSL_CA_CERT_PATH
        }
        print(f"SSL certificate loaded from: {cert_path}")
    else:
        print(f"Warning: SSL certificate not found at {cert_path}")

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
