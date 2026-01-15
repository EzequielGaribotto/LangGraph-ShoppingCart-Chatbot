"""
Servicio de gestión del catálogo de productos.
"""
import json
from pathlib import Path
from typing import List, Optional, Dict
from difflib import SequenceMatcher

from models import Product


class CatalogService:
    """
    Servicio para gestionar el catálogo de productos.
    
    Proporciona funcionalidades de carga, búsqueda y filtrado de productos.
    """
    
    def __init__(self, catalog_path: Optional[Path] = None):
        """
        Inicializa el servicio de catálogo.
        
        Args:
            catalog_path: Ruta al archivo JSON del catálogo. Si no se proporciona,
                         usa la ruta por defecto (data/catalog.json)
        """
        if catalog_path is None:
            # Ruta por defecto relativa al proyecto
            project_root = Path(__file__).parent.parent.parent
            catalog_path = project_root / "data" / "catalog.json"
        
        self.catalog_path = catalog_path
        self._products: Dict[str, Product] = {}
        self._loaded = False
    
    def load_catalog(self) -> None:
        """
        Carga el catálogo de productos desde el archivo JSON.
        
        Raises:
            FileNotFoundError: Si el archivo de catálogo no existe
            ValueError: Si el JSON está mal formado o los datos son inválidos
        """
        if not self.catalog_path.exists():
            raise FileNotFoundError(
                f"Archivo de catálogo no encontrado: {self.catalog_path}"
            )
        
        try:
            with open(self.catalog_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            products_data = data.get("products", [])
            
            for product_dict in products_data:
                try:
                    product = Product(**product_dict)
                    self._products[product.id] = product
                except Exception as e:
                    # Log el error pero continúa cargando otros productos
                    print(f"⚠️  Error al cargar producto {product_dict.get('id')}: {e}")
            
            self._loaded = True
            print(f"✅ Catálogo cargado: {len(self._products)} productos")
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Error al parsear JSON del catálogo: {e}")
        except Exception as e:
            raise ValueError(f"Error al cargar catálogo: {e}")
    
    def ensure_loaded(self) -> None:
        """Asegura que el catálogo esté cargado antes de usarlo."""
        if not self._loaded:
            self.load_catalog()
    
    def get_all_products(self) -> List[Product]:
        """
        Obtiene todos los productos del catálogo.
        
        Returns:
            Lista de todos los productos disponibles
        """
        self.ensure_loaded()
        return list(self._products.values())
    
    def get_by_id(self, product_id: str) -> Optional[Product]:
        """
        Busca un producto por su ID.
        
        Args:
            product_id: ID del producto
            
        Returns:
            Producto si se encuentra, None en caso contrario
        """
        self.ensure_loaded()
        return self._products.get(product_id)
    
    def get_by_name(self, name: str) -> Optional[Product]:
        """
        Busca un producto por nombre exacto (case-insensitive).
        
        Args:
            name: Nombre del producto a buscar
            
        Returns:
            Producto si se encuentra, None en caso contrario
        """
        self.ensure_loaded()
        name_lower = name.lower().strip()
        
        for product in self._products.values():
            if product.name.lower() == name_lower:
                return product
        return None
    
    def search_products(self, query: str, min_similarity: float = 0.4) -> List[Product]:
        """
        Busca productos por texto en nombre o descripción.
        
        Usa búsqueda fuzzy para tolerar errores de escritura.
        
        Args:
            query: Texto a buscar
            min_similarity: Similitud mínima para considerar un match (0.0 a 1.0)
            
        Returns:
            Lista de productos que coinciden, ordenados por relevancia
        """
        self.ensure_loaded()
        query_lower = query.lower().strip()
        
        if not query_lower:
            return []
        
        matches = []
        
        for product in self._products.values():
            # Buscar en nombre
            name_ratio = SequenceMatcher(
                None, query_lower, product.name.lower()
            ).ratio()
            
            # Buscar en descripción
            desc_ratio = SequenceMatcher(
                None, query_lower, product.description.lower()
            ).ratio()
            
            # Buscar en categoría
            cat_ratio = SequenceMatcher(
                None, query_lower, product.category.lower()
            ).ratio()
            
            # Tomar el mejor ratio
            best_ratio = max(name_ratio, desc_ratio * 0.8, cat_ratio * 0.9)
            
            # También verificar si el query está contenido como substring
            if (query_lower in product.name.lower() or 
                query_lower in product.description.lower() or
                query_lower in product.category.lower()):
                best_ratio = max(best_ratio, 0.7)
            
            if best_ratio >= min_similarity:
                matches.append((product, best_ratio))
        
        # Ordenar por relevancia (ratio más alto primero)
        matches.sort(key=lambda x: x[1], reverse=True)
        
        return [product for product, _ in matches]
    
    def __repr__(self) -> str:
        """Representación técnica del servicio."""
        return f"CatalogService(products={len(self._products)}, loaded={self._loaded})"
    
    def __str__(self) -> str:
        """Representación legible del servicio."""
        if self._loaded:
            return f"Catálogo con {len(self._products)} productos"
        return "Catálogo no cargado"
