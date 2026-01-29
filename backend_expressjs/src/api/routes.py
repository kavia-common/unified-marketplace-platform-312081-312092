import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from src.api.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from src.api.db import get_db
from src.api.models import (
    User,
    UserRole,
    Store,
    Product,
    CartItem,
    Order,
    OrderItem,
    OrderStatus,
    PaymentTransaction,
    PaymentStatus,
)
from src.api.schemas import (
    ApiMessage,
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    UserOut,
    StoreOut,
    ProductOut,
    CartOut,
    CartItemOut,
    CartAddItemRequest,
    CartUpdateItemRequest,
    OrderOut,
)

router = APIRouter()


def _calc_cart(db: Session, user_id: uuid.UUID) -> CartOut:
    items = (
        db.query(CartItem)
        .options(joinedload(CartItem.product))
        .filter(CartItem.user_id == user_id)
        .all()
    )
    subtotal = Decimal("0")
    out_items: List[CartItemOut] = []
    for ci in items:
        price = Decimal(str(ci.product.price))
        subtotal += price * ci.quantity
        out_items.append(CartItemOut(id=ci.id, product=ci.product, quantity=ci.quantity))
    return CartOut(items=out_items, subtotal=subtotal, currency="USD")


@router.get(
    "/health",
    response_model=ApiMessage,
    tags=["health"],
    summary="Health check",
    description="Basic health endpoint used by the frontend and platform monitoring.",
    operation_id="health",
)
# PUBLIC_INTERFACE
def health() -> ApiMessage:
    """Health endpoint.

    Returns:
        ApiMessage: Always returns a message if the service is running.
    """
    return ApiMessage(message="Healthy")


@router.post(
    "/auth/register",
    response_model=TokenResponse,
    tags=["auth"],
    summary="Register",
    description="Register a new user and return a JWT access token.",
    operation_id="register",
)
# PUBLIC_INTERFACE
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Register a new user and issue JWT."""
    existing = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered.")

    user = User(
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
        name=payload.name,
        role=payload.role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id, user.role)
    return TokenResponse(access_token=token)


@router.post(
    "/auth/login",
    response_model=TokenResponse,
    tags=["auth"],
    summary="Login",
    description="Authenticate user credentials and return a JWT access token.",
    operation_id="login",
)
# PUBLIC_INTERFACE
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Login and issue JWT."""
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User is inactive.")

    token = create_access_token(user.id, user.role)
    return TokenResponse(access_token=token)


@router.get(
    "/me",
    response_model=UserOut,
    tags=["auth"],
    summary="Get current user profile",
    operation_id="me",
)
# PUBLIC_INTERFACE
def me(user: User = Depends(get_current_user)) -> UserOut:
    """Return authenticated user's profile."""
    return user


@router.get(
    "/stores",
    response_model=list[StoreOut],
    tags=["stores"],
    summary="List stores",
    description="Public store listing used by the storefront.",
    operation_id="listStores",
)
# PUBLIC_INTERFACE
def list_stores(
    q: Optional[str] = None,
    db: Session = Depends(get_db),
) -> list[StoreOut]:
    """List active stores."""
    query = db.query(Store).filter(Store.is_active.is_(True))
    if q:
        query = query.filter(Store.name.ilike(f"%{q}%"))
    return query.order_by(Store.created_at.desc()).all()


@router.get(
    "/stores/{store_id}",
    response_model=StoreOut,
    tags=["stores"],
    summary="Get store details",
    operation_id="getStore",
)
# PUBLIC_INTERFACE
def get_store(store_id: uuid.UUID, db: Session = Depends(get_db)) -> StoreOut:
    """Get store details by id."""
    store = db.query(Store).filter(Store.id == store_id, Store.is_active.is_(True)).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found.")
    return store


@router.get(
    "/products",
    response_model=list[ProductOut],
    tags=["products"],
    summary="List products",
    description="Public product listing used by the storefront.",
    operation_id="listProducts",
)
# PUBLIC_INTERFACE
def list_products(
    store_id: Optional[uuid.UUID] = None,
    q: Optional[str] = None,
    db: Session = Depends(get_db),
) -> list[ProductOut]:
    """List active products (optionally filtered by store and search query)."""
    query = db.query(Product).filter(Product.is_active.is_(True))
    if store_id:
        query = query.filter(Product.store_id == store_id)
    if q:
        query = query.filter(Product.name.ilike(f"%{q}%"))
    return query.order_by(Product.created_at.desc()).all()


@router.get(
    "/products/{product_id}",
    response_model=ProductOut,
    tags=["products"],
    summary="Get product details",
    operation_id="getProduct",
)
# PUBLIC_INTERFACE
def get_product(product_id: uuid.UUID, db: Session = Depends(get_db)) -> ProductOut:
    """Get product details by id."""
    product = db.query(Product).filter(Product.id == product_id, Product.is_active.is_(True)).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")
    return product


@router.get(
    "/cart",
    response_model=CartOut,
    tags=["cart"],
    summary="Get current user's cart",
    operation_id="getCart",
)
# PUBLIC_INTERFACE
def get_cart(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> CartOut:
    """Return the authenticated user's server-side cart (placeholder implementation)."""
    return _calc_cart(db, user.id)


@router.post(
    "/cart/items",
    response_model=CartOut,
    tags=["cart"],
    summary="Add item to cart",
    operation_id="addCartItem",
)
# PUBLIC_INTERFACE
def add_cart_item(
    payload: CartAddItemRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CartOut:
    """Add a product to the cart or increase quantity."""
    product = db.query(Product).filter(Product.id == payload.product_id, Product.is_active.is_(True)).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")

    item = db.query(CartItem).filter(CartItem.user_id == user.id, CartItem.product_id == product.id).first()
    now = datetime.utcnow()
    if item:
        item.quantity += payload.quantity
        item.updated_at = now
    else:
        item = CartItem(user_id=user.id, product_id=product.id, quantity=payload.quantity, created_at=now, updated_at=now)
        db.add(item)

    db.commit()
    return _calc_cart(db, user.id)


@router.patch(
    "/cart/items/{cart_item_id}",
    response_model=CartOut,
    tags=["cart"],
    summary="Update cart item quantity",
    operation_id="updateCartItem",
)
# PUBLIC_INTERFACE
def update_cart_item(
    cart_item_id: uuid.UUID,
    payload: CartUpdateItemRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CartOut:
    """Set cart item quantity. If quantity=0, removes the item."""
    item = db.query(CartItem).filter(CartItem.id == cart_item_id, CartItem.user_id == user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found.")

    if payload.quantity <= 0:
        db.delete(item)
    else:
        item.quantity = payload.quantity
        item.updated_at = datetime.utcnow()

    db.commit()
    return _calc_cart(db, user.id)


@router.post(
    "/orders",
    response_model=OrderOut,
    tags=["orders"],
    summary="Create order from cart",
    description="Creates a multi-vendor order with line items grouped by store via product references. Clears cart.",
    operation_id="createOrderFromCart",
    status_code=status.HTTP_201_CREATED,
)
# PUBLIC_INTERFACE
def create_order_from_cart(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OrderOut:
    """Create an order from current user's cart items."""
    cart_items = (
        db.query(CartItem)
        .options(joinedload(CartItem.product))
        .filter(CartItem.user_id == user.id)
        .all()
    )
    if not cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty.")

    order = Order(
        user_id=user.id,
        status=OrderStatus.pending,
        currency="USD",
        subtotal=Decimal("0"),
        discount_total=Decimal("0"),
        total=Decimal("0"),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(order)
    db.flush()

    subtotal = Decimal("0")
    for ci in cart_items:
        unit_price = Decimal(str(ci.product.price))
        line_total = unit_price * ci.quantity
        subtotal += line_total

        oi = OrderItem(
            order_id=order.id,
            store_id=ci.product.store_id,
            product_id=ci.product.id,
            quantity=ci.quantity,
            unit_price=unit_price,
            line_total=line_total,
        )
        db.add(oi)

    # mock payment record
    payment = PaymentTransaction(
        order_id=order.id,
        provider="mock",
        provider_reference=None,
        amount=subtotal,
        currency="USD",
        status=PaymentStatus.initiated,
    )
    db.add(payment)

    order.subtotal = subtotal
    order.total = subtotal  # no discounts yet
    order.updated_at = datetime.utcnow()

    # clear cart
    for ci in cart_items:
        db.delete(ci)

    db.commit()

    created = (
        db.query(Order)
        .options(joinedload(Order.items), joinedload(Order.payments))
        .filter(Order.id == order.id)
        .first()
    )
    return created


@router.get(
    "/orders",
    response_model=list[OrderOut],
    tags=["orders"],
    summary="List orders for current user (or vendor)",
    description="Users see their orders. Vendors see orders containing their store's items. Admins see all orders.",
    operation_id="listOrders",
)
# PUBLIC_INTERFACE
def list_orders(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[OrderOut]:
    """List orders based on role."""
    base = db.query(Order).options(joinedload(Order.items), joinedload(Order.payments))

    if user.role == UserRole.admin:
        return base.order_by(Order.created_at.desc()).all()

    if user.role == UserRole.vendor:
        # vendor: orders where any order_item.store belongs to the vendor's stores
        store_ids = [s.id for s in db.query(Store.id).filter(Store.owner_user_id == user.id).all()]
        store_ids = [sid for (sid,) in store_ids]  # unpack tuples
        if not store_ids:
            return []
        orders = (
            base.join(OrderItem, OrderItem.order_id == Order.id)
            .filter(OrderItem.store_id.in_(store_ids))
            .order_by(Order.created_at.desc())
            .distinct()
            .all()
        )
        return orders

    # regular user
    return base.filter(Order.user_id == user.id).order_by(Order.created_at.desc()).all()


@router.get(
    "/orders/{order_id}",
    response_model=OrderOut,
    tags=["orders"],
    summary="Get order by id",
    operation_id="getOrder",
)
# PUBLIC_INTERFACE
def get_order(
    order_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OrderOut:
    """Get a specific order enforcing role-based access."""
    order = (
        db.query(Order)
        .options(joinedload(Order.items), joinedload(Order.payments))
        .filter(Order.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")

    if user.role == UserRole.admin:
        return order

    if user.role == UserRole.user and order.user_id == user.id:
        return order

    if user.role == UserRole.vendor:
        store_ids = [sid for (sid,) in db.query(Store.id).filter(Store.owner_user_id == user.id).all()]
        allowed = any(item.store_id in set(store_ids) for item in order.items)
        if allowed:
            return order

    raise HTTPException(status_code=403, detail="Not allowed to access this order.")
