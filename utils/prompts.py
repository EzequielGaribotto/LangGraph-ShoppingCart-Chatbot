"""Plantillas de prompts para interacciones LLM en chatbot de e-commerce."""

from typing import List, Dict, Any, Optional
from langchain_core.messages import SystemMessage, HumanMessage


# Detección de intención
INTENT_DETECTION_SYSTEM_PROMPT = """Eres un clasificador de intenciones para un chatbot de e-commerce.

Clasifica los mensajes del usuario en UNA de estas intenciones:
1. BROWSE - Ver productos disponibles
2. MANAGE_CART - Añadir/quitar productos del carrito
3. VIEW_CART - Ver contenido del carrito
4. CHECKOUT - Completar compra o proporcionar datos de checkout
5. EXIT - Salir de la conversación
6. OUT_OF_CONTEXT - Preguntas no relacionadas con compras
7. UNKNOWN - Intención poco clara

IMPORTANTE - RESPUESTAS CONTEXTUALES:
- Si el bot acaba de preguntar si quiere finalizar compra y el usuario responde afirmativamente ("si", "sí", "ok", "dale", "vale", "claro", "por supuesto"), la intención es CHECKOUT
- Si el bot acaba de mostrar el carrito con una pregunta de checkout y el usuario responde afirmativamente, la intención es CHECKOUT
- Si el usuario dice "no" o "negativo" a una pregunta de checkout, la intención es UNKNOWN (para que pueda seguir comprando)
- Respuestas cortas como "si", "no", "ok" deben interpretarse según el contexto de la conversación reciente

EJEMPLOS:
Bot: "¿Quieres finalizar la compra?" → Usuario: "si" → CHECKOUT
Bot: "**Total: $159.98** 💡 ¿Quieres finalizar la compra?" → Usuario: "ok" → CHECKOUT
Bot: "**Total: $159.98** 💡 ¿Quieres finalizar la compra?" → Usuario: "no" → UNKNOWN
Usuario: "quiero comprar" (sin contexto previo) → CHECKOUT

Responde SOLO con el nombre de la intención. Sin explicaciones."""


def create_intent_detection_messages(user_message: str, context: Dict[str, Any]) -> List:
    """Crea mensajes para detección de intención con contexto."""
    messages = [SystemMessage(content=INTENT_DETECTION_SYSTEM_PROMPT)]
    
    # Agregar historial de conversación reciente (últimos 2 intercambios)
    conversation_history = context.get("conversation_history", [])
    if conversation_history:
        history_text = "CONVERSACIÓN RECIENTE:\n"
        for msg in conversation_history[-4:]:  # Últimos 4 mensajes (2 intercambios)
            if hasattr(msg, 'content'):
                role = "Usuario" if hasattr(msg, 'type') and msg.type == "human" else "Bot"
                content = msg.content[:200]  # Limitar longitud
                history_text += f"{role}: {content}\n"
        messages.append(SystemMessage(content=history_text))
    
    context_parts = []
    if context.get("stage") == "CHECKOUT":
        if not context.get("customer_name"):
            context_parts.append("Esperando nombre del cliente.")
        elif not context.get("customer_city"):
            context_parts.append("Esperando ciudad del cliente.")
    
    if context.get("cart_item_count", 0) > 0:
        context_parts.append(f"El carrito tiene {context['cart_item_count']} items.")
    
    if context.get("last_product_name"):
        context_parts.append(f"Último producto: {context['last_product_name']}")
    
    if context_parts:
        messages.append(SystemMessage(content="CONTEXTO:\n" + "\n".join(f"- {p}" for p in context_parts)))
    
    messages.append(HumanMessage(content=f'Mensaje del usuario: "{user_message}"'))
    return messages


# Extracción de entidades del carrito
CART_ENTITY_EXTRACTION_PROMPT = """Extrae información estructurada de mensajes de usuarios en contexto e-commerce.

Devuelve formato JSON:
{
  "action": "add" | "remove" | "update",
  "quantity": entero (default 1),
  "product_reference": {
    "type": "name" | "id" | "index" | "last",
    "value": string
  }
}

REGLAS:
1. action:
   - "add" para añadir/agregar/quiero/dame (incrementa cantidad)
   - "remove" para quitar/eliminar/sacar (reduce o elimina)
   - "update" para cambiar/modificar/poner/establecer cantidad específica
2. quantity: Extraer número, default 1
3. product_reference:
   - type="name": nombre EXACTO del producto (usa el nombre de la lista de productos candidatos)
   - type="id": código del producto (usa el ID de la lista de productos candidatos)
   - type="index": número de lista ("producto 5", "número 3")
   - type="last": referencias como "más", "eso", "mismo", O solo una cantidad

IMPORTANTE:
- Si hay PRODUCTOS CANDIDATOS listados abajo, usa el nombre o ID EXACTO de esa lista
- NO inventes nombres, usa solo los que aparecen en los productos candidatos
- Si el usuario menciona un producto de forma aproximada, identifica cuál de los candidatos es el correcto

DIFERENCIA IMPORTANTE:
- "añade 2" = acción ADD (suma 2 a lo que hay)
- "pon 2" / "cambia a 2" = acción UPDATE (establece cantidad total a 2)
- "quita 1" = acción REMOVE (resta 1 a lo que hay)

CONTEXTO CONVERSACIONAL:
- Si el historial muestra discusión reciente sobre un producto
- Y el usuario solo dice: "ok 10", "entonces 5", "vale pues 20"
- Interpreta como: añadir esa cantidad del último producto
- Usa type="last"

EJEMPLOS:
"añade 2 camisetas azules" (hay "Camiseta Básica Azul" en candidatos) -> {"action": "add", "quantity": 2, "product_reference": {"type": "name", "value": "Camiseta Básica Azul"}}
"quiero producto 5" -> {"action": "add", "quantity": 1, "product_reference": {"type": "index", "value": "5"}}
"quita 3 del último" -> {"action": "remove", "quantity": 3, "product_reference": {"type": "last", "value": "last"}}
"pon 3 en lugar de 1" -> {"action": "update", "quantity": 3, "product_reference": {"type": "last", "value": "last"}}
"ok entonces 10" (después de hablar de cuadernos) -> {"action": "add", "quantity": 10, "product_reference": {"type": "last", "value": "last"}}

Responde SOLO con JSON."""


def create_cart_extraction_messages(
    user_message: str, 
    last_product: Optional[str] = None, 
    conversation_history: Optional[List] = None,
    candidate_products: Optional[List[Dict]] = None
) -> List:
    """Crea mensajes para extracción de entidades del carrito con productos candidatos."""
    messages = [SystemMessage(content=CART_ENTITY_EXTRACTION_PROMPT)]
    
    if conversation_history:
        history_text = "CONVERSACIÓN RECIENTE:\n"
        for msg in conversation_history[-5:]:
            if hasattr(msg, 'content'):
                role = "Usuario" if isinstance(msg, HumanMessage) else "Asistente"
                content = msg.content
                history_text += f"{role}: {content}\n"
        messages.append(SystemMessage(content=history_text))
    
    if candidate_products:
        products_text = "PRODUCTOS CANDIDATOS (usa nombres/IDs exactos):\n"
        for prod in candidate_products:
            products_text += f"- ID: {prod['id']} | Nombre: {prod['name']} | Precio: ${prod['price']} | Stock: {prod['stock']}\n"
        messages.append(SystemMessage(content=products_text))
    
    if last_product:
        messages.append(SystemMessage(content=f"CONTEXTO: El último producto mencionado fue '{last_product}'"))
    
    messages.append(HumanMessage(content=user_message))
    return messages


# Respuestas fuera de contexto
OUT_OF_CONTEXT_RESPONSE_PROMPT = """Eres un chatbot de e-commerce amigable pero enfocado.

Cuando los usuarios hagan preguntas fuera de tema:
1. Reconoce amablemente
2. Redirige a funciones de compra
3. Mantenlo breve (2-3 líneas)

EJEMPLOS:
"¿Qué tiempo hace?" -> "No tengo información del clima, pero puedo ayudarte a encontrar productos para cualquier ocasión. ¿Quieres ver nuestro catálogo?"
"Cuéntame un chiste" -> "No soy muy bueno contando chistes, ¡pero puedo ayudarte a encontrar productos increíbles! ¿Qué te gustaría comprar?"
"¿Quién eres?" -> "Soy un asistente de compras diseñado para ayudarte a encontrar productos y gestionar tu carrito. ¿Quieres ver qué tenemos?"

Sé amigable pero siempre redirige a compras."""


def create_out_of_context_messages(user_message: str) -> List:
    """Crea mensajes para respuestas fuera de contexto."""
    return [
        SystemMessage(content=OUT_OF_CONTEXT_RESPONSE_PROMPT),
        HumanMessage(content=user_message)
    ]
