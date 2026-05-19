import base64
import io
import json

from groq import Groq
from PIL import Image

from config import Config


class GroqAIService:
    """Groq LLM service for chat and menu image analysis."""

    def __init__(self):
        self.api_key = Config.GROQ_API_KEY
        self.chat_model = Config.GROQ_CHAT_MODEL
        self.vision_model = Config.GROQ_VISION_MODEL
        self.client = None
        self.is_available = False

        if self.api_key:
            try:
                self.client = Groq(api_key=self.api_key)
                self.is_available = True
                print(
                    f"✅ Groq AI initialized (chat={self.chat_model}, "
                    f"vision={self.vision_model})"
                )
            except Exception as exc:
                print(f"❌ Failed to initialize Groq AI: {exc}")
        else:
            print("⚠️ GROQ_API_KEY not provided. AI features disabled.")

    def _chat_completion(self, messages, model=None, temperature=0.4, max_tokens=512):
        if not self.is_available:
            raise RuntimeError("Groq AI service is not available")

        response = self.client.chat.completions.create(
            model=model or self.chat_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = response.choices[0].message.content
        return content.strip() if content else ""

    def get_response(self, system_prompt, user_prompt):
        """Simple text generation with system + user messages."""
        if not self.is_available:
            return "Üzgünüm, AI servisimiz şu anda kullanılamıyor."

        try:
            return self._chat_completion(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ]
            )
        except Exception as exc:
            print(f"Groq AI error: {exc}")
            return "Üzgünüm, AI servisimizde bir hata oluştu. Lütfen tekrar deneyin."

    def answer_with_context(
        self,
        question,
        restaurant_data,
        menu_context,
        chat_history=None,
        usage_stats=None,
    ):
        """Answer a restaurant question using retrieved menu context (RAG)."""
        if not self.is_available:
            return {
                "success": False,
                "error": "AI servisi mevcut değil. Lütfen GROQ_API_KEY ayarlayın.",
                "answer": None,
            }

        restaurant = restaurant_data or {}
        system_prompt = self._build_system_prompt(restaurant, menu_context, usage_stats)
        messages = [{"role": "system", "content": system_prompt}]

        if chat_history:
            for msg in chat_history[-5:]:
                role = msg.get("role", "user")
                if role not in ("user", "assistant"):
                    role = "user" if role == "user" else "assistant"
                messages.append(
                    {
                        "role": role,
                        "content": msg.get("content", ""),
                    }
                )

        messages.append({"role": "user", "content": question})

        try:
            answer = self._chat_completion(messages)
            return {"success": True, "answer": answer, "error": None}
        except Exception as exc:
            return {
                "success": False,
                "error": f"AI yanıtı oluşturulurken hata: {exc}",
                "answer": None,
            }

    def _build_system_prompt(self, restaurant, menu_context, usage_stats=None):
        hours = restaurant.get("hours") or {}
        limits_info = ""
        if usage_stats:
            limits_info = (
                f"\nKullanım: günlük {usage_stats.get('daily_used', 0)}/"
                f"{usage_stats.get('daily_limit', 10)} mesaj."
            )

        return f"""Sen bu restoranın garsonusun. Müşteri sorularına kısa, net ve Türkçe cevap ver.
Cevapların 2-3 cümleyi geçmesin. Her seferinde selamlama yapma.

Restoran:
- Ad: {restaurant.get('name', 'Bilinmiyor')}
- Açıklama: {restaurant.get('description', 'Bilinmiyor')}
- Mutfak: {', '.join(restaurant.get('cuisineTypes', []))}
- Etiketler: {', '.join(restaurant.get('tags', []))}
- Telefon: {restaurant.get('phone', 'Bilinmiyor')}
- E-posta: {restaurant.get('email', 'Bilinmiyor')}
- Website: {restaurant.get('website', 'Bilinmiyor')}
- Adres: {restaurant.get('address', 'Bilinmiyor')}
- Saatler: {hours.get('open', '?')} - {hours.get('close', '?')}
{limits_info}

Menüden ilgili bilgiler (vektör arama sonucu):
{menu_context or 'Menü bilgisi bulunamadı. Genel restoran bilgileriyle yanıtla.'}

Kurallar:
1. Önce menü bağlamındaki bilgileri kullan.
2. Bilgi yoksa "Bu konuda menümüzde bilgi bulunmuyor" de.
3. Fiyat ve ürün adlarını menü bağlamından ver; uydurma.
4. Önceki mesajlarla tutarlı ol."""

    def get_status(self):
        return {
            "available": self.is_available,
            "provider": "groq",
            "chat_model": self.chat_model if self.is_available else None,
            "vision_model": self.vision_model if self.is_available else None,
            "api_key_set": bool(self.api_key),
        }

    def test_basic_functionality(self):
        if not self.is_available:
            return {"success": False, "error": "AI service not available"}

        try:
            response = self._chat_completion(
                [{"role": "user", "content": "Say 'Merhaba' in Turkish only."}],
                max_tokens=32,
            )
            return {
                "success": True,
                "response": response,
                "message": "Basic Groq functionality working",
            }
        except Exception as exc:
            return {"success": False, "error": f"Basic test failed: {exc}"}

    def analyze_menu_image(self, image_base64, language="tr"):
        """Analyze menu image with Groq vision model and return structured JSON."""
        if not self.is_available:
            return {
                "success": False,
                "error": "AI servisi mevcut değil. Lütfen GROQ_API_KEY ayarlayın.",
                "suggestions": None,
            }

        if language == "tr":
            prompt = (
                "Bu menüdeki tüm yazıları oku ve listele. Fiyatları da ekle. "
                'Yanıtı yalnızca şu JSON formatında ver: {"menuName": "...", '
                '"description": "...", "categories": [{"name": "...", '
                '"products": [{"name": "...", "price": "...", "description": "..."}]}]}'
            )
        else:
            prompt = (
                "Read all text from this menu image including prices. "
                'Respond only in JSON: {"menuName": "...", "description": "...", '
                '"categories": [{"name": "...", "products": [{"name": "...", '
                '"price": "...", "description": "..."}]}]}'
            )

        try:
            image_data = base64.b64decode(image_base64)
            pil_image = Image.open(io.BytesIO(image_data))
            if pil_image.mode not in ("RGB", "L"):
                pil_image = pil_image.convert("RGB")

            buffer = io.BytesIO()
            pil_image.save(buffer, format="JPEG")
            b64_image = base64.b64encode(buffer.getvalue()).decode("utf-8")

            response_text = self._chat_completion(
                [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{b64_image}",
                                },
                            },
                        ],
                    }
                ],
                model=self.vision_model,
                temperature=0.2,
                max_tokens=4096,
            )

            return self._parse_menu_json_response(response_text)

        except Exception as exc:
            print(f"❌ Error analyzing menu image: {exc}")
            return {
                "success": False,
                "error": f"Menü görseli analiz edilirken hata: {exc}",
                "suggestions": None,
            }

    def _parse_menu_json_response(self, response_text):
        text = response_text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        try:
            suggestions = json.loads(text)
            return {"success": True, "suggestions": suggestions, "error": None}
        except json.JSONDecodeError:
            start_idx = text.find("{")
            end_idx = text.rfind("}") + 1
            if start_idx != -1 and end_idx > start_idx:
                try:
                    suggestions = json.loads(text[start_idx:end_idx])
                    return {"success": True, "suggestions": suggestions, "error": None}
                except json.JSONDecodeError:
                    pass

            return {
                "success": True,
                "suggestions": {
                    "menuName": "Menü Adı",
                    "description": "Menü açıklaması",
                    "categories": [],
                },
                "error": "AI yanıtı JSON formatında değil, varsayılan format kullanıldı",
            }
