"""
Construcción del grafo conversacional usando LangGraph.
"""

from langgraph.graph import StateGraph, END
from graph.state import ConversationState
from graph import nodes
from graph import edges


def create_shopping_cart_graph() -> StateGraph:
    """
    Crea el grafo del chatbot.
    
    Flujo:
    1. welcome (inicio)
    2. detect_intent
    3. Routing según intención: browse/manage_cart/view_cart/checkout
    4. Volver a detect_intent o END
    """
    graph = StateGraph(ConversationState)
    
    # Agregar todos los nodos
    graph.add_node("detect_intent", nodes.detect_intent_node)
    graph.add_node("browse", nodes.browse_products_node)
    graph.add_node("manage_cart", nodes.manage_cart_node)
    graph.add_node("view_cart", nodes.view_cart_node)
    graph.add_node("checkout", nodes.checkout_node)
    graph.add_node("out_of_context", nodes.out_of_context_node)
    
    # Punto de entrada: detección de intención
    graph.set_entry_point("detect_intent")
    
    # Desde detect_intent → routing por intención
    graph.add_conditional_edges(
        "detect_intent",
        edges.route_by_intent,
        {
            "browse": "browse",
            "manage_cart": "manage_cart",
            "view_cart": "view_cart",
            "checkout": "checkout",
            "out_of_context": "out_of_context",
            "END": END,
        }
    )
    
    # Desde browse → volver a detect_intent o END
    graph.add_conditional_edges(
        "browse",
        edges.should_continue,
        {
            "detect_intent": "detect_intent",
            "END": END,
        }
    )
    
    # Desde manage_cart → volver a detect_intent o END
    graph.add_conditional_edges(
        "manage_cart",
        edges.should_continue,
        {
            "detect_intent": "detect_intent",
            "END": END,
        }
    )
    
    # Desde view_cart → volver a detect_intent o END
    graph.add_conditional_edges(
        "view_cart",
        edges.should_continue,
        {
            "detect_intent": "detect_intent",
            "END": END,
        }
    )
    
    # Desde checkout → volver a detect_intent o END
    graph.add_conditional_edges(
        "checkout",
        edges.should_continue,
        {
            "detect_intent": "detect_intent",
            "END": END,
        }
    )
    
    # Desde out_of_context → volver a detect_intent o END
    graph.add_conditional_edges(
        "out_of_context",
        edges.should_continue,
        {
            "detect_intent": "detect_intent",
            "END": END,
        }
    )
    
    # Compilar el grafo
    return graph.compile()


def run_conversation_turn(state: ConversationState) -> ConversationState:
    """
    Ejecuta un turno de conversación en el grafo.
    
    Args:
        state: Estado actual de la conversación        
    Returns:
        Estado actualizado después de procesar el mensaje
    """
    graph = create_shopping_cart_graph()
    result = graph.invoke(state)
    return result
