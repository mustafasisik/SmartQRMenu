import os
import re
import time
import firebase_admin
from firebase_admin import credentials, auth, firestore
from config import Config
from gemini_service import GeminiAIService

class FirebaseService:
    """Firebase service for authentication and database operations"""
    
    def __init__(self):
        """Initialize Firebase services"""
        self.admin_app = None
        self.auth = None
        self.firestore_db = None
        self.is_available = False
        
        try:
            # Initialize Firebase Admin SDK
            if not firebase_admin._apps:

                firebase_creds = {
                    "type": "service_account",
                    "project_id": os.getenv("FIREBASE_PROJECT_ID"),
                    "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
                    "private_key": os.getenv("FIREBASE_PRIVATE_KEY").replace("\\n", "\n"),
                    "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
                    "client_id": os.getenv("FIREBASE_CLIENT_ID"),
                    "auth_uri": os.getenv("FIREBASE_AUTH_URI"),
                    "token_uri": os.getenv("FIREBASE_TOKEN_URI"),
                    "auth_provider_x509_cert_url": os.getenv("FIREBASE_AUTH_PROVIDER_CERT"),
                    "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_CERT_URL"),
                }
                

                cred = credentials.Certificate(firebase_creds)
                self.admin_app = firebase_admin.initialize_app(cred)
                print("✅ Firebase Admin SDK initialized successfully")
            else:
                existing_apps = list(firebase_admin._apps.keys())
                self.admin_app = firebase_admin._apps.get("__default__", firebase_admin._apps[existing_apps[0]])
                print(f"✅ Using existing Firebase app: {self.admin_app.name}")
            
            # Initialize Firebase Auth
            if self.admin_app:
                self.auth = auth
                print("✅ Firebase Auth initialized successfully")
            
            # Initialize Firestore
            if self.admin_app:
                self.firestore_db = firestore.client()
                print("✅ Firestore initialized successfully")
            
            # Check if Firebase config is available for client-side
            firebase_config = {
                "apiKey": os.environ.get('FIREBASE_API_KEY'),
                "authDomain": os.environ.get('FIREBASE_AUTH_DOMAIN'),
                "projectId": os.environ.get('FIREBASE_PROJECT_ID'),
                "storageBucket": os.environ.get('FIREBASE_STORAGE_BUCKET'),
                "messagingSenderId": os.environ.get('FIREBASE_MESSAGING_SENDER_ID'),
                "appId": os.environ.get('FIREBASE_APP_ID')
            }

            # Check if all required config values are present
            if all(firebase_config.values()):
                self.is_available = True
                print("✅ Firebase Admin SDK initialized successfully")
            else:
                print("⚠️ Firebase configuration incomplete. Some features will be disabled.")
            
            # Additional check for Firestore DB
            if not self.firestore_db:
                print("❌ Firestore DB initialization failed")
                self.is_available = False
            else:
                print("✅ Firestore DB is available")
            
            # Initialize Gemini AI service
            try:
                self.gemini_service = GeminiAIService()
                print("✅ Gemini AI service initialized successfully")
            except Exception as ai_error:
                print(f"⚠️ Gemini AI service initialization failed: {ai_error}")
                self.gemini_service = None
                
        except Exception as e:
            print(f"❌ Failed to initialize Firebase: {e}")
            self.is_available = False
    
    def verify_token(self, id_token):
        """Verify Firebase ID token"""
        if not self.admin_app:
            return None
        
        try:
            decoded_token = auth.verify_id_token(id_token)
            return decoded_token
        except Exception as e:
            print(f"Token verification failed: {e}")
            return None
    
    def get_user_by_uid(self, uid):
        """Get user information by UID"""
        if not self.admin_app:
            return None
        
        try:
            user = auth.get_user(uid)
            
            # Get user role from Firestore
            user_role = self.get_user_role(uid)
            
            return {
                'uid': user.uid,
                'email': user.email,
                'display_name': user.display_name,
                'photo_url': user.photo_url,
                'email_verified': user.email_verified,
                'role': user_role
            }
        except Exception as e:
            print(f"Failed to get user: {e}")
            return None
    
    def get_user_role(self, uid):
        """Get user role from Firestore"""
        if not self.firestore_db:
            print(f"❌ Firestore DB not available for role check for user: {uid}")
            return 'subscriber'  # Default role
        
        try:
            
            # Get user role from Firestore users collection
            user_doc = self.firestore_db.collection('users').document(uid).get()
            if user_doc.exists:
                user_data = user_doc.to_dict()
                role = user_data.get('role', 'subscriber')
                print(f"✅ User {uid} role from Firestore: {role}")
                return role
            else:
                print(f"⚠️ User {uid} not found in Firestore users collection, using default role: subscriber")
                return 'subscriber'  # Default role
            
        except Exception as e:
            print(f"❌ Failed to get user role for {uid}: {e}")
            return 'subscriber'
    
    def set_user_role(self, uid, role):
        """Set user role in Firestore"""
        if not self.firestore_db:
            return False
        
        try:
            # Validate role
            valid_roles = ['admin', 'editor', 'owner', 'subscriber']
            if role not in valid_roles:
                print(f"Invalid role: {role}")
                return False
            
            # Update user role
            self.firestore_db.collection('users').document(uid).set({
                'role': role,
                'updated_at': firestore.SERVER_TIMESTAMP
            }, merge=True)
            
            return True
            
        except Exception as e:
            print(f"Failed to set user role: {e}")
            return False
    
    def get_all_users(self):
        """Get all users from Firestore"""
        if not self.firestore_db:
            return []
        
        try:
            users = []
            users_ref = self.firestore_db.collection('users').stream()
            
            for user_doc in users_ref:
                user_data = user_doc.to_dict()
                user_data['uid'] = user_doc.id
                
                # Get additional info from Firebase Auth if available
                try:
                    auth_user = self.auth.get_user(user_doc.id)
                    user_data['email'] = auth_user.email
                    user_data['display_name'] = auth_user.display_name
                    user_data['photo_url'] = auth_user.photo_url
                    user_data['email_verified'] = auth_user.email_verified
                except:
                    pass
                
                users.append(user_data)
            
            return users
            
        except Exception as e:
            print(f"Failed to get all users: {e}")
            return []
    
    def list_users_with_roles(self):
        """List all users with their roles for debugging"""
        if not self.firestore_db:
            print("❌ Firestore DB not available")
            return
        
        try:
            print("\n👥 Users in Firestore with roles:")
            print("=" * 50)
            
            users_ref = self.firestore_db.collection('users').stream()
            user_count = 0
            
            for user_doc in users_ref:
                user_data = user_doc.to_dict()
                user_count += 1
                
                email = user_data.get('email', 'No email')
                role = user_data.get('role', 'No role')
                uid = user_doc.id
                
                print(f"📧 {email}")
                print(f"   UID: {uid}")
                print(f"   Role: {role}")
                print(f"   Display Name: {user_data.get('display_name', 'No name')}")
                print("-" * 30)
            
            if user_count == 0:
                print("❌ No users found in Firestore users collection")
            else:
                print(f"✅ Found {user_count} users in Firestore")
                
        except Exception as e:
            print(f"❌ Error listing users: {e}")
    
    def update_user_role_by_email(self, email, new_role):
        """Update user role by email address"""
        if not self.firestore_db:
            print("❌ Firestore DB not available")
            return False
        
        try:
            # Find user by email
            users_ref = self.firestore_db.collection('users')
            query = users_ref.where('email', '==', email)
            docs = query.stream()
            
            user_found = False
            for doc in docs:
                user_found = True
                uid = doc.id
                
                # Update role
                self.firestore_db.collection('users').document(uid).update({
                    'role': new_role,
                    'updated_at': firestore.SERVER_TIMESTAMP
                })
                
                print(f"✅ Updated role for {email} to {new_role}")
                return True
            
            if not user_found:
                print(f"❌ User with email {email} not found in Firestore")
                return False
                
        except Exception as e:
            print(f"❌ Error updating user role: {e}")
            return False
    
    def get_all_restaurants(self):
        """Get all restaurants from Firestore"""
        if not self.firestore_db:
            return []
        
        try:
            restaurants = []
            restaurants_ref = self.firestore_db.collection('restaurants').stream()
            
            for restaurant_doc in restaurants_ref:
                restaurant_data = restaurant_doc.to_dict()
                restaurant_data['id'] = restaurant_doc.id
                restaurants.append(restaurant_data)
            
            return restaurants
            
        except Exception as e:
            print(f"Failed to get all restaurants: {e}")
            return []
    
    def get_featured_restaurants(self):
        """Get featured restaurants from Firestore"""
        if not self.firestore_db:
            return []
        
        try:
            restaurants = []
            restaurants_ref = self.firestore_db.collection('restaurants').where('featured', '==', True).where('isActive', '==', True).stream()
            
            for restaurant_doc in restaurants_ref:
                restaurant_data = restaurant_doc.to_dict()
                restaurant_data['id'] = restaurant_doc.id
                restaurants.append(restaurant_data)
            
            print(f"✅ Retrieved {len(restaurants)} featured restaurants")
            return restaurants
            
        except Exception as e:
            print(f"❌ Error getting featured restaurants: {e}")
            return []
    
    def get_restaurant_by_slug(self, slug):
        """Get restaurant by slug from Firestore"""
        if not self.firestore_db:
            return None
        
        try:
            restaurant_doc = self.firestore_db.collection('restaurants').document(slug).get()
            
            if restaurant_doc.exists:
                restaurant_data = restaurant_doc.to_dict()
                restaurant_data['id'] = restaurant_doc.id
                print(f"✅ Retrieved restaurant: {restaurant_data.get('name', 'Unknown')}")
                return restaurant_data
            else:
                print(f"❌ Restaurant not found with slug: {slug}")
                return None
                
        except Exception as e:
            print(f"❌ Error getting restaurant by slug: {e}")
            return None
    
    def get_restaurant_menu(self, restaurant_slug):
        """Get restaurant menu from Firestore"""
        if not self.firestore_db:
            print("❌ Firestore DB not available")
            return []
        
        try:
            print(f"🍽️ Getting menu for restaurant: {restaurant_slug}")
            
            # Query menus collection by restaurantId and language
            menus_query = self.firestore_db.collection('menus').where('restaurantId', '==', restaurant_slug).where('language', '==', 'tr').where('isActive', '==', True)
            menus = list(menus_query.stream())
            
            if menus:
                # Get the first active menu for this restaurant
                menu_doc = menus[0]
                menu_data = menu_doc.to_dict()
                print(f"✅ Retrieved real menu from Firestore for restaurant: {restaurant_slug}")
                print(f"📋 Menu ID: {menu_doc.id}")
                print(f"📋 Menu has {len(menu_data.get('categories', []))} categories")
                print(f"📋 Menu language: {menu_data.get('language', 'unknown')}")
                print(f"📋 Menu data: {menu_data}")
                # Return full menu data including name, description, and categories
                return {
                    'name': menu_data.get('name', ''),
                    'description': menu_data.get('description', ''),
                    'categories': menu_data.get('categories', [])
                }
            else:
                print(f"⚠️ No active menu found in Firestore for {restaurant_slug} with language 'tr'")
                print(f"🔍 Query: restaurantId={restaurant_slug}, language=tr, isActive=true")
                return []
            
        except Exception as e:
            print(f"❌ Error getting restaurant menu: {e}")
            return []
    
    def create_restaurant(self, restaurant_data):
        """Create new restaurant in Firestore"""
        if not self.firestore_db:
            return False
        
        try:
            # Generate unique slug
            slug = self._generate_restaurant_slug(restaurant_data.get('name', ''))
            
            # Process owner and editor
            owner_data = None
            editor_data = None
            
            if restaurant_data.get('owner') and restaurant_data['owner'].get('email'):
                owner_data = {
                    'name': restaurant_data['owner'].get('name', ''),
                    'email': restaurant_data['owner']['email'],
                    'phone': restaurant_data['owner'].get('phone', '')
                }
                print(f"✅ Owner data prepared: {owner_data['email']}")
            
            if restaurant_data.get('editor') and restaurant_data['editor'].get('email'):
                editor_user = self._find_user_by_email(restaurant_data['editor']['email'])
                if editor_user:
                    editor_data = {
                        'email': restaurant_data['editor']['email'],
                        'userId': editor_user['uid']
                    }
                    print(f"✅ Editor found: {editor_user['email']} (UID: {editor_user['uid']})")
                else:
                    print(f"⚠️ Editor email not found: {restaurant_data['editor']['email']}")
            
            # Prepare restaurant data
            restaurant_doc = {
                'name': restaurant_data.get('name'),
                'description': restaurant_data.get('description'),
                'cuisineTypes': restaurant_data.get('cuisineTypes', []),
                'tags': restaurant_data.get('tags', []),
                'phone': restaurant_data.get('phone'),
                'email': restaurant_data.get('email'),
                'website': restaurant_data.get('website'),
                'address': restaurant_data.get('address'),
                'hours': restaurant_data.get('hours', {}),
                'isActive': restaurant_data.get('isActive', True),
                'featured': restaurant_data.get('featured', False),
                'owner': owner_data,
                'editor': editor_data,
                'slug': slug,
                'createdAt': firestore.SERVER_TIMESTAMP,
                'updatedAt': firestore.SERVER_TIMESTAMP
            }
            
            # Create restaurant with slug as document ID
            self.firestore_db.collection('restaurants').document(slug).set(restaurant_doc)
            
            print(f"✅ Restaurant created successfully with slug: {slug}")
            return True
            
        except Exception as e:
            print(f"Failed to create restaurant: {e}")
            return False
    
    def _generate_restaurant_slug(self, name):
        """Generate unique slug for restaurant name"""
        if not name or not name.strip():
            print("⚠️ Restaurant name is empty, generating fallback slug")
            return f"restaurant-{int(time.time())}"
        
        # Convert to lowercase and replace spaces with hyphens
        slug = name.lower().strip()
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)  # Remove special characters
        slug = re.sub(r'\s+', '-', slug)  # Replace spaces with hyphens
        slug = re.sub(r'-+', '-', slug)  # Replace multiple hyphens with single
        slug = slug.strip('-')  # Remove leading/trailing hyphens
        
        # Ensure slug is not empty after processing
        if not slug:
            print("⚠️ Slug is empty after processing, generating fallback slug")
            slug = f"restaurant-{int(time.time())}"
        
        # Check if slug exists, if yes add timestamp
        if self._slug_exists(slug):
            new_slug = f"{slug}-{int(time.time())}"
            print(f"⚠️ Slug '{slug}' already exists, using '{new_slug}'")
            slug = new_slug
        
        print(f"✅ Generated slug: '{slug}' for restaurant: '{name}'")
        return slug
    
    def create_test_restaurant(self):
        """Create a test restaurant for development purposes"""
        if not self.firestore_db:
            print("❌ Firestore DB not available")
            return False
        
        try:
            test_data = {
                'name': 'Lezzet Durağı',
                'description': 'Geleneksel Türk mutfağının en seçkin lezzetlerini sunan premium restoran',
                'cuisineTypes': ['Türk Mutfağı'],
                'tags': ['geleneksel', 'premium', 'aile dostu'],
                'phone': '+90 216 555 0123',
                'email': 'info@lezzetduragi.com',
                'website': 'www.lezzetduragi.com',
                'address': 'Bağdat Caddesi No: 156, Kadıköy, İstanbul',
                'hours': {'open': '12:00', 'close': '23:00'},
                'isActive': True,
                'featured': True
            }
            
            result = self.create_restaurant(test_data)
            if result:
                print("✅ Test restaurant created successfully")
                
                # Also create menu data for this restaurant
                self.create_test_menu('lezzet-dura')
                
                return True
            else:
                print("❌ Failed to create test restaurant")
                return False
                
        except Exception as e:
            print(f"❌ Error creating test restaurant: {e}")
            return False
    
    def create_test_menu(self, restaurant_slug):
        """Create test menu data for a restaurant"""
        if not self.firestore_db:
            print("❌ Firestore DB not available")
            return False
        
        try:
            # Different menu for Doydos
            if restaurant_slug == 'doydos':
                menu_data = {
                    'name': 'Doydos Menü',
                    'description': 'Tost çeşitleri, burger çeşitleri, porsiyon patso, elma dilim patates, kumpir ve menemen seçenekleri.',
                    'restaurantId': restaurant_slug,
                    'language': 'tr',
                    'isActive': True,
                    'isAIGenerated': {
                        'description': True,
                        'name': True
                    },
                    'categories': [
                        {
                            'name': 'Çorbalar',
                            'items': [
                                {
                                    'name': 'Ezogelin Çorbası',
                                    'price': '₺28',
                                    'description': 'Geleneksel ezogelin çorbası, mercimek ve bulgur ile',
                                    'allergens': ['Gluten'],
                                    'spice_level': 'Mild'
                                },
                                {
                                    'name': 'Yayla Çorbası',
                                    'price': '₺26',
                                    'description': 'Yoğurtlu yayla çorbası, nane ve tereyağı ile',
                                    'allergens': ['Süt'],
                                    'spice_level': 'Mild'
                                }
                            ]
                        },
                        {
                            'name': 'Pideler',
                            'items': [
                                {
                                    'name': 'Karışık Pide',
                                    'price': '₺45',
                                    'description': 'Kaşar peyniri, yumurta ve sucuk ile karışık pide',
                                    'allergens': ['Gluten', 'Süt'],
                                    'spice_level': 'Mild'
                                },
                                {
                                    'name': 'Kuşbaşılı Pide',
                                    'price': '₺55',
                                    'description': 'Kuşbaşı et, soğan ve maydanoz ile özel pide',
                                    'allergens': ['Gluten'],
                                    'spice_level': 'Medium'
                                }
                            ]
                        },
                        {
                            'name': 'İçecekler',
                            'items': [
                                {
                                    'name': 'Ayran',
                                    'price': '₺8',
                                    'description': 'Taze ev yapımı ayran',
                                    'allergens': ['Süt'],
                                    'spice_level': 'Mild'
                                },
                                {
                                    'name': 'Şalgam Suyu',
                                    'price': '₺6',
                                    'description': 'Geleneksel şalgam suyu',
                                    'allergens': [],
                                    'spice_level': 'Mild'
                                }
                            ]
                        }
                    ],
                    'createdAt': firestore.SERVER_TIMESTAMP,
                    'updatedAt': firestore.SERVER_TIMESTAMP
                }
            else:
                # Default menu for other restaurants
                menu_data = {
                    'name': 'Lezzet Durağı Menü',
                    'description': 'Geleneksel Türk mutfağının en seçkin lezzetleri',
                    'restaurantId': restaurant_slug,
                    'language': 'tr',
                    'isActive': True,
                    'isAIGenerated': {
                        'description': True,
                        'name': True
                    },
                    'categories': [
                        {
                            'name': 'Başlangıçlar',
                            'items': [
                                {
                                    'name': 'Mercimek Çorbası',
                                    'price': '₺25',
                                    'description': 'Geleneksel Türk mutfağının vazgeçilmezi, sıcak mercimek çorbası',
                                    'allergens': ['Gluten'],
                                    'spice_level': 'Mild'
                                },
                                {
                                    'name': 'Humus',
                                    'price': '₺30',
                                    'description': 'Nohut püresi, tahin ve zeytinyağı ile hazırlanmış',
                                    'allergens': ['Sesam'],
                                    'spice_level': 'Mild'
                                }
                            ]
                        },
                        {
                            'name': 'Ana Yemekler',
                            'items': [
                                {
                                    'name': 'Izgara Köfte',
                                    'price': '₺85',
                                    'description': 'Özel baharatlarla hazırlanmış, ızgara edilmiş dana köfte',
                                    'allergens': [],
                                    'spice_level': 'Medium'
                                },
                                {
                                    'name': 'Tavuk Şiş',
                                    'price': '₺75',
                                    'description': 'Marine edilmiş tavuk eti, sebzelerle birlikte',
                                    'allergens': [],
                                    'spice_level': 'Mild'
                                }
                            ]
                        },
                        {
                            'name': 'Tatlılar',
                            'items': [
                                {
                                    'name': 'Künefe',
                                    'price': '₺45',
                                    'description': 'Geleneksel Türk tatlısı, peynirli künefe',
                                    'allergens': ['Gluten', 'Süt'],
                                    'spice_level': 'Sweet'
                                }
                            ]
                        }
                    ],
                    'createdAt': firestore.SERVER_TIMESTAMP,
                    'updatedAt': firestore.SERVER_TIMESTAMP
                }
            
            # Save menu to Firestore with auto-generated ID
            doc_ref = self.firestore_db.collection('menus').document()
            doc_ref.set(menu_data)
            print(f"✅ Test menu created successfully for restaurant: {restaurant_slug} with ID: {doc_ref.id}")
            return True
            
        except Exception as e:
            print(f"❌ Error creating test menu: {e}")
            return False
    
    def _slug_exists(self, slug):
        """Check if restaurant slug already exists"""
        if not self.firestore_db:
            return False
        
        try:
            doc = self.firestore_db.collection('restaurants').document(slug).get()
            return doc.exists
        except:
            return False
    
    def assign_restaurant_role(self, restaurant_slug, email, role):
        """Assign editor or owner role to restaurant"""
        if not self.firestore_db:
            return False
        
        try:
            # Find user by email
            user = self._find_user_by_email(email)
            if not user:
                print(f"User with email {email} not found")
                return False
            
            # Update restaurant with role assignment
            restaurant_ref = self.firestore_db.collection('restaurants').document(restaurant_slug)
            
            if role == 'editor':
                restaurant_ref.update({
                    'editors': firestore.ArrayUnion([user['uid']]),
                    'updated_at': firestore.SERVER_TIMESTAMP
                })
            elif role == 'owner':
                restaurant_ref.update({
                    'owner': user['uid'],
                    'updated_at': firestore.SERVER_TIMESTAMP
                })
            
            print(f"✅ {role} role assigned to {email} for restaurant {restaurant_slug}")
            return True
            
        except Exception as e:
            print(f"Failed to assign restaurant role: {e}")
            return False
    
    def _find_user_by_email(self, email):
        """Find user by email address"""
        if not self.auth:
            return None
        
        try:
            user = self.auth.get_user_by_email(email)
            return {
                'uid': user.uid,
                'email': user.email,
                'display_name': user.display_name
            }
        except:
            return None
    
    def find_user_by_email_in_firestore(self, email):
        """Find user by email in Firestore users collection"""
        if not self.firestore_db:
            return None
        
        try:
            # Query users collection by email
            users_ref = self.firestore_db.collection('users')
            query = users_ref.where('email', '==', email)
            docs = query.stream()
            
            for doc in docs:
                user_data = doc.to_dict()
                user_data['uid'] = doc.id
                print(f"✅ Found user in Firestore: {email} -> UID: {doc.id}, Role: {user_data.get('role', 'subscriber')}")
                return user_data
            
            print(f"❌ User not found in Firestore: {email}")
            return None
            
        except Exception as e:
            print(f"❌ Error finding user by email in Firestore: {e}")
            return None
    
    def update_restaurant(self, restaurant_slug, restaurant_data):
        """Update restaurant in Firestore"""
        if not self.firestore_db:
            return False
        
        try:
            restaurant_data['updated_at'] = firestore.SERVER_TIMESTAMP
            
            # Update restaurant using slug
            self.firestore_db.collection('restaurants').document(restaurant_slug).update(restaurant_data)
            print(f"✅ Restaurant updated successfully: {restaurant_slug}")
            return True
            
        except Exception as e:
            print(f"Failed to update restaurant: {e}")
            return False
    
    def delete_restaurant(self, restaurant_slug):
        """Delete restaurant from Firestore"""
        if not self.firestore_db:
            return False
        
        try:
            self.firestore_db.collection('restaurants').document(restaurant_slug).delete()
            print(f"✅ Restaurant deleted successfully: {restaurant_slug}")
            return True
            
        except Exception as e:
            print(f"Failed to delete restaurant: {e}")
            return False

    # Cuisine Management Methods
    def get_all_cuisines(self):
        """Get all cuisines from Firestore"""
        if not self.firestore_db:
            return []
        
        try:
            cuisines_ref = self.firestore_db.collection('cuisines')
            cuisines = []
            
            for doc in cuisines_ref.stream():
                cuisine_data = doc.to_dict()
                cuisine_data['id'] = doc.id
                
                # Get restaurant count for this cuisine
                restaurants_ref = self.firestore_db.collection('restaurants')
                restaurant_count = len(list(restaurants_ref.where('cuisineTypes', 'array_contains', cuisine_data['name']).stream()))
                cuisine_data['restaurantCount'] = restaurant_count
                
                cuisines.append(cuisine_data)
            
            print(f"✅ Retrieved {len(cuisines)} cuisines")
            return cuisines
            
        except Exception as e:
            print(f"❌ Error getting cuisines: {e}")
            return []

    def create_cuisine(self, cuisine_data):
        """Create a new cuisine in Firestore"""
        if not self.firestore_db:
            return None
        
        try:
            # Generate unique ID
            cuisine_id = self._generate_cuisine_id(cuisine_data['name'])
            
            cuisine_doc = {
                'name': cuisine_data.get('name'),
                'description': cuisine_data.get('description', ''),
                'isActive': cuisine_data.get('isActive', True),
                'createdAt': firestore.SERVER_TIMESTAMP,
                'updatedAt': firestore.SERVER_TIMESTAMP
            }
            
            doc_ref = self.firestore_db.collection('cuisines').document(cuisine_id)
            doc_ref.set(cuisine_doc)
            
            print(f"✅ Cuisine created: {cuisine_data['name']} (ID: {cuisine_id})")
            return cuisine_id
            
        except Exception as e:
            print(f"❌ Error creating cuisine: {e}")
            raise e

    def update_cuisine(self, cuisine_id, cuisine_data):
        """Update a cuisine in Firestore"""
        if not self.firestore_db:
            return False
        
        try:
            cuisine_doc = {
                'name': cuisine_data.get('name'),
                'description': cuisine_data.get('description', ''),
                'isActive': cuisine_data.get('isActive', True),
                'updatedAt': firestore.SERVER_TIMESTAMP
            }
            
            doc_ref = self.firestore_db.collection('cuisines').document(cuisine_id)
            doc_ref.update(cuisine_doc)
            
            print(f"✅ Cuisine updated: {cuisine_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error updating cuisine: {e}")
            return False

    def delete_cuisine(self, cuisine_id):
        """Delete a cuisine from Firestore"""
        if not self.firestore_db:
            return False
        
        try:
            doc_ref = self.firestore_db.collection('cuisines').document(cuisine_id)
            doc_ref.delete()
            
            print(f"✅ Cuisine deleted: {cuisine_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error deleting cuisine: {e}")
            return False

    def _generate_cuisine_id(self, name):
        """Generate a unique cuisine ID from name"""
        if not name:
            return f"cuisine_{int(time.time())}"
        
        # Convert to lowercase and replace spaces with hyphens
        base_id = name.lower().replace(' ', '-').replace('ı', 'i').replace('ğ', 'g').replace('ü', 'u').replace('ş', 's').replace('ö', 'o').replace('ç', 'c')
        
        # Remove special characters
        base_id = re.sub(r'[^a-z0-9-]', '', base_id)
        
        # Check if ID exists
        if not self._cuisine_id_exists(base_id):
            return base_id
        
        # Add timestamp if ID exists
        return f"{base_id}-{int(time.time())}"

    def _cuisine_id_exists(self, cuisine_id):
        """Check if a cuisine ID already exists"""
        if not self.firestore_db:
            return False
        
        try:
            doc_ref = self.firestore_db.collection('cuisines').document(cuisine_id)
            doc = doc_ref.get()
            return doc.exists
        except Exception as e:
            print(f"❌ Error checking cuisine ID existence: {e}")
            return False

    # Editor Management Methods
    def get_editor_stats(self, editor_id):
        """Get statistics for an editor"""
        if not self.firestore_db:
            return {}
        
        try:
            # Get restaurants assigned to this editor
            restaurants_ref = self.firestore_db.collection('restaurants')
            editor_restaurants = list(restaurants_ref.where('editor.userId', '==', editor_id).stream())
            
            total_restaurants = len(editor_restaurants)
            active_restaurants = len([r for r in editor_restaurants if r.to_dict().get('isActive', True)])
            
            # Get last update time
            last_update = None
            if editor_restaurants:
                last_update = max([r.to_dict().get('updatedAt') for r in editor_restaurants if r.to_dict().get('updatedAt')])
            
            stats = {
                'total_restaurants': total_restaurants,
                'active_restaurants': active_restaurants,
                'last_update': last_update
            }
            
            return stats
            
        except Exception as e:
            print(f"❌ Error getting editor stats: {e}")
            return {}

    def get_editor_restaurants(self, editor_id):
        """Get all restaurants assigned to an editor"""
        if not self.firestore_db:
            return []
        
        try:
            restaurants_ref = self.firestore_db.collection('restaurants')
            editor_restaurants = list(restaurants_ref.where('editor.userId', '==', editor_id).stream())
            
            restaurants = []
            for doc in editor_restaurants:
                restaurant_data = doc.to_dict()
                restaurant_data['id'] = doc.id
                restaurants.append(restaurant_data)
            
            print(f"✅ Retrieved {len(restaurants)} restaurants for editor {editor_id}")
            return restaurants
            
        except Exception as e:
            print(f"❌ Error getting editor restaurants: {e}")
            return []

    def get_editor_recent_restaurants(self, editor_id, limit=10):
        """Get recent restaurants assigned to an editor"""
        if not self.firestore_db:
            return []
        
        try:
            restaurants_ref = self.firestore_db.collection('restaurants')
            editor_restaurants = list(restaurants_ref.where('editor.userId', '==', editor_id).order_by('updatedAt', direction='DESCENDING').limit(limit).stream())
            
            restaurants = []
            for doc in editor_restaurants:
                restaurant_data = doc.to_dict()
                restaurant_data['id'] = doc.id
                restaurants.append(restaurant_data)
            
            print(f"✅ Retrieved {len(restaurants)} recent restaurants for editor {editor_id}")
            return restaurants
            
        except Exception as e:
            print(f"❌ Error getting editor recent restaurants: {e}")
            return []

    def can_editor_edit_restaurant(self, editor_id, restaurant_slug):
        """Check if an editor has permission to edit a restaurant"""
        if not self.firestore_db:
            return False
        
        try:
            doc_ref = self.firestore_db.collection('restaurants').document(restaurant_slug)
            doc = doc_ref.get()
            
            if not doc.exists:
                return False
            
            restaurant_data = doc.to_dict()
            editor_user_id = restaurant_data.get('editor', {}).get('userId')
            
            # Editor can edit if they are assigned to this restaurant
            can_edit = editor_user_id == editor_id
            
            print(f"🔐 Editor {editor_id} can edit restaurant {restaurant_slug}: {can_edit}")
            return can_edit
            
        except Exception as e:
            print(f"❌ Error checking editor permissions: {e}")
            return False

    # Menu Management Methods
    def get_editor_menus(self, editor_id):
        """Get all menus for restaurants assigned to an editor"""
        if not self.firestore_db:
            return []
        
        try:
            # First get restaurants assigned to this editor
            restaurants_ref = self.firestore_db.collection('restaurants')
            editor_restaurants = list(restaurants_ref.where('editor.userId', '==', editor_id).stream())
            
            restaurant_ids = [doc.id for doc in editor_restaurants]
            
            if not restaurant_ids:
                return []
            
            # Get menus for these restaurants
            menus_ref = self.firestore_db.collection('menus')
            menus = []
            
            for restaurant_id in restaurant_ids:
                restaurant_menus = list(menus_ref.where('restaurantId', '==', restaurant_id).stream())
                for doc in restaurant_menus:
                    menu_data = doc.to_dict()
                    menu_data['id'] = doc.id
                    # Add restaurant name for display
                    restaurant_doc = next((r for r in editor_restaurants if r.id == restaurant_id), None)
                    if restaurant_doc:
                        menu_data['restaurantName'] = restaurant_doc.to_dict().get('name', 'Unknown Restaurant')
                    menus.append(menu_data)
            
            print(f"✅ Retrieved {len(menus)} menus for editor {editor_id}")
            return menus
            
        except Exception as e:
            print(f"❌ Error getting editor menus: {e}")
            return []

    def create_menu(self, menu_data):
        """Create a new menu in Firestore"""
        if not self.firestore_db:
            return None
        
        try:
            menu_doc = {
                'name': menu_data.get('name'),
                'description': menu_data.get('description', ''),
                'restaurantId': menu_data.get('restaurantId'),
                'language': menu_data.get('language', 'tr'),
                'categories': menu_data.get('categories', []),
                'isActive': menu_data.get('isActive', True),
                'isAIGenerated': menu_data.get('isAIGenerated', {}),
                'createdAt': firestore.SERVER_TIMESTAMP,
                'updatedAt': firestore.SERVER_TIMESTAMP
            }
            
            doc_ref = self.firestore_db.collection('menus').document()
            doc_ref.set(menu_doc)
            
            print(f"✅ Menu created: {menu_data.get('name')} (ID: {doc_ref.id})")
            return doc_ref.id
            
        except Exception as e:
            print(f"❌ Error creating menu: {e}")
            raise e

    def update_menu(self, menu_id, menu_data):
        """Update a menu in Firestore"""
        if not self.firestore_db:
            return False
        
        try:
            menu_doc = {
                'name': menu_data.get('name'),
                'description': menu_data.get('description', ''),
                'restaurantId': menu_data.get('restaurantId'),
                'language': menu_data.get('language', 'tr'),
                'categories': menu_data.get('categories', []),
                'isActive': menu_data.get('isActive', True),
                'isAIGenerated': menu_data.get('isAIGenerated', {}),
                'updatedAt': firestore.SERVER_TIMESTAMP
            }
            
            doc_ref = self.firestore_db.collection('menus').document(menu_id)
            doc_ref.update(menu_doc)
            
            print(f"✅ Menu updated: {menu_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error updating menu: {e}")
            return False

    def delete_menu(self, menu_id):
        """Delete a menu from Firestore"""
        if not self.firestore_db:
            return False
        
        try:
            doc_ref = self.firestore_db.collection('menus').document(menu_id)
            doc_ref.delete()
            
            print(f"✅ Menu deleted: {menu_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error deleting menu: {e}")
            return False

    def can_editor_edit_menu(self, editor_id, menu_id):
        """Check if an editor has permission to edit a menu"""
        if not self.firestore_db:
            return False
        
        try:
            doc_ref = self.firestore_db.collection('menus').document(menu_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                return False
            
            menu_data = doc.to_dict()
            restaurant_id = menu_data.get('restaurantId')
            
            if not restaurant_id:
                return False
            
            # Check if editor can edit the restaurant this menu belongs to
            return self.can_editor_edit_restaurant(editor_id, restaurant_id)
            
        except Exception as e:
            print(f"❌ Error checking menu permissions: {e}")
            return False
    
    def create_user(self, email, password, display_name=None):
        """Create a new user account"""
        if not self.admin_app:
            return None
        
        try:
            user_properties = {
                'email': email,
                'password': password,
                'email_verified': False
            }
            
            if display_name:
                user_properties['display_name'] = display_name
            
            user = auth.create_user(**user_properties)
            
            # Create user document in Firestore users collection
            if self.firestore_db:
                try:
                    user_doc = {
                        'email': user.email,
                        'display_name': user.display_name,
                        'role': 'subscriber',  # Default role
                        'created_at': firestore.SERVER_TIMESTAMP,
                        'updated_at': firestore.SERVER_TIMESTAMP
                    }
                    self.firestore_db.collection('users').document(user.uid).set(user_doc)
                    print(f"✅ User document created in Firestore for {user.email}")
                except Exception as e:
                    print(f"⚠️ Failed to create user document in Firestore: {e}")
            
            return {
                'uid': user.uid,
                'email': user.email,
                'display_name': user.display_name
            }
        except Exception as e:
            print(f"Failed to create user: {e}")
            return None
    
    def update_user_profile(self, uid, display_name=None, photo_url=None):
        """Update user profile information"""
        if not self.admin_app:
            return False
        
        try:
            update_data = {}
            if display_name:
                update_data['display_name'] = display_name
            if photo_url:
                update_data['photo_url'] = photo_url
            
            if update_data:
                auth.update_user(uid, **update_data)
                return True
            return False
        except Exception as e:
            print(f"Failed to update user profile: {e}")
            return False
    
    def delete_user(self, uid):
        """Delete a user account"""
        if not self.admin_app:
            return False
        
        try:
            auth.delete_user(uid)
            return True
        except Exception as e:
            print(f"Failed to delete user: {e}")
            return False
    
    # Firestore Database Operations
    def save_chat_message(self, user_id, question, answer, timestamp=None):
        """Update daily message count in messages_limits collection (no chat history)"""
        if not self.firestore_db:
            return False
        
        try:
            # Get current date for daily tracking
            from datetime import datetime
            current_date = datetime.now().strftime('%Y-%m-%d')
            
            # Update user usage statistics (increment count by 1)
            self._update_user_usage(user_id, current_date)
            
            return True
        except Exception as e:
            print(f"Failed to update message count: {e}")
            return False
    
    def _update_user_usage(self, user_id, current_date):
        """Update user's daily usage statistics in messages_limits collection"""
        try:
            # Update daily usage in messages_limits collection
            limit_ref = self.firestore_db.collection('messages_limits').document(f"{user_id}_{current_date}")
            limit_ref.set({
                'user_id': user_id,
                'date': current_date,
                'count': firestore.Increment(1),
                'last_updated': firestore.SERVER_TIMESTAMP
            }, merge=True)
            
        except Exception as e:
            print(f"Failed to update user usage: {e}")
    
    # _cleanup_old_messages method removed - no chat history needed
    
    def get_user_chat_history(self, user_id, limit=10):
        """Get user's chat history - now returns empty list (no chat history stored)"""
        # Chat history is no longer stored, return empty list
        return []
    
    def save_user_preferences(self, user_id, preferences):
        """Save user preferences to Firestore"""
        if not self.firestore_db:
            return False
        
        try:
            user_ref = self.firestore_db.collection('user_preferences').document(user_id)
            user_ref.set(preferences, merge=True)
            return True
        except Exception as e:
            print(f"Failed to save user preferences: {e}")
            return False
    
    def get_user_preferences(self, user_id):
        """Get user preferences from Firestore"""
        if not self.firestore_db:
            return {}
        
        try:
            user_ref = self.firestore_db.collection('user_preferences').document(user_id)
            doc = user_ref.get()
            
            if doc.exists:
                return doc.to_dict()
            else:
                return {}
        except Exception as e:
            print(f"Failed to get user preferences: {e}")
            return {}
    
    def save_restaurant_review(self, user_id, review_data):
        """Save restaurant review to Firestore"""
        if not self.firestore_db:
            return False
        
        try:
            review_ref = self.firestore_db.collection('restaurant_reviews')
            review_ref.add({
                'user_id': user_id,
                'restaurant_id': 'lezzet-duragi',
                'rating': review_data.get('rating'),
                'comment': review_data.get('comment'),
                'timestamp': firestore.SERVER_TIMESTAMP,
                'user_name': review_data.get('user_name', 'Anonymous')
            })
            return True
        except Exception as e:
            print(f"Failed to save review: {e}")
            return False
    
    def get_restaurant_reviews(self, limit=20):
        """Get restaurant reviews from Firestore"""
        if not self.firestore_db:
            return []
        
        try:
            review_ref = self.firestore_db.collection('restaurant_reviews')
            query = review_ref.where('restaurant_id', '==', 'lezzet-duragi').order_by('timestamp', direction=firestore.Query.DESCENDING).limit(limit)
            docs = query.stream()
            
            reviews = []
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                reviews.append(data)
            
            return reviews
        except Exception as e:
            print(f"Failed to get reviews: {e}")
            return []
    
    def check_user_limits(self, user_id):
        """Check if user has exceeded daily message limit (10 messages per day)"""
        if not self.firestore_db:
            return {'can_send': False, 'reason': 'Database not available'}
        
        try:
            from datetime import datetime
            current_date = datetime.now().strftime('%Y-%m-%d')
            
            # Check daily limit (10 messages per day) from messages_limits collection
            limit_ref = self.firestore_db.collection('messages_limits').document(f"{user_id}_{current_date}")
            limit_doc = limit_ref.get()
            daily_messages = limit_doc.to_dict().get('count', 0) if limit_doc.exists else 0
            
            # Check limit
            daily_limit = 10
            
            if daily_messages >= daily_limit:
                return {
                    'can_send': False,
                    'reason': 'Günlük mesaj limitiniz doldu (10 mesaj)',
                    'daily_used': daily_messages,
                    'daily_limit': daily_limit
                }
            
            return {
                'can_send': True,
                'daily_used': daily_messages,
                'daily_limit': daily_limit
            }
            
        except Exception as e:
            print(f"Failed to check user limits: {e}")
            return {'can_send': False, 'reason': 'Limit kontrolü yapılamadı'}
    
    def get_user_usage_stats(self, user_id):
        """Get user's current daily usage statistics from messages_limits collection"""
        if not self.firestore_db:
            return {}
        
        try:
            from datetime import datetime
            current_date = datetime.now().strftime('%Y-%m-%d')
            
            # Get daily usage from messages_limits collection
            limit_ref = self.firestore_db.collection('messages_limits').document(f"{user_id}_{current_date}")
            limit_doc = limit_ref.get()
            daily_messages = limit_doc.to_dict().get('count', 0) if limit_doc.exists else 0
            
            return {
                'daily_used': daily_messages,
                'daily_limit': 10,
                'daily_remaining': 10 - daily_messages
            }
            
        except Exception as e:
            print(f"Failed to get user usage stats: {e}")
            return {}
    
    def verify_id_token(self, id_token):
        """Verify Firebase ID token"""
        try:
            if not self.auth:
                print("Firebase Auth not initialized")
                return None
            
            decoded_token = self.auth.verify_id_token(id_token)
            return decoded_token
            
        except Exception as e:
            print(f"Failed to verify ID token: {e}")
            return None
    
    def ensure_user_document_exists(self, uid, email, display_name=None):
        """Ensure user document exists in Firestore users collection"""
        if not self.firestore_db:
            print("❌ Firestore DB not available for user document creation")
            return False
        
        try:
            # Check if user document already exists
            user_doc = self.firestore_db.collection('users').document(uid).get()
            
            if not user_doc.exists:
                # Create user document
                user_data = {
                    'email': email,
                    'display_name': display_name or '',
                    'role': 'subscriber',  # Default role
                    'created_at': firestore.SERVER_TIMESTAMP,
                    'updated_at': firestore.SERVER_TIMESTAMP
                }
                self.firestore_db.collection('users').document(uid).set(user_data)
                print(f"✅ User document created in Firestore for {email}")
                return True
            else:
                print(f"✅ User document already exists in Firestore for {email}")
                return True
                
        except Exception as e:
            print(f"❌ Failed to ensure user document exists: {e}")
            return False
    
    def get_status(self):
        """Get Firebase service status"""
        return {
            'available': self.is_available,
            'admin_sdk': bool(self.admin_app),
            'firestore': bool(self.firestore_db),
            'config_complete': bool(self.is_available)
        }

# Global Firebase service instance
firebase_service = FirebaseService()
