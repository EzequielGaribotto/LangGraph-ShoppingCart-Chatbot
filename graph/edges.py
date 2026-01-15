"""
Edges: determinan qué nodo ejecutar siguiente.
"""

from typing import Literal
from graph.state import ConversationState, UserIntent, ConversationStage


def route_by_intent(state: ConversationState) -> Literal["browse", "manage_cart", "view_cart", "checkout", "out_of_context", "END"]:
    """Determina el siguiente nodo basándose en la intención."""
    intent = state.get("current_intent", UserIntent.UNKNOWN)
    
    if intent == UserIntent.EXIT:
        return "END"
    elif intent == UserIntent.BROWSE:
        return "browse"
    elif intent == UserIntent.MANAGE_CART:
        return "manage_cart"
    elif intent == UserIntent.VIEW_CART:
        return "view_cart"
    elif intent == UserIntent.CHECKOUT:
        return "checkout"
    elif intent == UserIntent.OUT_OF_CONTEXT:
        return "out_of_context"
    else:
        # Si no entiende la intención, terminar y esperar siguiente mensaje
        return "END"


def should_continue(state: ConversationState) -> Literal["detect_intent", "END"]:
    """Determina si continuar la conversación o terminar."""
    # Después de procesar cada mensaje del usuario, terminamos
    # El siguiente invoke() del grafo procesará el siguiente mensaje
    return "END"
