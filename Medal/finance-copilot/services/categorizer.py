from __future__ import annotations

RULES: list[tuple[tuple[str, ...], str]] = [
    (("swiggy", "zomato", "uber eats", "dominos", "mcdonald", "food", "restaurant"), "Food"),
    (("uber", "ola", "rapido", "metro", "fuel", "petrol", "diesel", "parking"), "Travel"),
    (("amazon", "flipkart", "myntra", "shopping", "mall", "store"), "Shopping"),
    (("netflix", "spotify", "prime video", "hotstar", "subscription", "saas"), "Subscriptions"),
    (("rent", "housing", "maintenance"), "Housing"),
    (("electric", "water bill", "gas bill", "utility"), "Utilities"),
    (("hospital", "pharmacy", "medical", "doctor", "clinic"), "Healthcare"),
    (("school", "tuition", "course", "udemy", "coursera"), "Education"),
    (("atm", "withdraw", "cash"), "Cash"),
    (("salary", "payroll", "stipend", "reimbursement"), "Income"),
    (("emi", "loan", "bank charge", "interest"), "Finance"),
]


def categorize(description: str) -> str:
    text = description.lower()
    for keywords, category in RULES:
        if any(k in text for k in keywords):
            return category
    return "Other"


def apply_categories(records: list[dict]) -> list[dict]:
    out = []
    for r in records:
        row = dict(r)
        desc = row.pop("desc", row.get("description", ""))
        row["description"] = str(desc)
        row["category"] = categorize(row["description"])
        out.append(row)
    return out
