import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from pydantic import BaseModel, EmailStr, Field

from src.api.models import UserRole, OrderStatus, PaymentStatus


class ApiMessage(BaseModel):
    message: str = Field(..., description="Human-readable message.")


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token.")
    token_type: str = Field("bearer", description="Token type (always 'bearer').")


class RegisterRequest(BaseModel):
    email: EmailStr = Field(..., description="User email, unique.")
    password: str = Field(..., min_length=6, description="User password (min 6 chars).")
    name: Optional[str] = Field(None, description="Display name.")
    role: UserRole = Field(UserRole.user, description="Role for the new user.")


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="User email.")
    password: str = Field(..., description="User password.")


class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    name: Optional[str]
    role: UserRole
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class StoreOut(BaseModel):
    id: uuid.UUID
    owner_user_id: uuid.UUID
    name: str
    description: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ProductOut(BaseModel):
    id: uuid.UUID
    store_id: uuid.UUID
    name: str
    description: Optional[str]
    price: Decimal
    currency: str
    sku: Optional[str]
    image_url: Optional[str]
    inventory_qty: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class CartItemOut(BaseModel):
    id: uuid.UUID
    product: ProductOut
    quantity: int

    class Config:
        from_attributes = True


class CartOut(BaseModel):
    items: List[CartItemOut] = Field(default_factory=list)
    subtotal: Decimal = Field(0, description="Subtotal across all items (before discounts).")
    currency: str = Field("USD")


class CartAddItemRequest(BaseModel):
    product_id: uuid.UUID = Field(..., description="Product to add to cart.")
    quantity: int = Field(1, ge=1, le=999, description="Quantity to add.")


class CartUpdateItemRequest(BaseModel):
    quantity: int = Field(..., ge=0, le=999, description="Quantity; 0 removes the item.")


class OrderItemOut(BaseModel):
    id: uuid.UUID
    store_id: uuid.UUID
    product_id: uuid.UUID
    quantity: int
    unit_price: Decimal
    line_total: Decimal

    class Config:
        from_attributes = True


class PaymentOut(BaseModel):
    id: uuid.UUID
    provider: str
    provider_reference: Optional[str]
    amount: Decimal
    currency: str
    status: PaymentStatus
    created_at: datetime

    class Config:
        from_attributes = True


class OrderOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    status: OrderStatus
    currency: str
    subtotal: Decimal
    discount_total: Decimal
    total: Decimal
    created_at: datetime
    updated_at: datetime
    items: List[OrderItemOut]
    payments: List[PaymentOut]

    class Config:
        from_attributes = True
