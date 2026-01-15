"""
Tests de nodos y transiciones con LLM mockeado.
Estos tests verifican el comportamiento de los nodos sin hacer llamadas reales a la API.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from langchain_core.messages import AIMessage, HumanMessage

from graph.state import (
    create_initial_state,
    UserIntent,
    ConversationStage
)
from graph.nodes import (
    detect_intent_node,
    browse_products_node,
    view_cart_node,
)
from graph.edges import route_by_intent
from models.product import Product
from models.cart import ShoppingCart


# ===== TEST 1: Detección de intención mockeada =====
@patch('graph.nodes.get_llm')
def test_detect_intent_with_mocked_llm(mock_get_llm):
    """Test: detección de intención con LLM mockeado."""
    # Configurar mock del LLM
    mock_llm = Mock()
    mock_response = Mock()
    mock_response.content = "BROWSE"
    mock_llm.invoke.return_value = mock_response
    mock_get_llm.return_value = mock_llm
    
    # Crear estado con múltiples mensajes (para evitar el welcome)
    state = create_initial_state(session_id="test_001")
    state["messages"].append(AIMessage(content="Bienvenida inicial"))
    state["messages"].append(HumanMessage(content="muéstrame los productos"))
    state["stage"] = ConversationStage.SHOPPING
    
    # Ejecutar nodo
    result = detect_intent_node(state)
    
    # Verificar que se detectó la intención correcta
    assert result["current_intent"] == UserIntent.BROWSE
    assert mock_llm.invoke.called


# ===== TEST 2: Navegación de productos mockeada =====
@patch('graph.nodes.get_catalog_service')
def test_browse_products_with_mocked_catalog(mock_get_catalog):
    """Test: navegación de productos con catálogo mockeado."""
    # Mock del catálogo
    mock_service = Mock()
    mock_products = [
        Product(id="p1", name="Camiseta", price=19.99, category="ropa", stock=10),
        Product(id="p2", name="Pantalón", price=29.99, category="ropa", stock=5),
    ]
    mock_service.get_all_products.return_value = mock_products
    mock_get_catalog.return_value = mock_service
    
    # Crear estado
    state = create_initial_state(session_id="test_002")
    state["messages"].append(HumanMessage(content="ver productos"))
    initial_message_count = len(state["messages"])
    
    # Ejecutar nodo
    result = browse_products_node(state)
    
    # Verificar que se agregó mensaje del bot
    assert len(result["messages"]) == initial_message_count + 1
    last_message = result["messages"][-1]
    assert isinstance(last_message, AIMessage)
    assert "Camiseta" in last_message.content or "productos" in last_message.content.lower()


# ===== TEST 3: Ver carrito =====
def test_view_cart_node():
    """Test: visualización del carrito."""
    # Crear estado con productos en el carrito
    state = create_initial_state(session_id="test_003")
    product = Product(id="p1", name="Test Product", price=25.0, category="test", stock=10)
    state["cart"].add_item(product, quantity=2)
    state["messages"].append(HumanMessage(content="ver carrito"))
    initial_message_count = len(state["messages"])
    
    # Ejecutar nodo
    result = view_cart_node(state)
    
    # Verificar que se agregó mensaje con info del carrito
    assert len(result["messages"]) == initial_message_count + 1
    last_message = result["messages"][-1]
    assert isinstance(last_message, AIMessage)
    assert "$50.0" in last_message.content or "Test Product" in last_message.content


# ===== TEST 4: Edge de routing por intención =====
def test_route_by_intent_edge():
    """Test: routing del edge según la intención del usuario."""
    # Test de diferentes intenciones
    test_cases = [
        (UserIntent.BROWSE, "browse"),
        (UserIntent.MANAGE_CART, "manage_cart"),
        (UserIntent.VIEW_CART, "view_cart"),
        (UserIntent.CHECKOUT, "checkout"),
        (UserIntent.OUT_OF_CONTEXT, "out_of_context"),
        (UserIntent.EXIT, "END"),
        (UserIntent.UNKNOWN, "END"),
    ]
    
    for intent, expected_route in test_cases:
        state = create_initial_state()
        state["current_intent"] = intent
        
        result = route_by_intent(state)
        
        assert result == expected_route, f"Intent {intent} should route to {expected_route}"


# ===== TEST 5: Operaciones del carrito directas =====
def test_cart_operations_in_state():
    """Test: operaciones del carrito en el estado del grafo."""
    # Crear estado inicial
    state = create_initial_state(session_id="test_005")
    
    # Verificar carrito vacío
    assert state["cart"].is_empty()
    assert state["cart"].get_total() == 0.0
    
    # Añadir productos
    p1 = Product(id="p1", name="Producto 1", price=10.0, category="test", stock=10)
    p2 = Product(id="p2", name="Producto 2", price=20.0, category="test", stock=10)
    
    state["cart"].add_item(p1, quantity=2)
    state["cart"].add_item(p2, quantity=1)
    
    # Verificar totales
    assert state["cart"].get_item_count() == 3
    assert state["cart"].get_total() == 40.0
    assert not state["cart"].is_empty()
    
    # Actualizar cantidad
    state["cart"].update_quantity("p1", 5)
    assert state["cart"].get_item_count() == 6
    assert state["cart"].get_total() == 70.0
    
    # Eliminar producto
    state["cart"].remove_item("p2")
    assert state["cart"].get_item_count() == 5
    assert state["cart"].get_total() == 50.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
