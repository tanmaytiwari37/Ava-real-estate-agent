import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

current_dir = os.path.dirname(__file__)
env_path = os.path.join(current_dir, ".env")

# --- NEW DIAGNOSTICS ---
print(f"DEBUG: Looking for .env file at -> {env_path}")
print(f"DEBUG: Does the file actually exist here? -> {os.path.exists(env_path)}")
# -----------------------

load_dotenv(env_path, override=True)
DATABASE_URL = os.environ.get("DATABASE_URL")

print(f"DEBUG: Found URL -> {DATABASE_URL}")

if not DATABASE_URL:
    print("❌ ERROR: Still can't find it!")
    exit()

engine = create_engine(DATABASE_URL)
print("Attempting to connect to Neon...")

with engine.connect() as connection:
    result = connection.execute(text("SELECT city, price_inr, bedrooms FROM properties LIMIT 5"))
    print("\n✅ CONNECTION SUCCESSFUL! Here is your data:\n")
    for row in result:
        print(f"City: {row[0]} | Price: ₹{row[1]} | BHK: {row[2]}")