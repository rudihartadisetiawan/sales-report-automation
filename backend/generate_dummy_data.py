"""Generate dummy sales data for the weekly sales report demo."""
import os
import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

# ponytail: fixed seed for reproducible demo data, not security
random.seed(42)
np.random.seed(42)

PRODUCTS = [
    ("Headset Bluetooth", "Elektronik", 185000),
    ("Power Bank 10000mAh", "Elektronik", 245000),
    ("Mouse Wireless", "Elektronik", 125000),
    ("Kaos Polos", "Fashion", 75000),
    ("Kemeja Flanel", "Fashion", 165000),
    ("Celana Jeans", "Fashion", 235000),
    ("Sneakers", "Fashion", 320000),
    ("Botol Minum 1L", "Rumah Tangga", 65000),
    ("Set Pisau Dapur", "Rumah Tangga", 145000),
    ("Lampu LED", "Rumah Tangga", 55000),
    ("Tas Ransel", "Fashion", 195000),
    ("Kipas Angin Meja", "Elektronik", 155000),
]


def daily_multiplier(date: datetime) -> float:
    """Weekends are busier; some days have small spikes."""
    weekday = date.weekday()
    base = 1.0
    if weekday >= 5:  # Saturday/Sunday
        base += 0.45
    if random.random() < 0.15:
        base += 0.25
    return base


def generate_sales_data(days: int = 42, rows_per_day: int = 15) -> pd.DataFrame:
    """Generate realistic sales data for the past N days."""
    end_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    rows = []
    for i in range(days):
        date = end_date - timedelta(days=days - 1 - i)
        multiplier = daily_multiplier(date)
        for _ in range(rows_per_day):
            product, category, base_price = random.choice(PRODUCTS)
            # Vary price slightly for same product
            price = int(base_price * random.uniform(0.92, 1.08))
            # Quantity depends on product popularity and daily multiplier
            base_qty = random.randint(1, 5)
            if product in ("Kaos Polos", "Headset Bluetooth", "Sneakers"):
                base_qty += random.randint(1, 3)
            qty = max(1, int(base_qty * multiplier))
            rows.append({
                "tanggal": date.strftime("%Y-%m-%d"),
                "nama_produk": product,
                "kategori": category,
                "jumlah_terjual": qty,
                "harga_satuan": price,
                "total": qty * price,
            })
    df = pd.DataFrame(rows)
    return df


def main() -> None:
    data_dir = "data"
    os.makedirs(data_dir, exist_ok=True)
    df = generate_sales_data()
    csv_path = os.path.join(data_dir, "dummy_sales.csv")
    df.to_csv(csv_path, index=False)
    print(f"Generated {len(df)} rows to {csv_path}")
    print(f"Date range: {df['tanggal'].min()} to {df['tanggal'].max()}")
    print(f"Total revenue: Rp {df['total'].sum():,}")


if __name__ == "__main__":
    main()
