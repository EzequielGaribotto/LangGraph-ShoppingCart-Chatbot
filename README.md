# Shopping Cart Chatbot con LangGraph

Chatbot conversacional que simula un carrito de compra online usando LangGraph en Python.

## 📋 Características

✅ Catálogo de 12 productos (JSON)  
✅ Flujo completo: ver productos, añadir/quitar actualizar en el carrito, consultar carrito, checkout  
✅ Gestión de estados con LangGraph (5 etapas + 6 nodos)  
✅ Detección inteligente de intenciones mediante LLM  
✅ Extracción contextual de entidades (productos, cantidades) y intenciones  
✅ Manejo de errores y validaciones  
✅ CLI funcional con modo debug  
✅ Tests automatizados con pytest  
✅ Estructura de proyecto clara

## 🚀 Instalación Rápida

```bash
# Clonar repositorio
git clone https://github.com/tu-usuario/shopping_cart_chatbot_LangGraph
cd shopping_cart_chatbot_LangGraph

# Crear entorno virtual
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Instalar dependencias
pip install -r requirements.txt

# Configurar API key
# Crea un archivo .env en la raíz del proyecto:
cp .env.example .env

# Edita .env y añade tu API key:
# Para Google Gemini (GRATIS - Recomendado):
GOOGLE_API_KEY=tu-api-key-aqui
LLM_PROVIDER=google

# O para OpenAI:
# OPENAI_API_KEY=tu-api-key-aqui
# LLM_PROVIDER=openai

# O para Anthropic:
# ANTHROPIC_API_KEY=tu-api-key-aqui
# LLM_PROVIDER=anthropic
```

**IMPORTANTE:** Este chatbot usa un LLM (Large Language Model) para entender lenguaje natural. Necesitas una API key de:
- **Google Gemini** (GRATIS ✅ - Recomendado) - [Obtener API key](https://ai.google.dev/gemini-api/docs/api-key)
- **OpenAI** (de pago: gpt-4o-mini) - [Obtener API key](https://platform.openai.com/api-keys)
- **Anthropic** (de pago: claude-3-5-sonnet) - [Obtener API key](https://console.anthropic.com/)

## 💻 Uso

### CLI (Línea de Comandos)

**Modo normal (recomendado):**
```bash
python app/main.py
```

**Modo debug (con logs detallados):**
```bash
python app/main.py --debug
```

El modo debug muestra información técnica útil para desarrollo:
- Tiempos de ejecución de cada nodo
- Llamadas al LLM con prompts y respuestas
- Cambios de estado del grafo
- Detección de intenciones y procesamiento

Ejemplos de conversación: 
- [conversation debug.txt](conversation%20debug.txt) (modo debug)
- [conversation.txt](conversation.txt) (modo normal)


## 🧪 Tests

El proyecto incluye **10 tests automatizados** divididos en dos archivos:

### Tests Básicos (test_basic.py)
5 tests unitarios que prueban operaciones esenciales

### Tests con Mocks (test_nodes_mocked.py)
5 tests de integración con LLM mockeado

```bash
# Ejecutar todos los tests
pytest tests/ -v

# Ejecutar solo tests básicos
pytest tests/test_basic.py -v

# Ejecutar solo tests con mocks
pytest tests/test_nodes_mocked.py -v

# Con coverage
pytest tests/ --cov=. --cov-report=html
```

Más informacion en [**docs/ARCHITECTURE.md**](docs/ARCHITECTURE.md) -> Sección Tests

## 🏗️ Arquitectura

Para entender cómo funciona el sistema internamente (nodos, flujo del grafo, decisiones de diseño), consulta:

📚 [**docs/ARCHITECTURE.md**](docs/ARCHITECTURE.md) - Documentación completa de arquitectura

## 🔧 Tecnologías

- **Python 3.10+**
- **LangGraph** - Orquestación del flujo conversacional mediante grafos de estados
- **LangChain** - Integración con múltiples proveedores LLM
- **LLMs** - Google Gemini / OpenAI GPT / Anthropic Claude para procesamiento de lenguaje natural
- **Pydantic** - Validación de modelos de dominio
- **Pytest** - Testing automatizado
