import sqlite3

def migrate_database():
    conn = sqlite3.connect('translations.db')
    c = conn.cursor()
    
    try:
        # Check if xml_processed column exists
        c.execute('PRAGMA table_info(translations)')
        columns = [column[1] for column in c.fetchall()]
        
        if 'xml_processed' not in columns:
            print("Adding xml_processed column...")
            c.execute('ALTER TABLE translations ADD COLUMN xml_processed BOOLEAN DEFAULT FALSE')
            conn.commit()
            print("Database migration completed successfully!")
        else:
            print("xml_processed column already exists!")
            
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()