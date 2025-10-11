-- Script to drop all tables in the kontracts schema
-- WARNING: This will permanently delete all data!

-- Drop all tables, types, and sequences in the kontracts schema (if it exists)
DO $$
DECLARE
    r RECORD;
BEGIN
    -- Drop all tables in the kontracts schema
    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'kontracts')
    LOOP
        EXECUTE 'DROP TABLE IF EXISTS kontracts.' || quote_ident(r.tablename) || ' CASCADE';
        RAISE NOTICE 'Dropped table: kontracts.%', r.tablename;
    END LOOP;

    -- Drop all types (enums) in the kontracts schema
    FOR r IN (SELECT typname FROM pg_type WHERE typnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'kontracts') AND typtype = 'e')
    LOOP
        EXECUTE 'DROP TYPE IF EXISTS kontracts.' || quote_ident(r.typname) || ' CASCADE';
        RAISE NOTICE 'Dropped type: kontracts.%', r.typname;
    END LOOP;

    -- Drop all sequences in the kontracts schema
    FOR r IN (SELECT sequencename FROM pg_sequences WHERE schemaname = 'kontracts')
    LOOP
        EXECUTE 'DROP SEQUENCE IF EXISTS kontracts.' || quote_ident(r.sequencename) || ' CASCADE';
        RAISE NOTICE 'Dropped sequence: kontracts.%', r.sequencename;
    END LOOP;

    -- Drop all tables in the public schema
    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public')
    LOOP
        EXECUTE 'DROP TABLE IF EXISTS public.' || quote_ident(r.tablename) || ' CASCADE';
        RAISE NOTICE 'Dropped table: public.%', r.tablename;
    END LOOP;
END $$;

-- Optionally, drop the kontracts schema itself
-- Uncomment the line below if you want to delete the schema too
-- DROP SCHEMA IF EXISTS kontracts CASCADE;

-- Display remaining tables and types
SELECT 'TABLES' as object_type, schemaname, tablename as name
FROM pg_tables
WHERE schemaname IN ('kontracts', 'public')
UNION ALL
SELECT 'TYPES' as object_type, nspname as schemaname, typname as name
FROM pg_type
JOIN pg_namespace ON pg_type.typnamespace = pg_namespace.oid
WHERE nspname IN ('kontracts', 'public') AND typtype = 'e'
ORDER BY object_type, schemaname, name;
