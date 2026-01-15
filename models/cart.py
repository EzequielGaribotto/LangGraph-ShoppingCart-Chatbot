"""
Modelo de Carrito de Compras.
"""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
from models.product import Product


class CartItem(BaseModel):
    """
    Representa un item en el carrito (producto + cantidad).
    
    Attributes:
        product: El producto
        quantity: Cantidad del producto en el carrito
    """
    
    product: Product
    quantity: int = Field(..., description="Cantidad del producto", gt=0)
    
    @field_validator('quantity')
    @classmethod
    def validate_quantity(cls, v: int) -> int:
        """Valida que la cantidad sea positiva."""
        if v <= 0:
            raise ValueError('La cantidad debe ser mayor que 0')
        return v
    
    @property
    def subtotal(self) -> float:
        """Calcula el subtotal de este item (precio * cantidad)."""
        return round(self.product.price * self.quantity, 2)
    
    def __str__(self) -> str:
        """Representación en string del item."""
        return f"{self.product.name} x{self.quantity} = ${self.subtotal:.2f}"
    
    class Config:
        """Configuración de Pydantic."""
        json_schema_extra = {
            "example": {
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


class ShoppingCart(BaseModel):
    """
    Carrito de compras que gestiona los productos seleccionados.
    
    Attributes:
        items: Diccionario de items del carrito (product_id -> CartItem)
    """
    
    items: Dict[str, CartItem] = Field(default_factory=dict)
    
    def add_item(self, product: Product, quantity: int = 1) -> None:
        """
        Añade un producto al carrito o incrementa su cantidad.
        
        Args:
            product: Producto a añadir
            quantity: Cantidad a añadir (default: 1)
            
        Raises:
            ValueError: Si la cantidad es inválida o no hay suficiente stock
        """
        if quantity <= 0:
            raise ValueError("La cantidad debe ser mayor que 0")
        
        if not product.is_available(quantity):
            raise ValueError(f"Stock insuficiente para {product.name}. Disponible: {product.stock}")
        
        if product.id in self.items:
            # Producto ya existe, incrementar cantidad
            new_quantity = self.items[product.id].quantity + quantity
            
            # Verificar stock para la nueva cantidad total
            if not product.is_available(new_quantity):
                raise ValueError(
                    f"Stock insuficiente para {product.name}. "
                    f"Tienes {self.items[product.id].quantity} en el carrito, "
                    f"disponible: {product.stock}"
                )
            
            self.items[product.id].quantity = new_quantity
        else:
            # Nuevo producto
            self.items[product.id] = CartItem(product=product, quantity=quantity)
    
    def remove_item(self, product_id: str) -> None:
        """
        Elimina completamente un producto del carrito.
        
        Args:
            product_id: ID del producto a eliminar
            
        Raises:
            ValueError: Si el producto no está en el carrito
        """
        if product_id not in self.items:
            raise ValueError(f"El producto con ID '{product_id}' no está en el carrito")
        
        del self.items[product_id]
    
    def update_quantity(self, product_id: str, quantity: int) -> None:
        """
        Actualiza la cantidad de un producto en el carrito.
        
        Args:
            product_id: ID del producto
            quantity: Nueva cantidad (si es 0, elimina el producto)
            
        Raises:
            ValueError: Si el producto no está en el carrito o cantidad inválida
        """
        if product_id not in self.items:
            raise ValueError(f"El producto con ID '{product_id}' no está en el carrito")
        
        if quantity < 0:
            raise ValueError("La cantidad no puede ser negativa")
        
        if quantity == 0:
            self.remove_item(product_id)
        else:
            product = self.items[product_id].product
            if not product.is_available(quantity):
                raise ValueError(
                    f"Stock insuficiente para {product.name}. "
                    f"Disponible: {product.stock}"
                )
            self.items[product_id].quantity = quantity
    
    def get_item(self, product_id: str) -> Optional[CartItem]:
        """
        Obtiene un item del carrito por ID de producto.
        
        Args:
            product_id: ID del producto
            
        Returns:
            CartItem si existe, None en caso contrario
        """
        return self.items.get(product_id)
    
    def get_total(self) -> float:
        """
        Calcula el total del carrito.
        
        Returns:
            Total del carrito (suma de todos los subtotales)
        """
        return round(sum(item.subtotal for item in self.items.values()), 2)
    
    def get_item_count(self) -> int:
        """
        Obtiene el número total de items (suma de cantidades).
        
        Returns:
            Número total de items en el carrito
        """
        return sum(item.quantity for item in self.items.values())
    
    def is_empty(self) -> bool:
        """
        Verifica si el carrito está vacío.
        
        Returns:
            True si el carrito está vacío, False en caso contrario
        """
        return len(self.items) == 0
    
    def clear(self) -> None:
        """Vacía completamente el carrito."""
        self.items.clear()
    
    def get_items_list(self) -> List[CartItem]:
        """
        Obtiene una lista de todos los items del carrito.
        
        Returns:
            Lista de CartItems
        """
        return list(self.items.values())
    
    def has_product(self, product_id: str) -> bool:
        """
        Verifica si un producto está en el carrito.
        
        Args:
            product_id: ID del producto
            
        Returns:
            True si el producto está en el carrito, False en caso contrario
        """
        return product_id in self.items
    
    def __str__(self) -> str:
        """Representación en string del carrito."""
        if self.is_empty():
            return "Carrito vacío"
        
        items_str = "\n".join(f"  - {item}" for item in self.items.values())
        return f"Carrito ({self.get_item_count()} items):\n{items_str}\nTotal: ${self.get_total():.2f}"
    
    def __repr__(self) -> str:
        """Representación técnica del carrito."""
        return f"ShoppingCart(items={len(self.items)}, total=${self.get_total():.2f})"
    
    class Config:
        """Configuración de Pydantic."""
        json_schema_extra = {
            "example": {
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
