"""
Modelo de Pedido/Orden.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from models.cart import ShoppingCart
import time
import uuid

class Order(BaseModel):
    """
    Representa una orden de compra completada.
    
    Attributes:
        order_id: ID único de la orden
        cart: Carrito de compras asociado
        customer_name: Nombre del cliente
        customer_city: Ciudad del cliente
        total: Total de la orden
        timestamp: Fecha y hora de creación
    """
    
    order_id: str = Field(..., description="ID único de la orden")
    cart: ShoppingCart = Field(..., description="Carrito de compras")
    customer_name: str = Field(..., description="Nombre del cliente", min_length=1)
    customer_city: str = Field(..., description="Ciudad del cliente", min_length=1)
    total: float = Field(..., description="Total de la orden", ge=0)
    timestamp: datetime = Field(default_factory=datetime.now, description="Fecha de creación")
    
    @field_validator('customer_name', 'customer_city')
    @classmethod
    def validate_non_empty_string(cls, v: str) -> str:
        """Valida que los campos de texto no estén vacíos."""
        if not v or not v.strip():
            raise ValueError('El campo no puede estar vacío')
        return v.strip()
    
    @field_validator('cart')
    @classmethod
    def validate_cart_not_empty(cls, v: ShoppingCart) -> ShoppingCart:
        """Valida que el carrito no esté vacío."""
        if v.is_empty():
            raise ValueError('No se puede crear una orden con un carrito vacío')
        return v
    
    @field_validator('total')
    @classmethod
    def validate_total(cls, v: float) -> float:
        """Valida que el total sea no negativo."""
        if v < 0:
            raise ValueError('El total no puede ser negativo')
        return round(v, 2)
    
    @staticmethod
    def generate_order_id() -> str:
        """
        Genera un ID único para la orden usando timestamp + UUID para garantizar unicidad.
        
        Returns:
            ID de orden en formato ORD-YYYYMMDD-HHMMSS-XXX
        """
        now = datetime.now()
        timestamp_str = now.strftime("%Y%m%d-%H%M%S")
        # Usar los primeros 6 dígitos de un UUID para garantizar unicidad
        unique_suffix = str(uuid.uuid4().hex)[:6]
        # Pequeño sleep para asegurar unicidad en caso de llamadas rápidas
        time.sleep(0.001)
        return f"ORD-{timestamp_str}-{unique_suffix}"
    
    @classmethod
    def create_from_cart(
        cls,
        cart: ShoppingCart,
        customer_name: str,
        customer_city: str,
    ) -> "Order":
        """
        Crea una orden desde un carrito.
        
        Args:
            cart: Carrito de compras
            customer_name: Nombre del cliente
            customer_city: Ciudad del cliente
            
        Returns:
            Nueva orden creada
            
        Raises:
            ValueError: Si el carrito está vacío
        """
        if cart.is_empty():
            raise ValueError("No se puede crear una orden con un carrito vacío")
        
        # Crear una copia profunda del carrito para evitar modificaciones
        from copy import deepcopy
        cart_copy = deepcopy(cart)
        
        return cls(
            order_id=cls.generate_order_id(),
            cart=cart_copy,
            customer_name=customer_name,
            customer_city=customer_city,
            total=cart.get_total(),
        )
    
    def __str__(self) -> str:
        """Representación en string de la orden."""
        return (
            f"Orden {self.order_id} - {self.customer_name} "
            f"({self.cart.get_item_count()} items) - ${self.total:.2f}"
        )
    
    def __repr__(self) -> str:
        """Representación técnica de la orden."""
        return (
            f"Order(order_id='{self.order_id}', "
            f"customer='{self.customer_name}', "
            f"total=${self.total:.2f}, "
        )
    
    class Config:
        """Configuración de Pydantic."""
        json_schema_extra = {
            "example": {
                "order_id": "ORD-20260108-143022-123",
                "customer_name": "Juan Pérez",
                "customer_city": "Madrid",
                "total": 39.98,
                "timestamp": "2026-01-08T14:30:22",
                "cart": {
                    "items": {
                        "prod_001": {
                            "product": {
                                "id": "prod_001",
                                "name": "Camiseta Azul",
                                "price": 19.99,
                                "category": "ropa",
                                "description": "Camiseta de algodón",
                                "stock": 50
                            },
                            "quantity": 2
                        }
                    }
                }
            }
        }
