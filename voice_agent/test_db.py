import os
import socket
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Force socket to resolve ONLY IPv4 for Neon host to prevent local network IPv6 routing issues on developer machine
orig_getaddrinfo = socket.getaddrinfo
def getaddrinfo_ipv4(host, port, family=0, type=0, proto=0, flags=0):
    if host and "neon.tech" in host:
        return orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
    return orig_getaddrinfo(host, port, family, type, proto, flags)

socket.getaddrinfo = getaddrinfo_ipv4

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
    print("[ERROR] Still can't find DATABASE_URL!")
    exit()

engine = create_engine(DATABASE_URL)
print("Attempting to connect to Neon...")

with engine.connect() as connection:
    result = connection.execute(text("SELECT city, price_inr, bedrooms FROM properties LIMIT 5"))
    print("\n[OK] CONNECTION SUCCESSFUL! Here is your data:\n")
    for row in result:
        print(f"City: {row[0]} | Price: Rs {row[1]} | BHK: {row[2]}")