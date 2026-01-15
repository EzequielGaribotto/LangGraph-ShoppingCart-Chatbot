"""
Módulo de grafo conversacional con LangGraph.
"""

from graph.state import (
    ConversationState,
    UserIntent,
    ConversationStage,
    create_initial_state,
    is_cart_ready_for_checkout,
    is_order_info_complete,
    get_last_user_message,
)

from graph.nodes import (
    detect_intent_node,
    browse_products_node,
    manage_cart_node,
    view_cart_node,
    checkout_node,
    out_of_context_node,
    get_catalog_service,
)

from graph.edges import (
    route_by_intent,
    should_continue,
)

from graph.builder import create_shopping_cart_graph


__all__ = [
    # State
    "ConversationState",
    "UserIntent",
    "ConversationStage",
    "create_initial_state",
    "is_cart_ready_for_checkout",
    "is_order_info_complete",
    "get_last_user_message",
    # Nodes
    "detect_intent_node",
    "browse_products_node",
    "manage_cart_node",
    "view_cart_node",
    "checkout_node",
    "out_of_context_node",
    "get_catalog_service",
    # Edges
    "route_by_intent",
    "should_continue",
    # Builder
    "create_shopping_cart_graph",
]
