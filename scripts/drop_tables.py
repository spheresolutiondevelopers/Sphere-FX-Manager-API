import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import sync_engine
from sqlalchemy import text


def drop_all_tables():
    with sync_engine.connect() as conn:
        # Disable all constraints temporarily
        conn.execute(text("EXEC sp_msforeachtable 'ALTER TABLE ? NOCHECK CONSTRAINT all'"))
        conn.commit()

        # Drop all foreign key constraints
        conn.execute(text("""
            DECLARE @sql NVARCHAR(MAX) = N'';
            SELECT @sql += N'ALTER TABLE ' + 
                QUOTENAME(OBJECT_SCHEMA_NAME(parent_object_id)) + '.' + 
                QUOTENAME(OBJECT_NAME(parent_object_id)) + 
                ' DROP CONSTRAINT ' + QUOTENAME(name) + ';'
            FROM sys.foreign_keys;
            EXEC sp_executesql @sql;
        """))
        conn.commit()

        # Drop all tables
        conn.execute(text("EXEC sp_msforeachtable 'DROP TABLE ?'"))
        conn.commit()

        print("✅ All tables dropped successfully.")


if __name__ == "__main__":
    drop_all_tables()