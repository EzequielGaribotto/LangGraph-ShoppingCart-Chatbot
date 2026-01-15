"""Nodos del grafo para el flujo conversacional con LLM."""

import json
import logging
import time
import os
import re
from typing import Dict, Optional
from functools import wraps
from langchain_core.messages import AIMessage
from graph.state import (
    ConversationState,
    UserIntent,
    ConversationStage,
    get_last_user_message,
)
from app.services.catalog_service import CatalogService
from app.config.llm_config import create_llm
from utils.prompts import (
    create_intent_detection_messages,
    create_cart_extraction_messages,
    create_out_of_context_messages,
)
from models.order import Order

logging.basicConfig(
    level=logging.DEBUG if os.getenv("DEBUG") == "True" else logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Singletons
_catalog_service = None
_llm = None


def log_node_execution(func):
    """Decorador para registrar tiempo de ejecución y estado de nodos."""
    @wraps(func)
    def wrapper(state: ConversationState) -> ConversationState:
        node_name = func.__name__
        logger.info(f"🔷 Executing {node_name}")
        start_time = time.time()
        
        try:
            result = func(state)
            elapsed = time.time() - start_time
            logger.info(f"✅ {node_name} completed in {elapsed:.2f}s")
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"❌ {node_name} failed after {elapsed:.2f}s: {e}")
            raise
    
    return wrapper


def get_catalog_service() -> CatalogService:
    """Obtiene o inicializa el servicio de catálogo singleton."""
    global _catalog_service
    if _catalog_service is None:
        _catalog_service = CatalogService()
        _catalog_service.load_catalog()
    return _catalog_service


def get_llm():
    """Obtiene o inicializa el LLM singleton."""
    global _llm
    if _llm is None:
        logger.info("🔧 Initializing LLM...")
        _llm = create_llm()
        logger.info("✅ LLM initialized successfully")
    return _llm


def _handle_llm_error(e: Exception, error_context: str = "LLM") -> str:
    """Maneja errores del LLM y devuelve mensaje amigable para el usuario."""
    error_msg = str(e)
    
    if "API key" in error_msg or "401" in error_msg or "Unauthorized" in error_msg:
        logger.error(f"❌ Invalid API key: {e}")
        return "⚠️ Error de configuración de API key. Por favor verifica tu archivo .env."
    
    if "429" in error_msg or "rate_limit" in error_msg or "quota" in error_msg.lower():
        logger.error(f"⚠️ Rate limit exceeded: {e}")
        return "⚠️ Límite de rate de API excedido. Por favor espera unos minutos e intenta de nuevo."
    
    logger.error(f"❌ {error_context} error: {e}")
    return "❌ Ocurrió un error. Por favor intenta de nuevo."


@log_node_execution
def detect_intent_node(state: ConversationState) -> ConversationState:
    """Detecta la intención del usuario usando LLM."""
    # Mostrar mensaje de bienvenida en la primera interacción
    if len(state["messages"]) == 1:
        return _show_welcome_message(state)
    
    user_message = get_last_user_message(state)
    if not user_message:
        state["current_intent"] = UserIntent.UNKNOWN
        return state
    
    # Mantener intención CHECKOUT si estamos recolectando datos del cliente
    if state.get("stage") == ConversationStage.CHECKOUT:
        if not state.get("customer_name") or not state.get("customer_city"):
            state["current_intent"] = UserIntent.CHECKOUT
            return state
    
    # Usar LLM para detección de intención
    try:
        llm = get_llm()
        logger.debug(f"💬 Detecting intent for: '{user_message[:50]}...'")
        
        context = _build_context(state)
        messages = create_intent_detection_messages(user_message, context)
        
        logger.debug("🤖 Calling LLM for intent detection...")
        response = llm.invoke(messages)
        intent_str = response.content.strip().upper()
        logger.debug(f"🎯 Detected intent: {intent_str}")
        
        try:
            intent = UserIntent(intent_str.lower())
            state["current_intent"] = intent
            logger.info(f"✅ Intent: {intent.value}")
        except ValueError:
            state["current_intent"] = UserIntent.UNKNOWN
            
    except Exception as e:
        logger.error(f"❌ Error detecting intent: {e}")
        state["current_intent"] = UserIntent.UNKNOWN
    
    return state


def _show_welcome_message(state: ConversationState) -> ConversationState:
    """Agrega mensaje de bienvenida al estado."""
    welcome_msg = (
        "👋 **¡Bienvenido a la tienda online!**\n\n"
        "Puedo ayudarte a:\n"
        "📦 Ver productos: 'Muéstrame los productos'\n"
        "➕ Añadir al carrito: 'Añade 2 Camiseta Básica'\n"
        "🛒 Ver carrito: 'Qué llevo en el carrito'\n"
        "💳 Comprar: 'Quiero finalizar la compra'\n"
        "👋 Salir: 'Salir'\n\n"
        "¿Qué te gustaría hacer?"
    )
    state["messages"] = state["messages"] + [AIMessage(content=welcome_msg)]
    state["stage"] = ConversationStage.SHOPPING
    state["current_intent"] = UserIntent.UNKNOWN
    return state


def _build_context(state: ConversationState) -> Dict:
    """Construye diccionario de contexto para el LLM."""
    context = {
        "stage": state.get("stage", "SHOPPING"),
        "cart_item_count": state["cart"].get_item_count(),
        "customer_name": state.get("customer_name"),
        "customer_city": state.get("customer_city"),
        "conversation_history": state.get("messages", []),
    }
    
    last_product_id = state.get("last_product_id")
    if last_product_id:
        catalog = get_catalog_service()
        last_product = catalog.get_by_id(last_product_id)
        if last_product:
            context["last_product_name"] = last_product.name
    
    return context


@log_node_execution
def browse_products_node(state: ConversationState) -> ConversationState:
    """Muestra el catálogo de productos."""
    catalog = get_catalog_service()
    products = catalog.get_all_products()
    
    # Guardar resultados para referencia futura
    state["last_search_results"] = [
        {
            "id": p.id,
            "name": p.name,
            "price": p.price,
            "category": p.category,
            "stock": p.stock
        }
        for p in products
    ]
    
    # Formatear respuesta
    response = "📦 **Productos disponibles:**\n\n"
    for i, p in enumerate(products, 1):
        response += f"{i}. **{p.name}** - ${p.price} ({p.category}) - Stock: {p.stock}\n"
    
    response += "\n💡 Puedes decir: 'Añade 2 Camiseta Básica Azul' o 'Quiero producto 1'"
    
    state["messages"] = state["messages"] + [AIMessage(content=response)]
    state["stage"] = ConversationStage.SHOPPING
    
    return state


@log_node_execution
def manage_cart_node(state: ConversationState) -> ConversationState:
    """Añade o elimina productos del carrito usando LLM para extracción."""
    user_message = get_last_user_message(state)
    
    try:
        # Extraer datos de acción del carrito desde el mensaje del usuario
        action_data = _extract_cart_action(user_message, state)
        if not action_data:
            return _send_cart_error_message(state, "parse_error")
        
        # Encontrar el producto
        product = _find_product(action_data, state)
        if not product:
            return _send_cart_error_message(state, "product_not_found")
        
        # Guardar ID del producto para referencias futuras
        state["last_product_id"] = product.id
        
        # Ejecutar la acción (add/remove)
        response_text = _execute_cart_action(action_data, product, state)
        
    except Exception as e:
        response_text = _handle_llm_error(e, "Cart management")
    
    state["messages"] = state["messages"] + [AIMessage(content=response_text)]
    state["stage"] = ConversationStage.SHOPPING
    return state


def _extract_cart_action(user_message: str, state: ConversationState) -> Optional[Dict]:
    """Extrae detalles de acción del carrito desde mensaje del usuario usando LLM con productos candidatos."""
    llm = get_llm()
    catalog = get_catalog_service()
    
    # Obtener último producto para contexto
    last_product_name = None
    last_product_id = state.get("last_product_id")
    if last_product_id:
        last_product = catalog.get_by_id(last_product_id)
        if last_product:
            last_product_name = last_product.name
    
    # Buscar productos candidatos basados en el mensaje del usuario
    candidate_products = None
    search_results = catalog.search_products(user_message, min_similarity=0.3)
    if search_results:
        candidate_products = [
            {
                "id": p.id,
                "name": p.name,
                "price": p.price,
                "stock": p.stock,
                "category": p.category
            }
            for p in search_results[:10]  # Limitar a 10 candidatos para no saturar el LLM
        ]
        logger.debug(f"🔍 Found {len(candidate_products)} candidate products")
    
    conversation_history = state.get("messages", [])
    messages = create_cart_extraction_messages(
        user_message, 
        last_product_name,
        conversation_history,
        candidate_products
    )
    
    logger.debug("🤖 Calling LLM for cart entity extraction...")
    response = llm.invoke(messages)
    logger.debug(f"📝 Response received: {response.content[:100]}...")
    
    # Parsear JSON de la respuesta del LLM
    try:
        content = _clean_llm_json_response(response.content)
        data = json.loads(content)
        
        return {
            "action": data.get("action", "add"),
            "quantity": data.get("quantity", 1),
            "product_ref": data.get("product_reference", {}),
        }
    except (json.JSONDecodeError, AttributeError) as e:
        logger.warning(f"⚠️ Error parsing LLM response: {e}")
        return None


def _clean_llm_json_response(content: str) -> str:
    """Limpia respuesta del LLM para extraer JSON."""
    content = content.strip()
    
    # Remover bloques de código markdown
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()
    
    # Extraer patrón JSON
    json_match = re.search(r'\{.*\}', content, re.DOTALL)
    if json_match:
        content = json_match.group(0)
    
    return content


def _find_product(action_data: Dict, state: ConversationState):
    """Encuentra producto según tipo de referencia (id, name, index, last)."""
    catalog = get_catalog_service()
    product_ref = action_data["product_ref"]
    ref_type = product_ref.get("type", "name")
    ref_value = product_ref.get("value", "")
    
    if ref_type == "last":
        last_product_id = state.get("last_product_id")
        if last_product_id:
            return catalog.get_by_id(last_product_id)
    
    elif ref_type == "id":
        return catalog.get_by_id(ref_value)
    
    elif ref_type == "index":
        try:
            idx = int(ref_value) - 1
            results = state.get("last_search_results", [])
            if 0 <= idx < len(results):
                product_id = results[idx]["id"]
                return catalog.get_by_id(product_id)
        except ValueError:
            pass
    
    elif ref_type == "name":
        # Primero intentar búsqueda por ID (por si el LLM devolvió un ID)
        product = catalog.get_by_id(ref_value)
        if product:
            return product
        # Búsqueda exacta por nombre (el LLM ya eligió el nombre correcto)
        return catalog.get_by_name(ref_value)
    
    return None


def _execute_cart_action(action_data: Dict, product, state: ConversationState) -> str:
    """Ejecuta acción add/remove/update en el carrito."""
    action = action_data["action"]
    quantity = action_data["quantity"]
    cart = state["cart"]
    
    if action == "remove":
        return _remove_from_cart(cart, product, quantity)
    elif action == "update":
        return _update_cart_quantity(cart, product, quantity)
    else:  # add
        return _add_to_cart(cart, product, quantity)


def _add_to_cart(cart, product, quantity: int) -> str:
    """Añade producto al carrito con validación de stock."""
    if product.stock >= quantity:
        cart.add_item(product, quantity)
        return f"✅ {quantity}x {product.name} añadido al carrito."
    else:
        return f"⚠️ Solo hay {product.stock} unidades de {product.name} disponibles."


def _update_cart_quantity(cart, product, quantity: int) -> str:
    """Actualiza cantidad de item del carrito a cantidad específica."""
    if not cart.has_product(product.id):
        # Si no está en el carrito, añadirlo
        if product.stock >= quantity:
            cart.add_item(product, quantity)
            return f"✅ {quantity}x {product.name} añadido al carrito."
        else:
            return f"⚠️ Solo hay {product.stock} unidades de {product.name} disponibles."
    
    current_item = cart.get_item(product.id)
    current_quantity = current_item.quantity
    
    if quantity == 0:
        cart.remove_item(product.id)
        return f"✅ {product.name} eliminado del carrito."
    elif product.stock >= quantity:
        cart.update_quantity(product.id, quantity)
        return f"✅ Cantidad de {product.name} actualizada: {current_quantity} → {quantity}"
    else:
        return f"⚠️ Solo hay {product.stock} unidades de {product.name} disponibles."


def _remove_from_cart(cart, product, quantity: int) -> str:
    """Elimina producto del carrito."""
    if not cart.has_product(product.id):
        return f"⚠️ {product.name} no está en tu carrito."
    
    current_item = cart.get_item(product.id)
    current_quantity = current_item.quantity
    
    if quantity >= current_quantity:
        cart.remove_item(product.id)
        return f"✅ {product.name} eliminado del carrito."
    else:
        new_quantity = current_quantity - quantity
        cart.update_quantity(product.id, new_quantity)
        return f"✅ Reducida cantidad de {product.name}: {current_quantity} → {new_quantity}"


def _send_cart_error_message(state: ConversationState, error_type: str) -> ConversationState:
    """Envía mensaje de error para operaciones del carrito."""
    if error_type == "parse_error":
        message = "❌ No entendí eso. Intenta con: 'Añade 2 Camiseta Básica' o 'Quiero producto 1'"
    else:  # product_not_found
        message = "❌ No encontré ese producto. Intenta con: 'Añade 2 Camiseta Básica Azul' o 'Quiero producto 1'"
    
    state["messages"] = state["messages"] + [AIMessage(content=message)]
    state["stage"] = ConversationStage.SHOPPING
    return state


@log_node_execution
def view_cart_node(state: ConversationState) -> ConversationState:
    """Muestra contenido del carrito."""
    cart = state["cart"]
    
    if cart.is_empty():
        response = "🛒 Tu carrito está vacío.\n\n💡 Puedes ver productos con: 'Muéstrame los productos'"
    else:
        response = "🛒 **Tu carrito:**\n\n"
        for item in cart.items.values():
            response += f"- {item.quantity}x {item.product.name} - ${item.subtotal:.2f}\n"
        response += f"\n**Total: ${cart.get_total():.2f}**"
        response += "\n\n💡 ¿Quieres finalizar la compra?"
    
    state["messages"] = state["messages"] + [AIMessage(content=response)]
    return state


@log_node_execution
def checkout_node(state: ConversationState) -> ConversationState:
    """Maneja proceso de checkout (recolectar datos del cliente y confirmar orden)."""
    user_message = get_last_user_message(state)
    
    # Verificar si el carrito está vacío
    if state["cart"].is_empty():
        response = "⚠️ Tu carrito está vacío. Añade productos antes de comprar."
        state["messages"] = state["messages"] + [AIMessage(content=response)]
        state["stage"] = ConversationStage.SHOPPING
        return state
    
    # Recolectar nombre del cliente
    if not state.get("customer_name"):
        return _collect_customer_name(state, user_message)
    
    # Recolectar ciudad del cliente y completar orden
    if not state.get("customer_city"):
        return _complete_order(state, user_message)
    
    return state


def _collect_customer_name(state: ConversationState, user_message: str) -> ConversationState:
    """Recolecta nombre del cliente."""
    # Si el usuario solo dijo palabras clave de "checkout", pedir nombre
    if any(word in user_message.lower() for word in ["comprar", "finalizar", "checkout", "pagar"]):
        response = "📝 Para completar la compra necesito tus datos.\n¿Cuál es tu nombre?"
        state["messages"] = state["messages"] + [AIMessage(content=response)]
    else:
        # Parsear nombre del mensaje
        name = _extract_name_from_message(user_message)
        if name:
            state["customer_name"] = name
            response = "✅ Perfecto. ¿En qué ciudad?"
        else:
            response = "⚠️ No entendí tu nombre. ¿Cuál es tu nombre?"
        state["messages"] = state["messages"] + [AIMessage(content=response)]
    
    state["stage"] = ConversationStage.CHECKOUT
    return state


def _extract_name_from_message(message: str) -> Optional[str]:
    """Extrae nombre del mensaje del usuario, removiendo prefijos comunes."""
    name = message.strip()
    for prefix in ["mi nombre es", "me llamo", "soy", "mi nombre:"]:
        if name.lower().startswith(prefix):
            name = name[len(prefix):].strip()
            break
    return name if name else None


def _complete_order(state: ConversationState, city: str) -> ConversationState:
    """Completa la orden con información de ciudad."""
    state["customer_city"] = city.strip()
    
    # Crear orden
    order = Order.create_from_cart(
        cart=state["cart"],
        customer_name=state["customer_name"],
        customer_city=state["customer_city"]
    )
    state["order"] = order
    
    # Generar mensaje de confirmación
    response = _format_order_confirmation(order)
    
    # Limpiar carrito después de compra exitosa
    state["cart"].clear()
    
    state["messages"] = state["messages"] + [AIMessage(content=response)]
    state["stage"] = ConversationStage.COMPLETED
    
    return state


def _format_order_confirmation(order: Order) -> str:
    """Formatea mensaje de confirmación de orden."""
    response = f"✅ **¡Pedido confirmado!**\n\n"
    response += f"📦 **Orden #{order.order_id}**\n"
    response += f"👤 Cliente: {order.customer_name}\n"
    response += f"📍 Ciudad: {order.customer_city}\n\n"
    response += "**Productos:**\n"
    for item in order.cart.items.values():
        response += f"- {item.quantity}x {item.product.name} - ${item.subtotal:.2f}\n"
    response += f"\n💰 **Total: ${order.total:.2f}**\n\n"
    response += "¡Gracias por tu compra! 🎉"
    return response


@log_node_execution
def out_of_context_node(state: ConversationState) -> ConversationState:
    """Maneja preguntas fuera de contexto usando LLM."""
    user_message = get_last_user_message(state)
    
    try:
        llm = get_llm()
        logger.debug("🤖 Calling LLM for out-of-context question...")
        messages = create_out_of_context_messages(user_message)
        response = llm.invoke(messages)
        logger.debug(f"📝 Out-of-context response: {response.content[:100]}...")
        response_text = response.content.strip()
    except Exception as e:
        logger.error(f"Error in out_of_context_node: {e}")
        response_text = (
            "Soy un asistente de compras y solo puedo ayudarte con productos. "
            "¿Quieres ver nuestro catálogo?"
        )
    
    state["messages"] = state["messages"] + [AIMessage(content=response_text)]
    state["stage"] = ConversationStage.SHOPPING
    return state
