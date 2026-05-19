import hashlib
import re
from typing import Any

from pinecone import Pinecone, ServerlessSpec

from config import Config


def _normalize_menu_items(categories: list) -> list[dict]:
    """Flatten menu categories into searchable item records."""
    items = []
    for category in categories or []:
        category_name = category.get("name", "")
        products = category.get("products") or category.get("items") or []
        for product in products:
            items.append(
                {
                    "category": category_name,
                    "name": product.get("name", ""),
                    "price": product.get("price", ""),
                    "description": product.get("description", ""),
                    "allergens": product.get("allergens", []),
                    "spice_level": product.get("spice_level", ""),
                }
            )
    return items


def _item_to_text(item: dict, menu_name: str = "") -> str:
    parts = [
        f"Restoran menüsü: {menu_name}" if menu_name else "",
        f"Kategori: {item.get('category', '')}",
        f"Ürün: {item.get('name', '')}",
        f"Fiyat: {item.get('price', '')}",
    ]
    if item.get("description"):
        parts.append(f"Açıklama: {item['description']}")
    if item.get("allergens"):
        allergens = item["allergens"]
        if isinstance(allergens, list):
            parts.append(f"Alerjenler: {', '.join(allergens)}")
    if item.get("spice_level"):
        parts.append(f"Acılık: {item['spice_level']}")
    return " | ".join(p for p in parts if p)


class MenuVectorStore:
    """Pinecone-backed vector store for restaurant menu semantic search."""

    NAMESPACE_PREFIX = "restaurant"

    def __init__(self):
        self.api_key = Config.PINECONE_API_KEY
        self.index_name = Config.PINECONE_INDEX_NAME
        self.embed_model = Config.PINECONE_EMBED_MODEL
        self.dimension = Config.PINECONE_EMBED_DIMENSION
        self.top_k = Config.RAG_TOP_K
        self.pc = None
        self.index = None
        self.is_available = False

        if not self.api_key:
            print("⚠️ PINECONE_API_KEY not provided. Menu vector search disabled.")
            return

        try:
            self.pc = Pinecone(api_key=self.api_key)
            self._ensure_index()
            self.index = self.pc.Index(self.index_name)
            self.is_available = True
            print(f"✅ Pinecone menu index ready: {self.index_name}")
        except Exception as exc:
            print(f"❌ Failed to initialize Pinecone: {exc}")

    def _ensure_index(self):
        existing = {idx.name for idx in self.pc.list_indexes()}
        if self.index_name in existing:
            return

        print(f"📦 Creating Pinecone index: {self.index_name}")
        self.pc.create_index(
            name=self.index_name,
            dimension=self.dimension,
            metric="cosine",
            spec=ServerlessSpec(
                cloud=Config.PINECONE_CLOUD,
                region=Config.PINECONE_REGION,
            ),
        )

    def _namespace(self, restaurant_slug: str) -> str:
        safe = re.sub(r"[^a-zA-Z0-9_-]", "-", restaurant_slug)
        return f"{self.NAMESPACE_PREFIX}-{safe}"

    def _embed(self, texts: list[str], input_type: str) -> list[list[float]]:
        result = self.pc.inference.embed(
            model=self.embed_model,
            inputs=texts,
            parameters={"input_type": input_type, "truncate": "END"},
        )
        vectors = []
        for item in result.data:
            values = getattr(item, "values", None) or item.get("values")
            vectors.append(values)
        return vectors

    def _menu_content_hash(self, menu_data: dict) -> str:
        payload = str(menu_data.get("categories", [])) + str(menu_data.get("name", ""))
        return hashlib.md5(payload.encode("utf-8")).hexdigest()

    def index_restaurant_menu(
        self,
        restaurant_slug: str,
        menu_data: dict,
        force: bool = False,
    ) -> dict[str, Any]:
        """Index or re-index all menu items for a restaurant."""
        if not self.is_available:
            return {
                "success": False,
                "error": "Pinecone servisi kullanılamıyor. PINECONE_API_KEY ayarlayın.",
            }

        categories = menu_data.get("categories") or []
        items = _normalize_menu_items(categories)
        if not items:
            return {"success": False, "error": "İndekslenecek menü öğesi bulunamadı."}

        namespace = self._namespace(restaurant_slug)
        content_hash = self._menu_content_hash(menu_data)

        if not force:
            try:
                meta_probe = self.index.fetch(
                    ids=[f"{restaurant_slug}__meta"],
                    namespace=namespace,
                )
                vectors = meta_probe.vectors or {}
                if vectors:
                    stored_hash = vectors[f"{restaurant_slug}__meta"].metadata.get(
                        "content_hash"
                    )
                    if stored_hash == content_hash:
                        return {
                            "success": True,
                            "indexed": 0,
                            "skipped": True,
                            "message": "Menü zaten güncel.",
                        }
            except Exception:
                pass

        texts = [
            _item_to_text(item, menu_data.get("name", "")) for item in items
        ]
        embeddings = self._embed(texts, input_type="passage")

        vectors = []
        for idx, (item, embedding) in enumerate(zip(items, embeddings)):
            vector_id = f"{restaurant_slug}__{idx}"
            vectors.append(
                {
                    "id": vector_id,
                    "values": embedding,
                    "metadata": {
                        "restaurant_slug": restaurant_slug,
                        "category": item.get("category", ""),
                        "name": item.get("name", ""),
                        "price": str(item.get("price", "")),
                        "description": item.get("description", ""),
                        "text": texts[idx],
                        "type": "menu_item",
                    },
                }
            )

        vectors.append(
            {
                "id": f"{restaurant_slug}__meta",
                "values": embeddings[0],
                "metadata": {
                    "restaurant_slug": restaurant_slug,
                    "type": "meta",
                    "content_hash": content_hash,
                    "item_count": len(items),
                    "menu_name": menu_data.get("name", ""),
                },
            }
        )

        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            self.index.upsert(vectors=vectors[i : i + batch_size], namespace=namespace)

        return {
            "success": True,
            "indexed": len(items),
            "namespace": namespace,
            "skipped": False,
        }

    def search_menu(
        self,
        restaurant_slug: str,
        query: str,
        top_k: int | None = None,
    ) -> list[dict]:
        """Semantic search over menu items for a restaurant."""
        if not self.is_available or not query.strip():
            return []

        namespace = self._namespace(restaurant_slug)
        k = top_k or self.top_k

        try:
            query_embedding = self._embed([query], input_type="query")[0]
            results = self.index.query(
                namespace=namespace,
                vector=query_embedding,
                top_k=k,
                include_metadata=True,
                filter={"type": {"$eq": "menu_item"}},
            )

            matches = []
            for match in results.matches or []:
                meta = match.metadata or {}
                matches.append(
                    {
                        "score": match.score,
                        "category": meta.get("category", ""),
                        "name": meta.get("name", ""),
                        "price": meta.get("price", ""),
                        "description": meta.get("description", ""),
                        "text": meta.get("text", ""),
                    }
                )
            return matches
        except Exception as exc:
            print(f"Pinecone search error: {exc}")
            return []

    def format_search_results(self, matches: list[dict]) -> str:
        if not matches:
            return ""

        lines = []
        for match in matches:
            line = f"- {match.get('name', '')} ({match.get('category', '')})"
            if match.get("price"):
                line += f" — {match['price']}"
            if match.get("description"):
                line += f": {match['description']}"
            lines.append(line)
        return "\n".join(lines)

    def delete_restaurant_index(self, restaurant_slug: str) -> bool:
        if not self.is_available:
            return False
        try:
            self.index.delete(namespace=self._namespace(restaurant_slug), delete_all=True)
            return True
        except Exception as exc:
            print(f"Pinecone delete error: {exc}")
            return False

    def get_status(self) -> dict:
        return {
            "available": self.is_available,
            "index_name": self.index_name if self.is_available else None,
            "embed_model": self.embed_model if self.is_available else None,
            "api_key_set": bool(self.api_key),
        }
