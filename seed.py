# seed_data.py
from faker import Faker
import random
from datetime import date, timedelta
from db import get_connection

fake = Faker()
conn = get_connection()
cursor = conn.cursor()

cities = ["Bengaluru", "Mumbai", "Delhi", "Chennai"]

# ---------- INSERT STORES ----------
store_ids = []
for city in cities:
    cursor.execute(
        "INSERT INTO stores (city) VALUES (%s)",
        (city,)
    )
    store_ids.append(cursor.lastrowid)

# ---------- INSERT CUSTOMERS ----------
customer_ids = []
for _ in range(50):
    cursor.execute(
        """
        INSERT INTO customers (name, city, age)
        VALUES (%s, %s, %s)
        """,
        (
            fake.name(),
            random.choice(cities),
            random.randint(18, 65)
        )
    )
    customer_ids.append(cursor.lastrowid)

# ---------- INSERT ORDERS ----------
for _ in range(500):
    cursor.execute(
        """
        INSERT INTO orders (customer_id, store_id, order_date, amount, returned)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (
            random.choice(customer_ids),
            random.choice(store_ids),
            fake.date_between(start_date="-1y", end_date="today"),
            round(random.uniform(100, 5000), 2),
            random.choice([0, 0, 0, 1])  # ~25% returns
        )
    )

conn.commit()
cursor.close()
conn.close()

print("✅ MySQL database seeded successfully")
