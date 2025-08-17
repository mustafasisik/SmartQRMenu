import google.generativeai as genai
import json
from config import Config
from PIL import Image
import base64
import io

class GeminiAIService:
    """Service class for interacting with Google Gemini AI"""
    
    def __init__(self):
        """Initialize the Gemini AI service"""
        self.api_key = Config.GEMINI_API_KEY
        self.model_name = 'gemini-1.5-flash-latest'  # Use latest model
        self.model = None
        self.is_available = False
        
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel(self.model_name)
                self.is_available = True
                print(f"✅ Gemini AI initialized successfully with model: {self.model_name}")
            except Exception as e:
                print(f"❌ Failed to initialize Gemini AI: {e}")
                self.is_available = False
        else:
            print("⚠️ GEMINI_API_KEY not provided. AI features disabled.")
    
    def get_restaurant_context(self, restaurant_data):
        """Create a context string from restaurant data for AI prompts"""
        
        # Extract restaurant info
        restaurant = restaurant_data.get('restaurant', {})
        chef = restaurant_data.get('chef', {})
        menu = restaurant_data.get('menu', {})
        reviews = restaurant_data.get('reviews', [])
        faq = restaurant_data.get('faq', [])
        
        context = f"""
        Sen bu restoranın garsonusun ve müşterilerin sorularına cevap veriyorsun.
        Cevapların 2-3 cümleyi geçmemeli.
        Bu restoran hakkında bilgiler:
        
        Restoran: {restaurant.get('name', 'Bilinmiyor')}
        Slogan: {restaurant.get('tagline', 'Bilinmiyor')}
        Açıklama: {restaurant.get('description', 'Bilinmiyor')}
        
        Adres: {restaurant.get('address', {}).get('street', 'Bilinmiyor')}, {restaurant.get('address', {}).get('district', 'Bilinmiyor')}, {restaurant.get('address', {}).get('city', 'Bilinmiyor')}
        Telefon: {restaurant.get('contact', {}).get('phone', 'Bilinmiyor')}
        E-posta: {restaurant.get('contact', {}).get('email', 'Bilinmiyor')}
        
        Çalışma Saatleri: {restaurant.get('hours', {}).get('monday', 'Bilinmiyor')} (Pazartesi örneği)
        
        Şef: {chef.get('name', 'Bilinmiyor')}
        Şef Unvanı: {chef.get('title', 'Bilinmiyor')}
        Şef Deneyimi: {chef.get('experience', 'Bilinmiyor')}
        Şef Uzmanlıkları: {', '.join(chef.get('specialties', []))}
        
        Restoran Özellikleri: {', '.join(restaurant.get('features', []))}
        Restoran Ödülleri: {', '.join(restaurant.get('awards', []))}
        
        Menü Kategorileri:
        """
        
        # Handle menu categories
        categories = menu.get('categories', [])
        for category in categories:
            context += f"\n- {category.get('name', 'Bilinmiyor')}:"
            items = category.get('items', [])
            for item in items:
                context += f"\n  * {item.get('name', 'Bilinmiyor')} - {item.get('price', 'Bilinmiyor')}"
                if item.get('description'):
                    context += f" ({item.get('description')})"
        
        context += "\n\nMüşteri Yorumları:"
        for review in reviews:
            context += f"\n- {review.get('customer', 'Anonim')}: {review.get('rating', '0')}/5 yıldız"
            context += f"\n  {review.get('comment', '')}"
        
        context += "\n\nSSS:"
        for faq_item in faq:
            context += f"\nS: {faq_item.get('question', '')}"
            context += f"\nC: {faq_item.get('answer', '')}"
        
        return context
    
    def ask_question(self, question, restaurant_data):
        """Ask a question about the restaurant using Gemini AI"""
        if not self.is_available:
            return {
                'success': False,
                'error': 'AI servisi mevcut değil. Lütfen GEMINI_API_KEY ayarlayın.',
                'answer': None
            }
        
        try:
            # Create context from restaurant data
            context = self.get_restaurant_context(restaurant_data)
            
            # Create the prompt
            prompt = f"""
            {context}
            
            Kullanıcı Sorusu: {question}
            
            Lütfen yukarıdaki restoran bilgilerine dayanarak bu soruyu Türkçe olarak yanıtlayın. 
            Eğer bilgi mevcut değilse, "Bu konuda bilgi bulunmamaktadır" şeklinde yanıtlayın.
            Yanıtınız kısa, net ve yardımcı olsun.
            """
            
            # Generate response
            response = self.model.generate_content(prompt)
            
            return {
                'success': True,
                'answer': response.text,
                'error': None
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'AI yanıtı oluşturulurken hata: {str(e)}',
                'answer': None
            }
    
    def get_status(self):
        """Get the current status of the AI service"""
        return {
            'available': self.is_available,
            'model': self.model_name if self.is_available else None,
            'api_key_set': bool(self.api_key)
        }
    
    def test_basic_functionality(self):
        """Test if the basic Gemini functionality works"""
        if not self.is_available:
            return {
                'success': False,
                'error': 'AI service not available'
            }
        
        try:
            # Simple text generation test
            test_prompt = "Say 'Hello World' in Turkish"
            response = self.model.generate_content(test_prompt)
            
            return {
                'success': True,
                'response': response.text,
                'message': 'Basic Gemini functionality working'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Basic test failed: {str(e)}'
            }
    
    def analyze_menu_image(self, image_base64, language='tr'):
        """Analyze a menu image and extract menu information using Gemini AI"""
        if not self.is_available:
            return {
                'success': False,
                'error': 'AI servisi mevcut değil. Lütfen GEMINI_API_KEY ayarlayın.',
                'suggestions': None
            }
        
        try:
            # Create the prompt for menu analysis (same as working test code)
            if language == 'tr':
                prompt = "Bu menüdeki tüm yazıları oku ve listele. Yazıların yanında fiyatları da listele. Lütfen aşağıdaki JSON formatında yanıt verin: {\"menuName\": \"Menü adı\", \"description\": \"Menü açıklaması\", \"categories\": [{\"name\": \"Kategori adı\", \"products\": [{\"name\": \"Ürün adı\", \"price\": \"Fiyat (TL)\", \"description\": \"Ürün açıklaması\"}]}]}"
            else:
                prompt = "Read all text from this menu and list them. Include prices next to the items. Please respond in the following JSON format: {\"menuName\": \"Menu name\", \"description\": \"Menu description\", \"categories\": [{\"name\": \"Category name\", \"products\": [{\"name\": \"Product name\", \"price\": \"Price (TL)\", \"description\": \"Product description\"}]}]}"
            
            # Create image part for Gemini using Pillow
            try:
                # Convert base64 to PIL Image
                image_data = base64.b64decode(image_base64)
                pil_image = Image.open(io.BytesIO(image_data))
                
                print(f"🤖 Image loaded with Pillow: size={pil_image.size}, mode={pil_image.mode}")
                
                # Use the same approach as working test code
                response = self.model.generate_content([prompt, pil_image], stream=True)
                response.resolve()  # Resolve the stream
                
                print(f"🤖 Gemini response received successfully")
                
            except Exception as e:
                print(f"❌ Pillow method failed: {e}")
                
                # Fallback to base64 method
                try:
                    image_part = {
                        "mime_type": "image/jpeg",
                        "data": image_base64
                    }
                    
                    print(f"🤖 Falling back to base64 method")
                    response = self.model.generate_content([prompt, image_part])
                    
                except Exception as e2:
                    print(f"❌ Base64 fallback also failed: {e2}")
                    raise e2
            
            # Parse the response to extract JSON
            response_text = response.text.strip()
            print(f"🤖 Gemini response received: {len(response_text)} chars")
            print(f"🤖 Response preview: {response_text[:200]}...")
            
            # Try to extract JSON from the response
            try:
                # Remove any markdown formatting
                if response_text.startswith('```json'):
                    response_text = response_text[7:]
                if response_text.endswith('```'):
                    response_text = response_text[:-3]
                
                # Parse JSON
                suggestions = json.loads(response_text.strip())
                
                print(f"✅ Successfully parsed JSON response")
                
                return {
                    'success': True,
                    'suggestions': suggestions,
                    'error': None
                }
                
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse AI response as JSON: {e}")
                print(f"Response text: {response_text}")
                
                # Try to extract JSON from text if it's not pure JSON
                try:
                    # Look for JSON-like content in the response
                    start_idx = response_text.find('{')
                    end_idx = response_text.rfind('}') + 1
                    
                    if start_idx != -1 and end_idx != -1:
                        json_text = response_text[start_idx:end_idx]
                        suggestions = json.loads(json_text)
                        print(f"✅ Extracted JSON from text response")
                        
                        return {
                            'success': True,
                            'suggestions': suggestions,
                            'error': None
                        }
                except:
                    pass
                
                # Return a fallback response
                return {
                    'success': True,
                    'suggestions': {
                        'menuName': 'Menü Adı',
                        'description': 'Menü açıklaması buraya gelecek',
                        'categories': []
                    },
                    'error': 'AI yanıtı JSON formatında değil, varsayılan format kullanıldı'
                }
            
        except Exception as e:
            print(f"❌ Error analyzing menu image: {e}")
            return {
                'success': False,
                'error': f'Menü görseli analiz edilirken hata: {str(e)}',
                'suggestions': None
            }
