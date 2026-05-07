import pandas as pd

def get_demo_sales_data() -> pd.DataFrame:
    data = [
        ["2025-01-05", "Widget A", "WA-001", "Acme", "C001", 10, 100, 60],
        ["2025-01-12", "Widget B", "WB-001", "Beta", "C002", 5, 200, 150],
        ["2025-02-03", "Widget A", "WA-001", "Acme", "C001", 8, 100, 60],
        ["2025-02-15", "Widget C", "WC-001", "Gamma", "C003", 3, 50, 80],
        ["2025-03-01", "Widget B", "WB-001", "Beta", "C002", 7, 200, 150],
    ]

    return pd.DataFrame(
        data,
        columns=[
            "Order Date",
            "Product Name",
            "SKU Code",
            "Client Name",
            "Client ID",
            "Qty Sold",
            "Selling Price",
            "Unit Cost",
        ],
    )


def get_demo_inventory_data() -> pd.DataFrame:
    data = [
        ["Widget A", "WA-001", "Hardware", "Supplier X", "S001", 120, 50, 40],
        ["Widget B", "WB-001", "Hardware", "Supplier Y", "S002", 30, 40, 150],
        ["Widget C", "WC-001", "Accessories", "Supplier Z", "S003", 5, 20, 80],
        ["Widget D", "WD-001", "Accessories", "Supplier Z", "S003", 0, 15, 60],
    ]

    return pd.DataFrame(
        data,
        columns=[
            "Product Name",
            "SKU Code",
            "Category",
            "Supplier",
            "Supplier ID",
            "Stock On Hand",
            "Reorder Level",
            "Cost",
        ],
    )


def get_demo_customer_master() -> pd.DataFrame:
    data = [
        ["C001", "Acme", "Gold", "North", "30 days", "Alice"],
        ["C002", "Beta", "Silver", "South", "15 days", "Bob"],
        ["C003", "Gamma", "Bronze", "West", "Cash", "Charlie"],
    ]

    return pd.DataFrame(
        data,
        columns=[
            "Customer ID",
            "Customer Name",
            "Customer Tier",
            "Region",
            "Payment Terms",
            "Account Manager",
        ],
    )


def get_demo_product_master() -> pd.DataFrame:
    data = [
        ["WA-001", "Widget A", "Hardware", "Core", "Supplier X", "S001", "Active", 10, 50, 60],
        ["WB-001", "Widget B", "Hardware", "Core", "Supplier Y", "S002", "Active", 12, 150, 200],
        ["WC-001", "Widget C", "Accessories", "Add-on", "Supplier Z", "S003", "Active", 7, 80, 50],
        ["WD-001", "Widget D", "Accessories", "Add-on", "Supplier Z", "S003", "Active", 5, 60, 40],
    ]

    return pd.DataFrame(
        data,
        columns=[
            "SKU",
            "Product Name",
            "Category",
            "Subcategory",
            "Supplier",
            "Supplier ID",
            "Lifecycle Stage",
            "Lead Time Days",
            "Base Cost",
            "Base Price",
        ],
    )