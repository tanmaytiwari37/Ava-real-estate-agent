import pandas as pd 
from sqlalchemy import create_engine

# Remove your real password and replace it with a dummy placeholder string
NEON_DATABASE_URL = "postgresql://neondb_owner:YOUR_SECRET_PASSWORD_HERE@ep-small-poetry-aq5sj4hd-pooler.c-8.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
CSV_FILE_NAME = "Indian_Real_Estate_Market_Dataset.csv"

def upload_dataset_to_sql():
    try:
        df = pd.read_csv(CSV_FILE_NAME)
        df.columns = df.columns.str.strip()
        engine = create_engine(NEON_DATABASE_URL)
        df.to_sql("properties", con=engine, if_exists="replace", index=False)
    except FileNotFoundError:
        print(f"❌ Error: Could not find '{CSV_FILE_NAME}' in your folder. Make sure the filename matches exactly!")
    except Exception as e:
        print(f"❌ Migration failed due to error: {str(e)}")

if __name__ == "__main__":
    upload_dataset_to_sql()