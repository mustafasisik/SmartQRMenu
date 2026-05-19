from groq_service import GroqAIService
from menu_vector_store import MenuVectorStore


class RestaurantRAGService:
    """
    RAG pipeline: Pinecone menu vector search → Groq answer generation.
    """

    def __init__(self, groq_service: GroqAIService | None = None):
        self.groq = groq_service or GroqAIService()
        self.vector_store = MenuVectorStore()

    @property
    def is_available(self) -> bool:
        return self.groq.is_available

    def sync_menu_from_firestore(
        self,
        restaurant_slug: str,
        get_menu_fn,
        force: bool = False,
    ) -> dict:
        """Load menu from Firestore callback and index into Pinecone."""
        menu_data = get_menu_fn(restaurant_slug)
        if not menu_data or not menu_data.get("categories"):
            return {"success": False, "error": "Menü verisi bulunamadı."}
        return self.vector_store.index_restaurant_menu(
            restaurant_slug, menu_data, force=force
        )

    def _ensure_menu_indexed(self, restaurant_slug: str, get_menu_fn) -> None:
        if not self.vector_store.is_available:
            return
        self.sync_menu_from_firestore(restaurant_slug, get_menu_fn, force=False)

    def ask_question(
        self,
        question: str,
        restaurant_data: dict,
        get_menu_fn,
        chat_history=None,
        usage_stats=None,
    ) -> dict:
        """
        1. Index menu if needed
        2. Vector search relevant menu items
        3. Ask Groq with retrieved context
        """
        if not self.is_available:
            return {
                "success": False,
                "error": "AI servisi mevcut değil. Lütfen GROQ_API_KEY ayarlayın.",
                "answer": None,
            }

        restaurant_slug = restaurant_data.get("id") or restaurant_data.get("slug")
        if not restaurant_slug:
            return {
                "success": False,
                "error": "Restoran kimliği bulunamadı.",
                "answer": None,
            }

        menu_context = ""
        sources = []

        if self.vector_store.is_available and get_menu_fn:
            self._ensure_menu_indexed(restaurant_slug, get_menu_fn)
            matches = self.vector_store.search_menu(restaurant_slug, question)
            menu_context = self.vector_store.format_search_results(matches)
            sources = matches
        elif get_menu_fn:
            menu_data = get_menu_fn(restaurant_slug) or {}
            menu_context = self._fallback_menu_text(menu_data)

        result = self.groq.answer_with_context(
            question=question,
            restaurant_data=restaurant_data,
            menu_context=menu_context,
            chat_history=chat_history,
            usage_stats=usage_stats,
        )
        result["sources"] = sources
        return result

    def _fallback_menu_text(self, menu_data: dict) -> str:
        """Plain-text fallback when Pinecone is unavailable."""
        lines = []
        if menu_data.get("name"):
            lines.append(f"Menü: {menu_data['name']}")
        for category in menu_data.get("categories") or []:
            cat_name = category.get("name", "")
            products = category.get("products") or category.get("items") or []
            for product in products:
                line = f"- {product.get('name', '')} ({cat_name})"
                if product.get("price"):
                    line += f" — {product['price']}"
                if product.get("description"):
                    line += f": {product['description']}"
                lines.append(line)
        return "\n".join(lines)

    def get_response(self, system_prompt: str, user_prompt: str) -> str:
        return self.groq.get_response(system_prompt, user_prompt)

    def analyze_menu_image(self, image_base64: str, language: str = "tr") -> dict:
        return self.groq.analyze_menu_image(image_base64, language)

    def get_status(self) -> dict:
        return {
            "groq": self.groq.get_status(),
            "pinecone": self.vector_store.get_status(),
            "available": self.is_available,
        }

    def test_basic_functionality(self) -> dict:
        return self.groq.test_basic_functionality()
