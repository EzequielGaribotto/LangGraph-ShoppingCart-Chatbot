"""
Tests simplificados del proyecto (solo 5 tests básicos).
Cubre las operaciones esenciales del carrito y flujo principal.
"""

import pytest
from models.cart import ShoppingCart
from models.product import Product
from models.order import Order
from graph.state import (
    create_initial_state,
    UserIntent,
    ConversationStage
)


# ===== TEST 1: Añadir productos al carrito =====
def test_add_product_to_cart():
    """Test básico: añadir un producto al carrito."""
    cart = ShoppingCart()
    product = Product(
        id="prod_001",
        name="Camiseta Test",
        price=19.99,
        category="ropa",
        stock=50
    )
    
    cart.add_item(product, quantity=2)
    
    assert not cart.is_empty()
    assert cart.get_item_count() == 2
    assert cart.get_total() == 39.98


# ===== TEST 2: Eliminar productos del carrito =====
def test_remove_product_from_cart():
    """Test básico: eliminar un producto del carrito."""
    cart = ShoppingCart()
    product = Product(id="prod_001", name="Test", price=10.0, category="test", stock=10)
    
    cart.add_item(product, quantity=3)
    cart.remove_item("prod_001")
    
    assert cart.is_empty()
    assert cart.get_total() == 0.0


# ===== TEST 3: Calcular total del carrito =====
def test_cart_total_calculation():
    """Test básico: cálculo correcto del total del carrito."""
    cart = ShoppingCart()
    p1 = Product(id="p1", name="Producto 1", price=10.0, category="test", stock=10)
    p2 = Product(id="p2", name="Producto 2", price=20.0, category="test", stock=10)
    
    cart.add_item(p1, quantity=2)  # 20.0
    cart.add_item(p2, quantity=1)  # 20.0
    
    assert cart.get_total() == 40.0


# ===== TEST 4: Crear una orden desde el carrito =====
def test_create_order_from_cart():
    """Test básico: creación de una orden desde el carrito."""
    cart = ShoppingCart()
    product = Product(id="p1", name="Test", price=50.0, category="test", stock=10)
    cart.add_item(product, quantity=2)
    
    order = Order.create_from_cart(
        cart=cart,
        customer_name="Juan Pérez",
        customer_city="Madrid"
    )
    
    assert order.customer_name == "Juan Pérez"
    assert order.customer_city == "Madrid"
    assert order.total == 100.0
    assert not order.cart.is_empty()


# ===== TEST 5: Estado inicial del grafo =====
def test_initial_state_creation():
    """Test básico: creación del estado inicial del grafo."""
    state = create_initial_state(session_id="test_123")
    
    assert state["session_id"] == "test_123"
    assert state["cart"].is_empty()
    assert state["current_intent"] == UserIntent.BROWSE
    assert state["stage"] == ConversationStage.WELCOME
    assert state["customer_name"] is None
    assert state["customer_city"] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
