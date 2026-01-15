# Arquitectura del Shopping Cart Chatbot

## 📋 Índice

1. [Estructura General](#estructura-general)
2. [Flujo del Grafo de Estados](#flujo-del-grafo-de-estados)
3. [Nodos y Estados del Grafo LangGraph](#nodos-y-estados-del-grafo-langgraph)
4. [Sistema de Estados](#sistema-de-estados)
5. [Transiciones y Routing](#transiciones-y-routing)
6. [Modelos de Dominio](#modelos-de-dominio)
7. [Decisiones de Diseño](#decisiones-de-diseño)
8. [Tests Automatizados](#tests-automatizados)

---

## 📐 Estructura General

El proyecto está organizado en capas separando responsabilidades:

```
┌─────────────────────────────────┐
│     CLI (app/main.py)           │  ← Interfaz de usuario
├─────────────────────────────────┤
│  Grafo LangGraph (builder.py)  │  ← Orquestación del flujo
├─────────────────────────────────┤
│  Nodos (graph/nodes.py)         │  ← Lógica conversacional
├─────────────────────────────────┤
│  Modelos (models/)              │  ← Lógica de negocio
└─────────────────────────────────┘
```

### Organización de Archivos

```
app/
  ├── main.py              # CLI interactivo
  ├── config/
  │   └── llm_config.py    # Configuración multi-proveedor LLM
  └── services/
      └── catalog_service.py  # Gestión de catálogo
graph/
  ├── builder.py           # Construcción del grafo
  ├── nodes.py             # Implementación de nodos
  ├── edges.py             # Lógica de transiciones
  └── state.py             # Definición de estados
models/
  ├── product.py           # Modelo de producto
  ├── cart.py              # Modelo de carrito
  └── order.py             # Modelo de orden
data/
  └── catalog.json         # Catálogo de 12 productos
tests/
  ├── test_basic.py        # Tests unitarios
  └── test_nodes_mocked.py # Tests con mocks
```


## 🔄 Flujo del Grafo de Estados
![alt text](<Flujo del grafo de estados.png>)
---

## 🔄 Nodos y Estados del Grafo LangGraph

### Punto de Entrada

El grafo comienza en el nodo **`detect_intent`** que actúa como router central del sistema.

### Los 6 Nodos del Grafo

#### 1. **detect_intent_node** (Nodo Central)

**Responsabilidad**: Router central que analiza el mensaje del usuario y clasifica su intención.

**Funcionamiento**:
1. En la primera interacción, muestra mensaje de bienvenida
2. Envía el mensaje del usuario al LLM con contexto (carrito, historial, último producto)
3. El LLM responde con una de las 7 intenciones posibles
4. Actualiza `state["current_intent"]`
5. El edge `route_by_intent` redirige al nodo correspondiente

**Transición**: Se ejecuta `route_by_intent` que decide el siguiente nodo según la intención detectada.

---

#### 2. **browse_products_node**

**Responsabilidad**: Muestra el catálogo completo de productos disponibles.

**Funcionamiento**:
1. Obtiene todos los productos del `CatalogService` (12 productos)
2. Genera un mensaje formateado con ID, nombre, precio y categoría de cada producto
3. Añade el mensaje al historial

**Transición**: Termina y espera el siguiente mensaje del usuario (vuelve a `detect_intent` en el próximo ciclo).

---

#### 3. **manage_cart_node**

**Responsabilidad**: Añade o quita productos del carrito usando procesamiento LLM.

**Funcionamiento**:
1. **Extracción estructurada**: El LLM analiza el mensaje y devuelve JSON con:
   ```json
   {
     "action": "add" | "remove",
     "quantity": número,
     "product_reference": {
       "type": "name" | "id" | "index" | "last",
       "value": string
     }
   }
   ```
2. **Búsqueda de producto**: Localiza el producto en el catálogo según el tipo de referencia
3. **Validación de stock**: Verifica disponibilidad antes de añadir
4. **Actualización**: Modifica el carrito y guarda `last_product_id` para contexto

**Manejo contextual**: Entiende referencias como:
- "añade 5 más" (usa `last_product_id`)
- "quiero el producto 3" (índice de lista)
- "Camiseta azul" (búsqueda por nombre)
- "prod_001" (búsqueda por ID)

**Transición**: Termina y espera el siguiente mensaje del usuario.

---

#### 4. **view_cart_node**

**Responsabilidad**: Muestra el contenido actual del carrito de compras.

**Funcionamiento**:
1. Verifica si el carrito está vacío
2. Si está vacío: mensaje informativo
3. Si tiene items: lista cada producto con cantidad, precio unitario y subtotal
4. Muestra el total general al final

**Ejemplo de salida**:
```
🛒 Tu carrito:
1. Camiseta Básica Azul x2 = $39.98
2. Pantalón Jeans x1 = $49.99
💰 Total: $89.97
```

**Transición**: Termina y espera el siguiente mensaje del usuario.

---

#### 5. **checkout_node**

**Responsabilidad**: Gestiona el proceso completo de compra y recolección de datos.

**Funcionamiento** (estado interno):
1. **Validación inicial**: Verifica que el carrito no esté vacío
2. **Recolección de nombre**: Si falta, solicita el nombre del cliente
3. **Recolección de ciudad**: Si falta, solicita la ciudad de envío
4. **Confirmación final**: 
   - Crea la orden usando `Order.create_from_cart()`
   - Genera número de pedido único
   - Muestra resumen completo con items, total, datos de envío
   - Limpia el carrito
   - Actualiza stage a `COMPLETED`

**Estados internos del checkout**:
- Sin datos → pide nombre
- Con nombre → pide ciudad
- Con ambos → confirma y finaliza

**Transición**: Termina cuando completa el pedido o si necesita más datos del usuario.

---

#### 6. **out_of_context_node**

**Responsabilidad**: Maneja preguntas no relacionadas con el proceso de compra.

**Ejemplos de preguntas**: 
- "¿Qué hora es?"
- "¿Quién ganó el mundial?"
- "Cuéntame un chiste"

**Funcionamiento**:
1. Usa el LLM para generar una respuesta contextual y educada
2. Redirige amablemente al usuario hacia las funcionalidades del chatbot
3. Mantiene el flujo de compra activo

**Transición**: Vuelve al flujo normal esperando el siguiente mensaje del usuario.

---

## 🗂️ Sistema de Estados

### ConversationState (TypedDict)

El estado completo de la conversación se define en [graph/state.py](graph/state.py):

```python
{
    "messages": List[BaseMessage],    # Historial completo de mensajes
    "cart": ShoppingCart,             # Instancia del carrito de compras
    "current_intent": UserIntent,     # Última intención detectada
    "stage": ConversationStage,       # Etapa actual del flujo
    "last_search_results": List[dict], # Productos buscados recientemente
    "last_product_id": str,           # ID del último producto mencionado
    "customer_name": str,             # Nombre del cliente
    "customer_city": str,             # Ciudad de envío
    "order": Order,                   # Orden creada (si existe)
    "session_id": str                 # Identificador único de sesión
}
```

### UserIntent (7 Intenciones)

Enum definido en [graph/state.py](graph/state.py):

| Intención | Descripción | Ejemplos de frases |
|-----------|-------------|-------------------|
| `BROWSE` | Ver catálogo de productos | "muéstrame productos", "qué vendes", "ver todo" |
| `MANAGE_CART` | Añadir, quitar productos o cambiar cantidad de productos | "añade 2 camisetas", "quita el pantalón", "quiero 3", "pon 3 en vez de 1" |
| `VIEW_CART` | Consultar carrito | "qué llevo", "ver carrito", "mi pedido actual" |
| `CHECKOUT` | Finalizar compra | "quiero comprar", "finalizar", "pagar" |
| `OUT_OF_CONTEXT` | Preguntas no relacionadas | "qué hora es", "cuéntame un chiste" |
| `UNKNOWN` | No entendido | Mensajes ambiguos |
| `EXIT` | Salir del chat | "salir", "adiós", "terminar" |

### ConversationStage (5 Etapas)

Enum definido en [graph/state.py](graph/state.py):

| Etapa | Descripción | Cuándo se usa |
|-------|-------------|---------------|
| `WELCOME` | Inicio | Primera interacción |
| `SHOPPING` | Navegando/comprando | Durante el proceso de compra |
| `CHECKOUT` | Recogiendo datos | Pidiendo nombre y ciudad |
| `COMPLETED` | Compra finalizada | Después de confirmar pedido |
| `ERROR` | Error | Cuando ocurre un error |


---

## 📦 Modelos de Dominio

Los modelos de negocio están separados de la lógica conversacional para mantener la separación de responsabilidades.

### Product ([models/product.py](models/product.py))

Modelo Pydantic que representa un producto del catálogo.

```python
class Product(BaseModel):
    id: str                    # Identificador único (ej: "prod_001")
    name: str                  # Nombre del producto
    price: float               # Precio unitario
    category: str              # Categoría (ropa, electrónica, hogar)
    description: Optional[str] # Descripción detallada
    stock: int                 # Stock disponible
```

**Validaciones**:
- Precio debe ser positivo
- Stock debe ser no negativo

---

### ShoppingCart ([models/cart.py](models/cart.py))

Modelo Pydantic que gestiona el carrito de compras.

**Atributos**:
```python
class ShoppingCart(BaseModel):
    items: List[CartItem] = []  # Lista de items en el carrito
```

**Métodos principales**:
- `add_item(product: Product, quantity: int)` - Añade producto o incrementa cantidad
- `remove_item(product_id: str)` - Elimina producto del carrito
- `update_quantity(product_id: str, quantity: int)` - Actualiza cantidad
- `get_total() -> float` - Calcula el total del carrito
- `is_empty() -> bool` - Verifica si está vacío
- `get_item_count() -> int` - Cuenta total de items
- `has_stock(product: Product, quantity: int) -> bool` - Verifica disponibilidad

**CartItem**:
```python
class CartItem(BaseModel):
    product: Product
    quantity: int
    
    @property
    def subtotal(self) -> float:
        return self.product.price * self.quantity
```

---

### Order ([models/order.py](models/order.py))

Modelo Pydantic que representa un pedido confirmado.

```python
class Order(BaseModel):
    order_number: str          # Número único (ej: "ORD-20250115-1234")
    items: List[CartItem]      # Items del pedido
    total: float               # Total a pagar
    customer_name: str         # Nombre del cliente
    customer_city: str         # Ciudad de envío
    created_at: datetime       # Fecha y hora de creación
```

**Método de creación**:
```python
@staticmethod
def create_from_cart(
    cart: ShoppingCart, 
    customer_name: str, 
    customer_city: str
) -> Order:
    """Crea una orden desde un carrito."""
```

Genera automáticamente:
- Número de pedido único con timestamp
- Copia de items del carrito
- Total calculado
- Fecha de creación

---

## 🔀 Transiciones y Routing

### Estructura del Grafo

Implementado en [graph/builder.py](graph/builder.py):

```
                    ┌──────────────┐
              ┌────▶│detect_intent │◀────┐
              │     └──────┬───────┘      │
              │            │              │
              │     [route_by_intent]     │
              │            │              │
              │   ┌────────┴─────────┐    │
              │   │                  │    │
          ┌───┴───▼──┐        ┌──────▼────┴──┐
          │  browse  │        │ manage_cart  │
          └──────────┘        └──────────────┘
              │                     │
              └──────────┬──────────┘
                         │
              ┌──────────▼──────────┐
              │    view_cart        │
              │    checkout         │
              │    out_of_context   │
              └──────────┬──────────┘
                         │
                  [should_continue]
                         │
                    ┌────▼────┐
                    │   END   │
                    └─────────┘
```

### Edges (Lógica de Transición)

Implementado en [graph/edges.py](graph/edges.py):

#### 1. **route_by_intent**

**Función**: Routing condicional desde `detect_intent` hacia el nodo apropiado.

**Lógica**:
```python
def route_by_intent(state: ConversationState) -> str:
    intent = state.get("current_intent")
    
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
    else:  # UNKNOWN
        return "END"
```

**Posibles destinos**: `browse`, `manage_cart`, `view_cart`, `checkout`, `out_of_context`, `END`

---

#### 2. **should_continue**

**Función**: Decide si el flujo termina o continúa.

**Lógica**:
```python
def should_continue(state: ConversationState) -> str:
    # Después de procesar cada mensaje, terminamos
    # El siguiente invoke() procesará el siguiente mensaje
    return "END"
```

**Diseño**: El sistema procesa un mensaje por invocación. Cada ciclo termina después de procesar la respuesta, y el siguiente mensaje del usuario inicia un nuevo ciclo desde `detect_intent`.

**Posibles destinos**: `detect_intent`, `END`

---

### Flujo de Ejecución Completo

Puedes ver un ejemplo completo de flujo aquí [conversation debug](/conversation%20debug.txt) o [conversation](/conversation.txt).

---

## 🎨 Decisiones de Diseño

### 1. Uso de LLM para Procesamiento de Lenguaje Natural

**Decisión**: Utilizar un Large Language Model para detección de intenciones y extracción de entidades.

**Justificación**:
- ✅ **Flexibilidad**: Comprende múltiples formas de expresar la misma intención
  - "quiero comprar" = "finalizar compra" = "checkout" = "pagar" = "ya está"
- ✅ **Robustez**: No depende de palabras clave exactas o patrones rígidos
- ✅ **Contexto**: Utiliza información del historial conversacional
- ✅ **Mantenibilidad**: Añadir nuevas variantes no requiere modificar código  

**Alternativa descartada**: Reglas basadas en palabras clave (demasiado rígidas y difíciles de mantener).  

---

### 2. Extracción Estructurada con JSON

**Decisión**: El LLM devuelve JSON estructurado para operaciones del carrito.

**Formato de respuesta**:
```json
{
  "action": "add" | "remove",
  "quantity": 3,
  "product_reference": {
    "type": "name" | "id" | "index" | "last",
    "value": "Camiseta Básica Azul"
  }
}
```

**Justificación**:
- ✅ **Precisión**: Formato estructurado fácil de validar y procesar
- ✅ **Contexto conversacional**: Maneja referencias como "el último", "ese", "más"
- ✅ **Múltiples tipos de referencia**: Soporta búsqueda por nombre, ID, índice o contexto
- ✅ **Validación**: JSON Schema permite validar la estructura

---

### 3. Arquitectura de 6 Nodos Especializados

**Decisión**: Separar funcionalidades en nodos independientes con responsabilidad única (Single Responsibility Principle).

**Nodos**:
1. `detect_intent` - Clasificación de intenciones
2. `browse` - Mostrar catálogo
3. `manage_cart` - Añadir/quitar productos
4. `view_cart` - Visualizar carrito
5. `checkout` - Proceso de compra
6. `out_of_context` - Preguntas no relacionadas

**Justificación**:
- ✅ **Modularidad**: Cada nodo es testeable independientemente
- ✅ **Mantenibilidad**: Modificar un nodo no afecta a otros
- ✅ **Claridad**: Flujo fácil de seguir y documentar
- ✅ **Extensibilidad**: Añadir nuevos nodos sin romper existentes

---

### 4. Nodo de Checkout Unificado

**Decisión**: Un solo nodo gestiona toda la recolección de datos y confirmación de compra.

**Justificación**:
- ✅ **Cohesión**: Lógica relacionada agrupada en un mismo lugar
- ✅ **Flujo natural**: Secuencia clara (validar carrito → nombre → ciudad → confirmar)
- ✅ **Estado simple**: Un nodo mantiene el estado del proceso de checkout
- ✅ **Menos transiciones**: Reduce complejidad del grafo

**Alternativa descartada**: Nodos separados para cada dato (más complejo sin beneficio real).

---

### 5. Soporte Multi-Proveedor de LLM

**Decisión**: Configuración centralizada en [app/config/llm_config.py](app/config/llm_config.py) para cambiar entre proveedores.

**Proveedores soportados**:
- **OpenAI** (GPT-4, GPT-3.5-turbo)
- **Anthropic** (Claude)
- **Google** (Gemini)

**Justificación**:
- ✅ **Flexibilidad**: Usuario elige según presupuesto y preferencias
- ✅ **Resiliencia**: Cambiar de proveedor si uno falla o tiene límites
- ✅ **Accesibilidad**: Google Gemini ofrece tier gratuito
- ✅ **Testing**: Permite probar con diferentes modelos

**Implementación**: Detección automática de API keys en variables de entorno.

---

### 6. Manejo de Preguntas Fuera de Contexto

**Decisión**: Nodo dedicado `out_of_context_node` para preguntas no relacionadas.

**Justificación**:
- ✅ **Experiencia de usuario**: Responde educadamente sin romper el flujo
- ✅ **Flexibilidad**: LLM genera respuestas contextuales y naturales
- ✅ **Redirección suave**: Guía al usuario de vuelta a funcionalidades del chatbot
- ✅ **Robustez**: No ignora al usuario ni da errores

**Ejemplo**: 
- Usuario: "¿quién ganó el mundial?" 
- Bot: "No tengo información sobre eso, pero puedo ayudarte a comprar productos. ¿Quieres ver el catálogo?"

---

### 7. Procesamiento por Mensaje (Un Ciclo por Invocación)

**Decisión**: Cada invocación del grafo procesa un solo mensaje del usuario.

**Funcionamiento**:
```python
# Cada mensaje del usuario inicia un nuevo ciclo
state = graph.invoke(state)  # Procesa UN mensaje
# El grafo termina en END
# Siguiente mensaje → nuevo invoke()
```

**Justificación**:
- ✅ **Control**: La aplicación mantiene control entre mensajes
- ✅ **Estado persistente**: Fácil guardar estado entre interacciones
- ✅ **Debugging**: Más fácil inspeccionar estado en cada paso
- ✅ **Flexibilidad**: Permite modificar estado antes del siguiente mensaje

---

## 🧪 Tests Automatizados

El proyecto implementa una estrategia de testing enfocada en validar la lógica de negocio y el comportamiento del grafo sin depender de APIs externas.

### Estrategia de Testing

#### Tests Unitarios ([tests/test_basic.py](tests/test_basic.py))

**Objetivo**: Validar lógica de negocio pura sin dependencias externas.

**Cobertura** (5 tests):
1. ✅ Añadir productos al carrito
2. ✅ Eliminar productos del carrito
3. ✅ Calcular total del carrito
4. ✅ Crear orden desde carrito
5. ✅ Inicializar estado conversacional

**Ventajas**:
- Muy rápidos (< 1 segundo todos los tests)
- No requieren API keys
- Validan modelos Pydantic y lógica de dominio
- 100% determinísticos

---

#### Tests de Integración con Mocks ([tests/test_nodes_mocked.py](tests/test_nodes_mocked.py))

**Objetivo**: Probar nodos y transiciones del grafo sin llamadas reales al LLM.

**Cobertura**:
1. ✅ Detección de intención (LLM mockeado)
2. ✅ Navegación de productos (catálogo mockeado)
3. ✅ Visualización del carrito
4. ✅ Routing condicional de edges
5. ✅ Flujo completo de estados

**Ventajas**:
- Tests determinísticos (misma entrada → misma salida)
- Sin costos de API
- Validan flujo del grafo completo
- Cobertura de nodos críticos

---