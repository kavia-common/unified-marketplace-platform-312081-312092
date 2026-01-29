from decimal import Decimal

from sqlalchemy.orm import Session

from src.api.auth import hash_password
from src.api.models import User, UserRole, Store, Product, Coupon


# PUBLIC_INTERFACE
def seed_if_empty(db: Session) -> None:
    """Seed minimal demo data if the DB is empty (idempotent-ish)."""
    existing = db.query(User).count()
    if existing > 0:
        return

    admin = User(
        email="admin@example.com",
        hashed_password=hash_password("password"),
        name="Admin",
        role=UserRole.admin,
        is_active=True,
    )
    vendor = User(
        email="vendor@example.com",
        hashed_password=hash_password("password"),
        name="Vendor",
        role=UserRole.vendor,
        is_active=True,
    )
    customer = User(
        email="user@example.com",
        hashed_password=hash_password("password"),
        name="Customer",
        role=UserRole.user,
        is_active=True,
    )
    db.add_all([admin, vendor, customer])
    db.flush()

    store1 = Store(owner_user_id=vendor.id, name="Vendor Store", description="Demo vendor store", is_active=True)
    db.add(store1)
    db.flush()

    p1 = Product(
        store_id=store1.id,
        name="Blue T-Shirt",
        description="Soft cotton t-shirt",
        price=Decimal("19.99"),
        currency="USD",
        sku="TSHIRT-BLUE-001",
        image_url=None,
        inventory_qty=100,
        is_active=True,
    )
    p2 = Product(
        store_id=store1.id,
        name="Coffee Mug",
        description="Ceramic mug",
        price=Decimal("12.50"),
        currency="USD",
        sku="MUG-COFFEE-001",
        image_url=None,
        inventory_qty=250,
        is_active=True,
    )
    db.add_all([p1, p2])

    coupon = Coupon(code="WELCOME10", percent_off=10, is_active=True, expires_at=None)
    db.add(coupon)

    db.commit()
