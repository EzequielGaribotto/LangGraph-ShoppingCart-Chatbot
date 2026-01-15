"""
Definición de estados para el grafo conversacional de LangGraph.
"""

from typing import TypedDict, List, Optional, Annotated
from enum import Enum
from operator import add
from langchain_core.messages import BaseMessage
from models.cart import ShoppingCart
from models.order import Order


class UserIntent(str, Enum):
    """
    Intenciones del usuario.
    """
    BROWSE = "browse"  # Ver productos
    MANAGE_CART = "manage_cart"  # Añadir/quitar productos del carrito
    VIEW_CART = "view_cart"  # Ver carrito
    CHECKOUT = "checkout"  # Finalizar compra
    OUT_OF_CONTEXT = "out_of_context"  # Preguntas fuera de contexto
    UNKNOWN = "unknown"  # No entendido
    EXIT = "exit"  # Salir


class ConversationStage(str, Enum):
    """
    Etapas del flujo de compra.
    """
    WELCOME = "welcome"  # Bienvenida
    SHOPPING = "shopping"  # Navegando y comprando
    CHECKOUT = "checkout"  # Datos de envío
    COMPLETED = "completed"  # Compra finalizada
    ERROR = "error"  # Error


class ConversationState(TypedDict):
    """
    Estado de la conversación del chatbot.
    
    Attributes:
        messages: Lista de mensajes de la conversación
        cart: Carrito de compras actual
        current_intent: Intención detectada del usuario
        stage: Etapa actual del flujo
        last_search_results: Productos encontrados
        last_product_id: ID del último producto mencionado/agregado
        customer_name: Nombre del cliente
        customer_city: Ciudad del cliente
        order: Orden creada (si existe)
        session_id: ID de sesión
    """
    messages: Annotated[List[BaseMessage], add]
    cart: ShoppingCart
    current_intent: UserIntent
    stage: ConversationStage
    last_search_results: Optional[List[dict]]
    last_product_id: Optional[str]
    customer_name: Optional[str]
    customer_city: Optional[str]
    order: Optional[Order]
    session_id: str


def create_initial_state(session_id: Optional[str] = None) -> ConversationState:
    """Crea el estado inicial para una nueva conversación."""
    import uuid
    if session_id is None:
        session_id = str(uuid.uuid4())
    
    return ConversationState(
        messages=[],
        cart=ShoppingCart(),
        current_intent=UserIntent.BROWSE,
        stage=ConversationStage.WELCOME,
        last_search_results=None,
        last_product_id=None,
        customer_name=None,
        customer_city=None,
        order=None,
        session_id=session_id
    )


def is_cart_ready_for_checkout(state: ConversationState) -> bool:
    """Verifica si el carrito tiene productos."""
    return not state["cart"].is_empty()


def is_order_info_complete(state: ConversationState) -> bool:
    """Verifica si se tiene nombre y ciudad."""
    return (
        state.get("customer_name") is not None
        and state.get("customer_city") is not None
        and len(state.get("customer_name", "").strip()) > 0
        and len(state.get("customer_city", "").strip()) > 0
    )


def get_last_user_message(state: ConversationState) -> str:
    """Obtiene el último mensaje del usuario."""
    for message in reversed(state["messages"]):
        if hasattr(message, "type") and message.type == "human":
            return message.content
    return ""
