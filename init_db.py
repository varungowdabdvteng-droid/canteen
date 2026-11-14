"""
Database initialization script for Online Canteen Pre-Ordering System.
Creates the database schema, default admin account, demo student, and initial food items.
"""
from app import init_db

if __name__ == "__main__":
    print("Initializing database (database.db)...")
    init_db()
    print("Database initialization complete!")
    print("\nDefault Accounts:")
    print("--------------------------------------------------")
    print("Administrator: admin@canteen.com  / Password: admin123")
    print("Demo Student:  student@canteen.com / Password: student123")
    print("--------------------------------------------------")
