"""
Modelo de Producto para el catálogo de la tienda.
"""
from pydantic import BaseModel, Field, field_validator


class Product(BaseModel):
    """
    Representa un producto en el catálogo de la tienda.
    
    Attributes:
        id: Identificador único del producto
        name: Nombre del producto
        price: Precio del producto (debe ser positivo)
        category: Categoría del producto (ropa, electrónica, hogar, deportes, etc.)
        description: Descripción detallada del producto
        stock: Cantidad disponible en inventario (opcional, default: 100)
    """
    
    id: str = Field(..., description="ID único del producto", min_length=1)
    name: str = Field(..., description="Nombre del producto", min_length=1)
    price: float = Field(..., description="Precio del producto", gt=0)
    category: str = Field(..., description="Categoría del producto")
    description: str = Field(default="", description="Descripción del producto")
    stock: int = Field(default=100, description="Stock disponible", ge=0)
    
    @field_validator('price')
    @classmethod
    def validate_price(cls, v: float) -> float:
        """Valida que el precio sea positivo y tenga máximo 2 decimales."""
        if v <= 0:
            raise ValueError('El precio debe ser mayor que 0')
        # Redondear a 2 decimales
        return round(v, 2)
    
    @field_validator('name', 'category')
    @classmethod
    def validate_non_empty_string(cls, v: str) -> str:
        """Valida que los campos de texto no estén vacíos."""
        if not v or not v.strip():
            raise ValueError('El campo no puede estar vacío')
        return v.strip()
    
    @field_validator('stock')
    @classmethod
    def validate_stock(cls, v: int) -> int:
        """Valida que el stock no sea negativo."""
        if v < 0:
            raise ValueError('El stock no puede ser negativo')
        return v
    
    def is_available(self, quantity: int = 1) -> bool:
        """
        Verifica si hay suficiente stock disponible.
        
        Args:
            quantity: Cantidad solicitada
            
        Returns:
            True si hay suficiente stock, False en caso contrario
        """
        return self.stock >= quantity
    
    def __str__(self) -> str:
        """Representación en string del producto."""
        return f"{self.name} - ${self.price:.2f} ({self.category})"
    
    def __repr__(self) -> str:
        """Representación técnica del producto."""
        return f"Product(id='{self.id}', name='{self.name}', price={self.price})"
    
    class Config:
        """Configuración de Pydantic."""
        json_schema_extra = {
            "example": {
                "id": "prod_001",
                "name": "Camiseta Azul",
                "price": 19.99,
                "category": "ropa",
                "description": "Camiseta de algodón 100% en color azul",
                "stock": 50
            }
        }
