import sqlite3

# Check what subject the assessment is looking for
registry_db = '/Users/soms/adaptive-assessment-system/backend/data/registry.db'
conn = sqlite3.connect(registry_db)
cursor = conn.cursor()
cursor.execute("SELECT name, subject FROM item_banks_registry WHERE name = 'maths_complex_nos'")
row = cursor.fetchone()
print(f"Item bank name: {row[0]}")
print(f"Registry subject: {row[1]}")
conn.close()

# The assessment uses item_bank_name which is 'maths_complex_nos'
# So update questions to use that:
db_path = '/Users/soms/adaptive-assessment-system/backend/data/maths_complex_nos.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("UPDATE questions SET subject = 'maths_complex_nos'")
conn.commit()
print(f"Updated {cursor.rowcount} questions to subject='maths_complex_nos'")
conn.close()