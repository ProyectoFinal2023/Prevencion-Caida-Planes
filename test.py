import os
import urllib.parse
from sqlalchemy import create_engine
import pandas as pd
from faker import Faker
from dotenv import load_dotenv

# Function to get SQLAlchemy engine
def get_engine():
    load_dotenv()
    db_user = os.environ.get("DB_USER")
    db_pass = os.environ.get("DB_PASS")
    db_host = os.environ.get("DB_HOST")
    db_port = os.environ.get("DB_PORT")
    db_name = os.environ.get("DB_NAME")
    new_pass = urllib.parse.quote_plus(db_pass)
    url = f"postgresql+pg8000://{db_user}:{new_pass}@{db_host}:{db_port}/{db_name}"
    engine = create_engine(url)
    return engine

def generate_fake_data(N):
    fake = Faker('es_AR')
    data = []
    for _ in range(N):
        data.append({
            'telefono': fake.phone_number(),
            'mail': fake.email()
        })
    return data

def main(N):
    engine = get_engine()
    data = generate_fake_data(N)
    
    # Create a Pandas DataFrame from the generated data
    df = pd.DataFrame(data)
    print(df)
    # Insert the DataFrame into the PostgreSQL database

    try:
        df.to_sql('aux_datos', engine, if_exists='append', index=False, method="multi")
        print("Data inserted successfully.")
    except Exception as e:
        print("Error inserting data:", str(e))
    
if __name__ == "__main__":
    N = 10000  # Change N to the desired number of rows to insert
    main(N)
    print(1)
