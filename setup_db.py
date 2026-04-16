#!/usr/bin/env python3
"""
One-time setup script for the MindGraph Django backend.
Run this script ONCE to create the PostgreSQL database and user,
then apply migrations.

Usage:
    python3 setup_db.py

This script uses the 'postgres' OS superuser via peer auth OR prompts
you for the postgres password if running via TCP.
"""
import subprocess
import sys
import os
import getpass

def run(cmd, **kwargs):
    print(f"  $ {' '.join(cmd)}")
    result = subprocess.run(cmd, **kwargs)
    return result

def main():
    print("=" * 60)
    print("  MindGraph Backend – Database Setup")
    print("=" * 60)

    db_name = "mindmapdb"
    db_user = "deepeigen"

    # ── Ask for postgres superuser password ──────────────────────────
    print("\nThis script needs to connect to PostgreSQL as the 'postgres' superuser.")
    print("If your postgres account uses 'peer' auth (default on Ubuntu) you can")
    print("run this using: sudo -u postgres python3 setup_db.py\n")
    
    pg_pass = getpass.getpass("Enter your postgres superuser password (or press Enter for peer auth): ")
    
    env = os.environ.copy()
    if pg_pass:
        env["PGPASSWORD"] = pg_pass
        pg_host_args = ["-h", "localhost", "-U", "postgres"]
    else:
        # Try peer auth – must be run as postgres OS user
        pg_host_args = ["-U", "postgres"]

    # ── Create user ───────────────────────────────────────────────────
    print(f"\n[1/3] Creating PostgreSQL user '{db_user}' (if not exists)...")
    create_user_sql = f"DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = '{db_user}') THEN CREATE USER {db_user} WITH CREATEDB; END IF; END $$;"
    r = run(["psql", *pg_host_args, "-d", "postgres", "-c", create_user_sql], env=env)
    if r.returncode != 0:
        print("  ⚠  Failed to create user. Try running as: sudo -u postgres python3 setup_db.py")
        sys.exit(1)

    # ── Create database ───────────────────────────────────────────────
    print(f"\n[2/3] Creating database '{db_name}' (if not exists)...")
    create_db_sql = f"SELECT 'CREATE DATABASE {db_name} OWNER {db_user}' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '{db_name}') \\gexec"
    r = run(["psql", *pg_host_args, "-d", "postgres", "-c", f"CREATE DATABASE {db_name} OWNER {db_user}"], env=env, capture_output=True)
    if r.returncode != 0 and b"already exists" not in r.stderr:
        print(f"  Error: {r.stderr.decode()}")
    else:
        print(f"  ✓ Database '{db_name}' ready.")

    # ── Grant privileges ──────────────────────────────────────────────
    run(["psql", *pg_host_args, "-d", db_name, "-c", f"GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {db_user};"], env=env)

    # ── Run Django migrations ─────────────────────────────────────────
    print(f"\n[3/3] Running Django migrations...")
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    r = subprocess.run(
        [sys.executable, "manage.py", "migrate"],
        cwd=backend_dir,
        env={**os.environ, "DB_NAME": db_name, "DB_USER": db_user, "DB_HOST": "localhost" if pg_pass else ""}
    )
    if r.returncode != 0:
        print("  ⚠  Migrations failed. Check settings.py and DB credentials.")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("  ✅  Setup complete! Start the backend with:")
    print(f"       cd {backend_dir}")
    print("       python3 manage.py runserver 8000")
    print("=" * 60)

if __name__ == "__main__":
    main()
