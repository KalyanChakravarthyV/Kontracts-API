#!/usr/bin/env python3
"""
Script to drop all tables in PostgreSQL database.
WARNING: This will permanently delete all data!

Usage:
    python scripts/drop_all_tables.py
"""

import os
import sys
from sqlalchemy import create_engine, text, inspect
from dotenv import load_dotenv

# Add parent directory to path to import from app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("ERROR: DATABASE_URL not found in environment variables")
    sys.exit(1)


def drop_all_tables():
    """Drop all tables, types, and sequences in the database"""
    engine = create_engine(DATABASE_URL)

    print("Connecting to database...")
    print(f"Database URL: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'unknown'}")
    print()

    with engine.connect() as connection:
        inspector = inspect(engine)

        # Get all schemas
        schemas = ['kontracts', 'public']

        for schema in schemas:
            # Check if schema exists
            if schema == 'kontracts' and schema not in inspector.get_schema_names():
                print(f"Schema '{schema}' does not exist, skipping...")
                continue

            # Get all tables in the schema
            tables = inspector.get_table_names(schema=schema)

            if tables:
                print(f"\n=== Dropping tables in schema '{schema}' ===")
                for table in tables:
                    try:
                        full_table_name = f"{schema}.{table}"
                        print(f"Dropping table: {full_table_name}")
                        connection.execute(text(f"DROP TABLE IF EXISTS {full_table_name} CASCADE"))
                        connection.commit()
                    except Exception as e:
                        print(f"Error dropping table {full_table_name}: {e}")
            else:
                print(f"No tables found in schema '{schema}'")

            # Drop all enum types in the schema
            print(f"\n=== Dropping enum types in schema '{schema}' ===")
            try:
                result = connection.execute(text(f"""
                    SELECT typname
                    FROM pg_type
                    WHERE typnamespace = (SELECT oid FROM pg_namespace WHERE nspname = '{schema}')
                    AND typtype = 'e'
                """))
                types = [row[0] for row in result]

                if types:
                    for type_name in types:
                        try:
                            full_type_name = f"{schema}.{type_name}"
                            print(f"Dropping type: {full_type_name}")
                            connection.execute(text(f"DROP TYPE IF EXISTS {full_type_name} CASCADE"))
                            connection.commit()
                        except Exception as e:
                            print(f"Error dropping type {full_type_name}: {e}")
                else:
                    print(f"No enum types found in schema '{schema}'")
            except Exception as e:
                print(f"Error querying types in schema '{schema}': {e}")

            # Drop all sequences in the schema
            print(f"\n=== Dropping sequences in schema '{schema}' ===")
            try:
                result = connection.execute(text(f"""
                    SELECT sequencename
                    FROM pg_sequences
                    WHERE schemaname = '{schema}'
                """))
                sequences = [row[0] for row in result]

                if sequences:
                    for sequence_name in sequences:
                        try:
                            full_sequence_name = f"{schema}.{sequence_name}"
                            print(f"Dropping sequence: {full_sequence_name}")
                            connection.execute(text(f"DROP SEQUENCE IF EXISTS {full_sequence_name} CASCADE"))
                            connection.commit()
                        except Exception as e:
                            print(f"Error dropping sequence {full_sequence_name}: {e}")
                else:
                    print(f"No sequences found in schema '{schema}'")
            except Exception as e:
                print(f"Error querying sequences in schema '{schema}': {e}")

        print("\n=== Checking for remaining objects ===")
        remaining_objects = False
        for schema in schemas:
            if schema == 'kontracts' and schema not in inspector.get_schema_names():
                continue

            tables = inspector.get_table_names(schema=schema)
            if tables:
                remaining_objects = True
                print(f"Schema '{schema}': {len(tables)} table(s) remaining: {', '.join(tables)}")

            # Check for remaining types
            result = connection.execute(text(f"""
                SELECT typname
                FROM pg_type
                WHERE typnamespace = (SELECT oid FROM pg_namespace WHERE nspname = '{schema}')
                AND typtype = 'e'
            """))
            types = [row[0] for row in result]
            if types:
                remaining_objects = True
                print(f"Schema '{schema}': {len(types)} type(s) remaining: {', '.join(types)}")

        if not remaining_objects:
            print("All objects have been successfully dropped!")

        # Optionally drop the kontracts schema
        drop_schema = input("\nDo you want to drop the 'kontracts' schema as well? (yes/no): ")
        if drop_schema.lower() in ['yes', 'y']:
            try:
                print("Dropping schema 'kontracts'...")
                connection.execute(text("DROP SCHEMA IF EXISTS kontracts CASCADE"))
                connection.commit()
                print("Schema 'kontracts' dropped successfully!")
            except Exception as e:
                print(f"Error dropping schema: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("WARNING: This script will DELETE ALL TABLES in the database!")
    print("=" * 60)

    confirm = input("\nAre you sure you want to continue? (yes/no): ")

    if confirm.lower() in ['yes', 'y']:
        drop_all_tables()
        print("\nDone!")
    else:
        print("\nOperation cancelled.")
