from __future__ import annotations

import math
import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker


fake = Faker()
random.seed(42)
np.random.seed(42)


@dataclass(frozen=True)
class Product:
    product_name: str
    sku: str
    category: str
    subcategory: str
    base_price: float
    base_cost: float
    launch_date: date
    lifecycle_stage: str
    reorder_point: int
    target_days_cover: int
    supplier_id: str
    supplier_name: str
    lead_time_days: int


START_DATE = date(2024, 1, 1)
END_DATE = date(2025, 12, 31)
NUM_SALES_ROWS = 25000
NUM_CUSTOMERS = 1800
WAREHOUSES = ["Johannesburg DC", "Cape Town DC", "Durban Hub", "Pretoria Hub"]
REGIONS = ["Gauteng", "Western Cape", "KwaZulu-Natal", "Eastern Cape", "Free State", "Limpopo"]
CHANNELS = ["Retail", "Wholesale", "Ecommerce", "Distributor"]
CURRENCIES = ["ZAR", "USD"]
PAYMENT_TERMS = ["COD", "Net 15", "Net 30", "Net 45", "Net 60"]
SALES_REPS = ["N. Dlamini", "S. Naidoo", "T. Mokoena", "L. van Wyk", "A. Petersen"]
PROMOTIONS = ["None", "Summer Promo", "Year End Promo", "Bundle Discount", "Launch Campaign"]
RETURN_REASONS = ["Damaged", "Wrong Item", "Customer Return", "Late Delivery", "Pricing Dispute"]
ORDER_STATUSES = ["Completed", "Completed", "Completed", "Completed", "Returned", "Cancelled"]
SUPPLIERS = [
    ("SUP001", "Apex Industrial Supplies", 14),
    ("SUP002", "BluePeak Components", 21),
    ("SUP003", "OmniTrade Distributors", 30),
    ("SUP004", "MetroSource Wholesale", 10),
    ("SUP005", "PrimeLine Imports", 45),
]


PRODUCTS = [
    Product("Widget Alpha", "SKU001", "Hardware", "Fasteners", 85, 47, date(2023, 5, 1), "mature", 120, 35, *SUPPLIERS[0]),
    Product("Widget Beta", "SKU002", "Hardware", "Fasteners", 95, 54, date(2023, 8, 1), "mature", 100, 30, *SUPPLIERS[0]),
    Product("Widget Gamma", "SKU003", "Hardware", "Tools", 220, 140, date(2024, 2, 15), "growth", 60, 25, *SUPPLIERS[1]),
    Product("Widget Delta", "SKU004", "Hardware", "Tools", 310, 205, date(2024, 7, 20), "growth", 40, 20, *SUPPLIERS[1]),
    Product("Widget Echo", "SKU005", "Accessories", "Cables", 40, 18, date(2022, 9, 1), "mature", 200, 40, *SUPPLIERS[2]),
    Product("Widget Flux", "SKU006", "Accessories", "Cables", 55, 24, date(2025, 1, 5), "new", 150, 45, *SUPPLIERS[2]),
    Product("Widget Nova", "SKU007", "Accessories", "Batteries", 125, 73, date(2024, 11, 1), "growth", 70, 28, *SUPPLIERS[3]),
    Product("Widget Orion", "SKU008", "Electronics", "Sensors", 480, 310, date(2023, 3, 10), "mature", 35, 18, *SUPPLIERS[4]),
    Product("Widget Pulse", "SKU009", "Electronics", "Sensors", 525, 345, date(2025, 3, 1), "new", 30, 16, *SUPPLIERS[4]),
    Product("Widget Quantum", "SKU010", "Electronics", "Controllers", 760, 510, date(2022, 11, 15), "declining", 25, 20, *SUPPLIERS[4]),
    Product("Widget Rift", "SKU011", "Packaging", "Boxes", 18, 8, date(2022, 1, 1), "mature", 300, 50, *SUPPLIERS[3]),
    Product("Widget Spark", "SKU012", "Packaging", "Labels", 12, 4, date(2023, 6, 1), "mature", 400, 60, *SUPPLIERS[3]),
]


SEASONALITY = {
    1: 0.95,
    2: 0.92,
    3: 1.00,
    4: 1.03,
    5: 0.98,
    6: 0.93,
    7: 0.97,
    8: 1.04,
    9: 1.08,
    10: 1.12,
    11: 1.20,
    12: 1.35,
}


def daterange_days(start: date, end: date) -> int:
    return (end - start).days


def make_customers(n: int) -> pd.DataFrame:
    tiers = ["SMB", "Mid-Market", "Enterprise", "Key Account"]
    tier_weights = [0.55, 0.25, 0.15, 0.05]
    rows = []
    for idx in range(1, n + 1):
        tier = random.choices(tiers, weights=tier_weights, k=1)[0]
        if tier in {"Enterprise", "Key Account"}:
            name = fake.company()
        else:
            name = f"{fake.last_name()} Trading"
        rows.append(
            {
                "customer_id": f"CUST{idx:05d}",
                "customer_name": name,
                "customer_tier": tier,
                "region": random.choice(REGIONS),
                "channel_preference": random.choice(CHANNELS),
                "payment_terms": random.choice(PAYMENT_TERMS),
                "account_manager": random.choice(SALES_REPS),
            }
        )
    return pd.DataFrame(rows)


def random_order_date() -> date:
    offset = random.randint(0, daterange_days(START_DATE, END_DATE))
    return START_DATE + timedelta(days=offset)


def product_demand_multiplier(product: Product, order_date: date) -> float:
    month_factor = SEASONALITY[order_date.month]
    lifecycle_factor = {
        "new": 1.15,
        "growth": 1.10,
        "mature": 1.00,
        "declining": 0.82,
    }[product.lifecycle_stage]

    months_since_launch = max(0, (order_date.year - product.launch_date.year) * 12 + (order_date.month - product.launch_date.month))
    launch_boost = 1.0
    if product.lifecycle_stage == "new" and months_since_launch <= 3:
        launch_boost = 1.35
    elif product.lifecycle_stage == "growth" and months_since_launch <= 6:
        launch_boost = 1.15

    return month_factor * lifecycle_factor * launch_boost


def quantity_for(product: Product, tier: str, channel: str, order_date: date) -> int:
    base = {
        "Hardware": 9,
        "Accessories": 14,
        "Electronics": 4,
        "Packaging": 25,
    }[product.category]
    tier_mult = {"SMB": 1.0, "Mid-Market": 1.5, "Enterprise": 2.2, "Key Account": 3.0}[tier]
    channel_mult = {"Retail": 0.8, "Wholesale": 1.8, "Ecommerce": 0.7, "Distributor": 2.4}[channel]
    demand = base * tier_mult * channel_mult * product_demand_multiplier(product, order_date)
    qty = max(1, int(np.random.poisson(lam=max(1.0, demand))))
    return qty


def unit_price_for(product: Product, tier: str, channel: str, order_date: date) -> float:
    tier_discount = {"SMB": 0.00, "Mid-Market": 0.04, "Enterprise": 0.08, "Key Account": 0.12}[tier]
    channel_discount = {"Retail": 0.00, "Wholesale": 0.05, "Ecommerce": 0.02, "Distributor": 0.09}[channel]
    season_adj = 0.03 if order_date.month in {11, 12} else 0.00
    promo_adj = random.choice([0.00, 0.00, 0.00, -0.03, -0.05, 0.02])
    noise = random.uniform(-0.025, 0.025)
    factor = 1 - tier_discount - channel_discount + season_adj + promo_adj + noise
    return round(max(product.base_price * 0.7, product.base_price * factor), 2)


def maybe_make_messy(value, field_name: str):
    if value is None:
        return value

    if field_name == "order_date" and random.random() < 0.10:
        formats = ["%Y/%m/%d", "%d-%m-%Y", "%m/%d/%Y", "%Y-%m-%d"]
        return value.strftime(random.choice(formats))

    if field_name in {"unit_price", "sales_amount", "unit_cost", "gross_profit"} and random.random() < 0.10:
        currency = random.choice(["R", "$", ""])
        return f"{currency}{value:,.2f}"

    if isinstance(value, str) and random.random() < 0.03:
        return f" {value}  "

    return value


def generate_sales_data(customers: pd.DataFrame, n_rows: int = NUM_SALES_ROWS) -> pd.DataFrame:
    rows = []

    for i in range(1, n_rows + 1):
        product = random.choice(PRODUCTS)
        customer = customers.sample(1).iloc[0]
        order_date = random_order_date()
        channel = customer["channel_preference"]
        qty = quantity_for(product, customer["customer_tier"], channel, order_date)
        unit_price = unit_price_for(product, customer["customer_tier"], channel, order_date)
        unit_cost = round(product.base_cost * random.uniform(0.96, 1.05), 2)
        status = random.choices(ORDER_STATUSES, weights=[78, 8, 5, 4, 3, 2], k=1)[0]
        promotion = random.choices(PROMOTIONS, weights=[55, 12, 10, 13, 10], k=1)[0]

        if status == "Cancelled":
            qty = 0
        if status == "Returned":
            qty = -max(1, int(qty * random.uniform(0.2, 0.8)))

        sales_amount = round(qty * unit_price, 2)
        gross_profit = round(qty * (unit_price - unit_cost), 2)
        order_id = f"ORD-{order_date.strftime('%Y%m')}-{i:06d}"
        invoice_id = f"INV-{order_date.strftime('%Y%m')}-{i:06d}"
        warehouse = random.choice(WAREHOUSES)
        currency = random.choices(CURRENCIES, weights=[92, 8], k=1)[0]
        exchange_rate = 1.0 if currency == "ZAR" else round(random.uniform(17.5, 19.8), 4)
        sales_rep = customer["account_manager"]
        return_reason = random.choice(RETURN_REASONS) if status == "Returned" else ""

        row = {
            "Order Date": maybe_make_messy(order_date, "order_date"),
            "Order ID": order_id,
            "Invoice No": invoice_id,
            "Product Name": maybe_make_messy(product.product_name, "product_name"),
            "SKU": product.sku,
            "Category": product.category,
            "Sub Category": product.subcategory,
            "Customer ID": customer["customer_id"],
            "Customer": maybe_make_messy(customer["customer_name"], "customer"),
            "Customer Tier": customer["customer_tier"],
            "Region": customer["region"],
            "Sales Channel": channel,
            "Warehouse": warehouse,
            "Sales Rep": sales_rep,
            "Qty": qty,
            "Unit Price": maybe_make_messy(unit_price, "unit_price"),
            "Unit Cost": maybe_make_messy(unit_cost, "unit_cost"),
            "Sales Amt": maybe_make_messy(sales_amount, "sales_amount"),
            "Gross Profit": maybe_make_messy(gross_profit, "gross_profit"),
            "Currency": currency,
            "Exchange Rate": exchange_rate,
            "Promotion": promotion,
            "Order Status": status,
            "Payment Terms": customer["payment_terms"],
            "Return Reason": return_reason,
            "Delivery Days": max(1, int(np.random.normal(loc=product.lead_time_days / 2, scale=3))),
            "Notes": random.choice(["", "rush delivery", "manual correction", "VIP customer", "promo order"]),
        }

        if random.random() < 0.025:
            row["Customer"] = ""
        if random.random() < 0.02:
            row["Order Date"] = ""
        if random.random() < 0.01:
            row["Qty"] = -abs(int(row["Qty"]) or 1)
        if random.random() < 0.012:
            row["Sales Amt"] = 0
        if random.random() < 0.008:
            row["SKU"] = ""
        if random.random() < 0.006:
            row["Category"] = random.choice(["Hardware ", " accessories", "Elec", "Packaging"])

        rows.append(row)

        if random.random() < 0.006:
            dup = row.copy()
            dup["Notes"] = "possible duplicate"
            rows.append(dup)

    return pd.DataFrame(rows)


def generate_inventory_snapshot(sales_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    sales_df = sales_df.copy()
    sales_df["Order Date"] = pd.to_datetime(sales_df["Order Date"], errors="coerce")
    sales_df["Qty"] = pd.to_numeric(sales_df["Qty"], errors="coerce")

    for product in PRODUCTS:
        recent_sales = sales_df[
            (sales_df["SKU"] == product.sku)
            & (sales_df["Order Date"] >= pd.Timestamp("2025-10-01"))
            & (sales_df["Order Date"] <= pd.Timestamp("2025-12-31"))
        ]
        monthly_velocity = max(1.0, recent_sales["Qty"].fillna(0).clip(lower=0).sum() / 3.0)

        for warehouse in WAREHOUSES:
            demand_factor = random.uniform(0.7, 1.4)
            stock_on_hand = int(max(0, monthly_velocity * (product.target_days_cover / 30) * demand_factor))
            stock_on_order = int(max(0, monthly_velocity * random.uniform(0.1, 0.8)))
            reserved_stock = int(max(0, stock_on_hand * random.uniform(0.02, 0.18)))
            available_stock = stock_on_hand - reserved_stock
            inventory_value = round(stock_on_hand * product.base_cost, 2)
            stock_days_cover = round((stock_on_hand / max(monthly_velocity, 1.0)) * 30, 1)
            reorder_qty = max(0, product.reorder_point - available_stock)
            aging_bucket = random.choices(
                ["0-30 days", "31-60 days", "61-90 days", "90+ days"],
                weights=[35, 30, 20, 15],
                k=1,
            )[0]

            row = {
                "Snapshot Date": random.choice(["2025-12-31", "31/12/2025", "2025/12/31"]),
                "Warehouse": warehouse,
                "Product": product.product_name,
                "Product Code": product.sku,
                "Category": product.category,
                "Sub Category": product.subcategory,
                "Supplier ID": product.supplier_id,
                "Supplier": product.supplier_name,
                "Lead Time Days": product.lead_time_days,
                "Stock": stock_on_hand,
                "Reserved Stock": reserved_stock,
                "Available Stock": available_stock,
                "Qty On Order": stock_on_order,
                "Reorder Point": product.reorder_point,
                "Suggested Reorder Qty": reorder_qty,
                "Avg Monthly Demand": round(monthly_velocity, 1),
                "Days Cover": stock_days_cover,
                "Unit Cost": maybe_make_messy(product.base_cost, "unit_cost"),
                "Inventory Value": maybe_make_messy(inventory_value, "sales_amount"),
                "Aging Bucket": aging_bucket,
                "Lifecycle Stage": product.lifecycle_stage,
                "Status Notes": random.choice(["", "cycle count pending", "slow moving", "high priority item"]),
            }

            if random.random() < 0.08:
                row["Stock"] = max(0, int(row["Stock"] * random.uniform(1.8, 3.5)))
                row["Status Notes"] = "possible overstock"
            if random.random() < 0.10:
                row["Stock"] = max(0, int(row["Stock"] * random.uniform(0.0, 0.25)))
                row["Status Notes"] = "possible stockout risk"
            if random.random() < 0.03:
                row["Stock"] = -abs(int(row["Stock"]))
            if random.random() < 0.03:
                row["Reorder Point"] = None
            if random.random() < 0.02:
                row["Product"] = ""
            if random.random() < 0.02:
                row["Inventory Value"] = ""

            rows.append(row)

    return pd.DataFrame(rows)


def generate_master_files(customers: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    product_rows = []
    for product in PRODUCTS:
        product_rows.append(
            {
                "SKU": product.sku,
                "Product Name": product.product_name,
                "Category": product.category,
                "Sub Category": product.subcategory,
                "Launch Date": product.launch_date.isoformat(),
                "Lifecycle Stage": product.lifecycle_stage,
                "Base Price": product.base_price,
                "Base Cost": product.base_cost,
                "Supplier ID": product.supplier_id,
                "Supplier": product.supplier_name,
                "Lead Time Days": product.lead_time_days,
                "Reorder Point": product.reorder_point,
                "Target Days Cover": product.target_days_cover,
            }
        )
    return customers.copy(), pd.DataFrame(product_rows)


def write_outputs(output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    customers = make_customers(NUM_CUSTOMERS)
    sales = generate_sales_data(customers, NUM_SALES_ROWS)
    inventory = generate_inventory_snapshot(sales)
    customer_master, product_master = generate_master_files(customers)

    sales_csv = output_dir / "enterprise_sales_messy.csv"
    inventory_csv = output_dir / "enterprise_inventory_messy.csv"
    customer_csv = output_dir / "customer_master.csv"
    product_csv = output_dir / "product_master.csv"
    excel_file = output_dir / "enterprise_test_pack.xlsx"

    sales.to_csv(sales_csv, index=False)
    inventory.to_csv(inventory_csv, index=False)
    customer_master.to_csv(customer_csv, index=False)
    product_master.to_csv(product_csv, index=False)

    with pd.ExcelWriter(excel_file, engine="openpyxl") as writer:
        sales.to_excel(writer, sheet_name="Sales_Messy", index=False)
        inventory.to_excel(writer, sheet_name="Inventory_Messy", index=False)
        customer_master.to_excel(writer, sheet_name="Customer_Master", index=False)
        product_master.to_excel(writer, sheet_name="Product_Master", index=False)

    return [sales_csv, inventory_csv, customer_csv, product_csv, excel_file]


def main() -> None:
    output_dir = Path("generated_test_data")
    files = write_outputs(output_dir)

    print("Generated enterprise-level test data:")
    for file in files:
        print(f"- {file}")

    print("\nDataset characteristics:")
    print("- 25,000+ sales rows with duplicates and messy ERP-style formatting")
    print("- Multi-warehouse inventory snapshot with stock risks and overstock cases")
    print("- Customer and product master data for joins and validation")
    print("- Seasonality, returns, promotions, tiers, channels, supplier lead times")


if __name__ == "__main__":
    main()
