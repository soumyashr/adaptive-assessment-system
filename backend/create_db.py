# create_db.py
from database import Base, engine
import models

# Drop all tables
Base.metadata.drop_all(bind=engine)

# Recreate with new schema
Base.metadata.create_all(bind=engine)

print("Database recreated with new schema")