"""
Punto de entrada principal del chatbot de e-commerce.

Este módulo proporciona una interfaz simple para interactuar con el chatbot.
"""

import sys
from pathlib import Path

# Agregar directorio raíz al PYTHONPATH para que funcionen los imports
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

import uuid
from typing import Optional
from langchain_core.messages import HumanMessage, AIMessage

from graph.state import create_initial_state, ConversationState
from graph.builder import run_conversation_turn


class ShoppingChatBot:
    """
    Chatbot conversacional para e-commerce con LangGraph.
    
    Esta clase proporciona una interfaz simple para:
    - Iniciar conversaciones
    - Enviar mensajes del usuario
    - Obtener respuestas del bot
    - Mantener el contexto de la conversación
    """
    
    def __init__(self, session_id: Optional[str] = None):
        """
        Inicializa una nueva instancia del chatbot.
        
        Args:
            session_id: ID opcional de la sesión. Si no se proporciona, se genera uno nuevo.
        """
        self.session_id = session_id or str(uuid.uuid4())
        self.state: ConversationState = create_initial_state(session_id=self.session_id)
        
    def send_message(self, user_message: str) -> str:
        """
        Envía un mensaje del usuario y obtiene la respuesta del bot.
        
        Args:
            user_message: Mensaje del usuario
            
        Returns:
            Respuesta del bot
        """
        # Agregar mensaje del usuario al estado
        human_msg = HumanMessage(content=user_message)
        self.state["messages"].append(human_msg)
        
        # Ejecutar turno de conversación
        self.state = run_conversation_turn(self.state)
        
        # Extraer última respuesta del bot
        if self.state["messages"]:
            last_message = self.state["messages"][-1]
            if isinstance(last_message, AIMessage):
                return last_message.content
        
        return "Lo siento, no pude procesar tu mensaje. ¿Podrías intentar de nuevo?"
    
    def get_state(self) -> ConversationState:
        """
        Obtiene el estado actual de la conversación.
        
        Returns:
            Estado actual
        """
        return self.state
    
    def reset(self):
        """
        Reinicia la conversación manteniendo el mismo session_id.
        """
        self.state = create_initial_state(session_id=self.session_id)
    
    def get_cart_summary(self) -> dict:
        """
        Obtiene un resumen del carrito actual.
        
        Returns:
            Diccionario con información del carrito
        """
        cart = self.state.get("cart")
        if not cart:
            return {"items": [], "total": 0.0, "item_count": 0}
        
        return {
            "items": [
                {
                    "product_id": item.product_id,
                    "name": item.name,
                    "quantity": item.quantity,
                    "price": item.price,
                    "subtotal": item.get_subtotal(),
                }
                for item in cart.items
            ],
            "total": cart.get_total(),
            "item_count": cart.get_item_count(),
        }


# ============================================================================
# INTERFAZ CLI SIMPLE
# ============================================================================

def run_cli():
    """
    Ejecuta el chatbot en modo CLI con opción de debug.
    """
    import os
    import argparse
    from dotenv import load_dotenv
    
    # Parsear argumentos de línea de comandos
    parser = argparse.ArgumentParser(description="E-commerce Shopping Chatbot")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Habilitar modo debug con logging detallado"
    )
    args = parser.parse_args()
    
    # Cargar variables de entorno
    load_dotenv()
    
    # Establecer variable de entorno DEBUG si el flag está presente
    if args.debug or os.getenv("DEBUG", "False").lower() == "true":
        os.environ["DEBUG"] = "True"
        # Reconfigurar logging después de establecer la variable DEBUG
        import logging
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            force=True  # Forzar reconfiguración
        )
        print("🐛 Debug mode enabled\n")
    
    print("=" * 70)
    print("🛒 CHATBOT DE E-COMMERCE")
    print("=" * 70)
    
    # Verificar configuración de API key
    google_key = os.getenv("GOOGLE_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    
    if not google_key and not openai_key and not anthropic_key:
        print("❌ ERROR: No se encontró ninguna API key configurada.\n")
        return
    
    print("Escribe 'salir' o 'exit' para terminar\n")
    
    bot = ShoppingChatBot()
    
    # Mensaje de bienvenida (enviar primer mensaje)
    welcome = bot.send_message("hola")
    print(f"🤖 Bot: {welcome}\n")
    
    while True:
        try:
            # Leer input del usuario
            user_input = input("👤 Tú: ").strip()
            
            if not user_input:
                continue
            
            # Verificar si quiere salir
            if user_input.lower() in ["salir", "exit", "quit", "adiós", "adios"]:
                print("\n¡Hasta luego! 👋\n")
                break
            
            # Enviar mensaje y obtener respuesta
            response = bot.send_message(user_input)
            print(f"\n🤖 Bot: {response}\n")
            
        except KeyboardInterrupt:
            print("\n\n¡Hasta luego! 👋\n")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}\n")


if __name__ == "__main__":
    run_cli()
