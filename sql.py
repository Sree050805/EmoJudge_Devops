import sqlite3
from werkzeug.security import generate_password_hash

# Connect to the existing database (or create new)
conn = sqlite3.connect('users.db')
cursor = conn.cursor()

# Create the users table if it doesn’t exist
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    attorney_id TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    email TEXT
)
''')

# Insert 13 new users with hashed passwords
new_users_data = [
    ('sophia.bennett', 'sb1122'),
    ('oliver.thomas', 'otSecure!55'),
    ('ava.davis', 'avaStrong321'),
    ('william.clark', 'wcPass789'),
    ('mia.hall', 'mia123hall'),
    ('james.moore', 'jmAlpha999'),
    ('isabella.adams', 'iaSecret321'),
    ('lucas.king', 'lkKnight12'),
    ('charlotte.scott', 'csQueen88'),
    ('henry.morgan', 'hmPirate007'),
    ('amelia.carter', 'acSecure22'),
    ('jackson.taylor', 'jtFast777'),
    ('ella.evans', 'eeRock123')
]

# Hash the passwords before inserting
hashed_new_users = [(attorney_id, generate_password_hash(password)) for attorney_id, password in new_users_data]

# Insert the users (ignore duplicates if already exist)
cursor.executemany('''
INSERT OR IGNORE INTO users (attorney_id, password)
VALUES (?, ?)
''', hashed_new_users)

# Commit and close
conn.commit()
conn.close()

print("✅ 13 new users have been added to the database!")


