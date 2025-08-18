from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import os
import json
from config import Config
from gemini_service import GeminiAIService
from firebase_config import firebase_service
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = Config.SECRET_KEY

# Make Firebase config available to all templates
@app.context_processor
def inject_firebase_config():
    return {
        'config': {
            'FIREBASE_API_KEY': Config.FIREBASE_API_KEY,
            'FIREBASE_AUTH_DOMAIN': Config.FIREBASE_AUTH_DOMAIN,
            'FIREBASE_PROJECT_ID': Config.FIREBASE_PROJECT_ID,
            'FIREBASE_STORAGE_BUCKET': Config.FIREBASE_STORAGE_BUCKET,
            'FIREBASE_MESSAGING_SENDER_ID': Config.FIREBASE_MESSAGING_SENDER_ID,
            'FIREBASE_APP_ID': Config.FIREBASE_APP_ID
        }
    }

# Initialize Gemini AI service
gemini_service = GeminiAIService()

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function



@app.route('/')
def index():
    return render_template('pages/home.html')

@app.route('/api/health')
def health_check():
    return jsonify({'status': 'healthy', 'message': 'Flask app is running!'})

@app.route('/api/featured-restaurants')
def get_featured_restaurants():
    """Get featured restaurants for homepage"""
    try:
        featured_restaurants = firebase_service.get_featured_restaurants()
        return jsonify({
            'restaurants': featured_restaurants,
            'count': len(featured_restaurants)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/restaurants/<restaurant_slug>/menu')
def get_restaurant_menu(restaurant_slug):
    """Get restaurant menu by slug"""
    try:
        print(f"🍽️ Menu request for restaurant: {restaurant_slug}")
        menu_data = firebase_service.get_restaurant_menu(restaurant_slug)
        
        if menu_data and isinstance(menu_data, dict):
            categories_count = len(menu_data.get('categories', []))
            print(f"📋 Menu data retrieved: {categories_count} categories")
            print(f"📋 Menu name: {menu_data.get('name', 'Unknown')}")
            print(f"📋 Menu description: {menu_data.get('description', 'No description')}")
        else:
            print(f"📋 Menu data retrieved: 0 categories")
        
        response_data = {
            'restaurant_slug': restaurant_slug,
            'menu': menu_data
        }
        print(f"📤 Sending menu response: {response_data}")
        return jsonify(response_data)
    except Exception as e:
        print(f"❌ Error getting restaurant menu: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat', methods=['POST'])
@login_required
def chat_with_ai():
    """Chat with AI garson"""
    try:
        data = request.get_json()
        if not data or 'question' not in data:
            return jsonify({'error': 'Question required'}), 400
        
        question = data['question']
        if len(question) > 150:
            return jsonify({'error': 'Question too long'}), 400
        
        # Get restaurant context from session or request
        restaurant_slug = session.get('current_restaurant_slug')
        if not restaurant_slug:
            return jsonify({'error': 'Restaurant context not found'}), 400
        
        # Get restaurant data for context
        restaurant = firebase_service.get_restaurant_by_slug(restaurant_slug)
        if not restaurant:
            return jsonify({'error': 'Restaurant not found'}), 400
        
        # Get additional context from frontend
        frontend_context = data.get('context', '')
        restaurant_info = data.get('restaurant_info', '')
        
        # Create enhanced context for AI
        context = f"""
        Sen bu restoranın garsonusun ve müşterilerin sorularına cevap veriyorsun.
        Cevapların 2-3 cümleyi geçmemeli ve Türkçe olmalı.
        
        Restoran Bilgileri:
        - İsim: {restaurant.get('name', 'Bilinmiyor')}
        - Açıklama: {restaurant.get('description', 'Bilinmiyor')}
        - Mutfak Türü: {', '.join(restaurant.get('cuisineTypes', []))}
        - Etiketler: {', '.join(restaurant.get('tags', []))}
        - Telefon: {restaurant.get('phone', 'Bilinmiyor')}
        - Email: {restaurant.get('email', 'Bilinmiyor')}
        - Website: {restaurant.get('website', 'Bilinmiyor')}
        - Adres: {restaurant.get('address', 'Bilinmiyor')}
        - Çalışma Saatleri: {restaurant.get('hours', {}).get('open', 'Bilinmiyor')} - {restaurant.get('hours', {}).get('close', 'Bilinmiyor')}
        
        {frontend_context}
        
        {restaurant_info}
        
        Müşteri Sorusu: {question}
        
        Lütfen menü içeriğini ve restoran bilgilerini kullanarak detaylı ve yardımcı cevaplar ver.
        """
        
        # Use Gemini AI service to get response
        if firebase_service.gemini_service and firebase_service.gemini_service.is_available:
            try:
                response = firebase_service.gemini_service.get_response(context)
                
                # Save chat message to Firestore
                print(f"💾 Saving chat message for user {session.get('user_id')}")
                save_result = firebase_service.save_chat_message(session.get('user_id'), question, response)
                print(f"💾 Save result: {save_result}")
                
                # Get updated usage stats
                print(f"📊 Getting updated usage stats for user {session.get('user_id')}")
                usage_stats = firebase_service.get_user_usage_stats(session.get('user_id'))
                print(f"📊 Updated usage stats: {usage_stats}")
                
                return jsonify({
                    'answer': response,
                    'restaurant_slug': restaurant_slug,
                    'usage_stats': usage_stats
                })
            except Exception as ai_error:
                print(f"AI service error: {ai_error}")
                # Fallback response
                return jsonify({
                    'answer': 'Üzgünüm, şu anda AI servisimiz meşgul. Lütfen daha sonra tekrar deneyin.',
                    'restaurant_slug': restaurant_slug
                })
        else:
            # AI service not available
            return jsonify({
                'answer': 'Üzgünüm, AI servisimiz şu anda kullanılamıyor. Lütfen daha sonra tekrar deneyin.',
                'restaurant_slug': restaurant_slug
            })
            
    except Exception as e:
        print(f"Chat API error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/menu/<restaurant_slug>')
def restaurant_menu(restaurant_slug):
    """Display restaurant menu page"""
    try:
        # Get restaurant data by slug
        restaurant = firebase_service.get_restaurant_by_slug(restaurant_slug)
        if not restaurant:
            return "Restoran bulunamadı", 404
        
        # Store restaurant slug in session for AI chat context
        session['current_restaurant_slug'] = restaurant_slug
        
        return render_template('pages/menu.html', restaurant=restaurant)
    except Exception as e:
        print(f"Error loading restaurant menu: {e}")
        return "Restoran verileri yüklenemedi", 500



@app.route('/login')
def login_page():
    """Login page"""
    return render_template('pages/login.html')

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    """API endpoint for login"""
    try:
        data = request.get_json()
        if not data or 'id_token' not in data:
            return jsonify({'error': 'ID token required'}), 400
        
        # Verify the ID token with Firebase
        decoded_token = firebase_service.verify_id_token(data['id_token'])
        print(f"🔐 Decoded token: {decoded_token}")
        
        if decoded_token:
            # Store user info in session
            session['user_id'] = decoded_token['uid']
            session['user_email'] = decoded_token.get('email', '')
            session['user_display_name'] = decoded_token.get('name', '')
            session['user_photo_url'] = decoded_token.get('picture', '')
            
            print(f"💾 Session stored - User ID: {session['user_id']}")
            print(f"💾 Session stored - Email: {session['user_email']}")
            print(f"💾 Session stored - Display Name: {session['user_display_name']}")
            print(f"💾 Session stored - Photo URL: {session['user_photo_url']}")
            
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'user': {
                    'uid': decoded_token['uid'],
                    'email': decoded_token.get('email', ''),
                    'display_name': decoded_token.get('name', ''),
                    'photo_url': decoded_token.get('picture', '')
                }
            })
        else:
            print("❌ Token verification failed")
            return jsonify({'error': 'Invalid token'}), 401
            
    except Exception as e:
        return jsonify({'error': f'Login failed: {str(e)}'}), 500

@app.route('/register')
def register_page():
    """Registration page"""
    return render_template('pages/register.html')

@app.route('/api/auth/register', methods=['POST'])
def api_register():
    """API endpoint for registration"""
    try:
        data = request.get_json()
        if not data or 'id_token' not in data:
            return jsonify({'error': 'ID token required'}), 400
        
        # Verify the ID token with Firebase
        decoded_token = firebase_service.verify_id_token(data['id_token'])
        if decoded_token:
            # Store user info in session
            session['user_id'] = decoded_token['uid']
            session['user_email'] = decoded_token.get('email', '')
            session['user_display_name'] = decoded_token.get('name', '')
            session['user_photo_url'] = decoded_token.get('picture', '')
            
            return jsonify({
                'success': True,
                'message': 'Registration successful',
                'user': {
                    'uid': decoded_token['uid'],
                    'email': decoded_token.get('email', ''),
                    'display_name': decoded_token.get('name', ''),
                    'photo_url': decoded_token.get('picture', '')
                }
            })
        else:
            return jsonify({'error': 'Invalid token'}), 401
            
    except Exception as e:
        return jsonify({'error': f'Registration failed: {str(e)}'}), 500

@app.route('/profile')
@login_required
def profile_page():
    """User profile page (requires authentication)"""
    user_id = session.get('user_id')
    user_info = firebase_service.get_user_by_uid(user_id)
    return render_template('pages/profile.html', user=user_info)

@app.route('/admin')
@login_required
def admin_panel():
    """Admin panel page"""
    user_id = session.get('user_id')
    user_info = firebase_service.get_user_by_uid(user_id)
    
    if not user_info or user_info.get('role') != 'admin':
        return redirect(url_for('home'))
    
    return render_template('admin/dashboard.html', user=user_info)

@app.route('/admin/users')
@login_required
def admin_users():
    """Admin users management page"""
    user_id = session.get('user_id')
    user_info = firebase_service.get_user_by_uid(user_id)
    
    if not user_info or user_info.get('role') != 'admin':
        return redirect(url_for('home'))
    
    return render_template('admin/users.html', user=user_info)

@app.route('/admin/restaurants')
@login_required
def admin_restaurants():
    """Admin restaurants management page"""
    user_id = session.get('user_id')
    user_info = firebase_service.get_user_by_uid(user_id)
    
    if not user_info or user_info.get('role') != 'admin':
        return redirect(url_for('home'))
    
    return render_template('admin/restaurants.html', user=user_info)

@app.route('/admin/cuisines')
@login_required
def admin_cuisines():
    """Admin cuisines management page"""
    user_id = session.get('user_id')
    user_info = firebase_service.get_user_by_uid(user_id)
    
    if not user_info or user_info.get('role') != 'admin':
        return redirect(url_for('home'))
    
    return render_template('admin/cuisines.html', user=user_info)

# Editor Panel Routes
@app.route('/editor')
@login_required
def editor_dashboard():
    """Editor dashboard page"""
    user_id = session.get('user_id')
    user_info = firebase_service.get_user_by_uid(user_id)
    
    if not user_info or user_info.get('role') not in ['editor', 'admin']:
        return redirect(url_for('home'))
    
    return render_template('editor/dashboard.html', user=user_info)

@app.route('/editor/restaurants')
@login_required
def editor_restaurants():
    """Editor restaurants management page"""
    user_id = session.get('user_id')
    user_info = firebase_service.get_user_by_uid(user_id)
    
    if not user_info or user_info.get('role') not in ['editor', 'admin']:
        return redirect(url_for('home'))
    
    return render_template('editor/restaurants.html', user=user_info)

@app.route('/editor/profile')
@login_required
def editor_profile():
    """Editor profile page"""
    user_id = session.get('user_id')
    user_info = firebase_service.get_user_by_uid(user_id)
    
    if not user_info or user_info.get('role') not in ['editor', 'admin']:
        return redirect(url_for('home'))
    
    return render_template('editor/profile.html', user=user_info)

@app.route('/editor/menus')
@login_required
def editor_menus():
    """Editor menus management page"""
    user_id = session.get('user_id')
    user_info = firebase_service.get_user_by_uid(user_id)
    
    if not user_info or user_info.get('role') not in ['editor', 'admin']:
        return redirect(url_for('home'))
    
    return render_template('editor/menus.html', user=user_info)

@app.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    return redirect(url_for('index'))

@app.route('/api/chat', methods=['POST'])
@login_required
def chat():
    """AI chat endpoint for restaurant questions (requires authentication)"""
    try:
        data = request.get_json()
        if not data or 'question' not in data:
            return jsonify({'error': 'Soru gerekli'}), 400
        
        question = data['question']
        user_id = session.get('user_id')
        
        # Check character limits
        if len(question) > 150:  # 150 karakter limiti
            return jsonify({
                'error': 'Soru çok uzun. Maksimum 150 karakter kullanabilirsiniz.',
                'success': False
            }), 400
        
        # Get restaurant slug from session
        restaurant_slug = session.get('current_restaurant_slug')
        if not restaurant_slug:
            return jsonify({'error': 'Restoran bilgisi bulunamadı'}), 400
        
        # Check user limits BEFORE processing
        limits = firebase_service.check_user_limits(user_id)
        print(f"🔍 User limits check: {limits}")
        
        if not limits['can_send']:
            print(f"❌ User {user_id} exceeded limits: {limits['reason']}")
            return jsonify({
                'error': limits['reason'],
                'limits': limits,
                'success': False
            }), 429  # Too Many Requests
        
        # Get restaurant data
        restaurant = firebase_service.get_restaurant_by_slug(restaurant_slug)
        if not restaurant:
            return jsonify({'error': 'Restoran bulunamadı'}), 500
        
        # Get chat history for context
        chat_history = firebase_service.get_user_chat_history(user_id, limit=10)
        
        # Get current usage stats
        current_usage_stats = firebase_service.get_user_usage_stats(user_id, restaurant_slug)
        
        # Get AI response with context
        response = gemini_service.ask_question(question, restaurant, chat_history, current_usage_stats)
        
        if response['success']:
            print(f"💾 Saving chat message for user {user_id}")
            # Save chat message to Firestore
            save_result = firebase_service.save_chat_message(user_id, question, response['answer'])
            print(f"💾 Save result: {save_result}")
            
            # Get updated usage stats
            print(f"📊 Getting updated usage stats for user {user_id}")
            usage_stats = firebase_service.get_user_usage_stats(user_id)
            print(f"📊 Updated usage stats: {usage_stats}")
            
            return jsonify({
                'answer': response['answer'],
                'success': True,
                'usage_stats': usage_stats
            })
        else:
            return jsonify({
                'error': response['error'],
                'success': False
            }), 500
            
    except Exception as e:
        return jsonify({'error': f'Sistem hatası: {str(e)}'}), 500

@app.route('/api/ai-status')
def ai_status():
    """Get AI service status"""
    return jsonify(gemini_service.get_status())

@app.route('/api/auth/verify', methods=['POST'])
def verify_token():
    """Verify Firebase ID token and create session"""
    try:
        data = request.get_json()
        if not data or 'idToken' not in data:
            return jsonify({'error': 'ID token required'}), 400
        
        id_token = data['idToken']
        decoded_token = firebase_service.verify_token(id_token)
        
        if decoded_token:
            # Store user info in session
            session['user_id'] = decoded_token['uid']
            session['user_email'] = decoded_token.get('email', '')
            session['user_name'] = decoded_token.get('name', '')
            
            # Get additional user info from Firebase Admin
            user_info = firebase_service.get_user_by_uid(decoded_token['uid'])
            if user_info:
                session['user_display_name'] = user_info.get('display_name', '')
            
            return jsonify({
                'success': True,
                'user': {
                    'uid': decoded_token['uid'],
                    'email': decoded_token.get('email', ''),
                    'name': decoded_token.get('name', ''),
                    'display_name': user_info.get('display_name', '') if user_info else ''
                }
            })
        else:
            return jsonify({'error': 'Invalid token'}), 401
            
    except Exception as e:
        return jsonify({'error': f'Authentication error: {str(e)}'}), 500

@app.route('/api/auth/status')
def auth_status():
    """Get current authentication status"""
    print(f"🔍 Auth status check - Session keys: {list(session.keys())}")
    
    if 'user_id' in session:
        user_id = session['user_id']
        print(f"✅ User ID in session: {user_id}")
        
        # Get user info from Firebase
        user_info = firebase_service.get_user_by_uid(user_id)
        print(f"📱 Firebase user info: {user_info}")
        
        if user_info:
            response_data = {
                'authenticated': True,
                'user_id': user_id,
                'user': {
                    'uid': user_id,
                    'email': user_info.get('email', ''),
                    'display_name': user_info.get('display_name', ''),
                    'photo_url': user_info.get('photo_url', '')
                }
            }
            print(f"🎯 Returning Firebase user data: {response_data}")
            return jsonify(response_data)
        else:
            # Fallback to session data
            response_data = {
                'authenticated': True,
                'user_id': user_id,
                'user': {
                    'uid': user_id,
                    'email': session.get('user_email', ''),
                    'display_name': session.get('user_display_name', ''),
                    'photo_url': session.get('user_photo_url', '')
                }
            }
            print(f"🔄 Returning session user data: {response_data}")
            return jsonify(response_data)
    else:
        print("❌ No user_id in session")
        return jsonify({
            'authenticated': False,
            'user': None
        })

@app.route('/api/firebase-status')
def firebase_status():
    """Get Firebase service status"""
    return jsonify(firebase_service.get_status())

@app.route('/api/chat/history')
@login_required
def get_chat_history():
    """Get user's chat history from Firestore"""
    user_id = session.get('user_id')
    limit = request.args.get('limit', 10, type=int)
    
    chat_history = firebase_service.get_user_chat_history(user_id, limit)
    return jsonify({
        'success': True,
        'chat_history': chat_history
    })

@app.route('/api/user/preferences', methods=['GET', 'POST'])
@login_required
def user_preferences():
    """Get or update user preferences"""
    user_id = session.get('user_id')
    
    if request.method == 'GET':
        preferences = firebase_service.get_user_preferences(user_id)
        return jsonify({
            'success': True,
            'preferences': preferences
        })
    
    elif request.method == 'POST':
        try:
            preferences = request.get_json()
            if firebase_service.save_user_preferences(user_id, preferences):
                return jsonify({
                    'success': True,
                    'message': 'Preferences saved successfully'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Failed to save preferences'
                }), 500
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Error saving preferences: {str(e)}'
            }), 500

@app.route('/api/reviews', methods=['GET', 'POST'])
def reviews():
    """Get or post restaurant reviews"""
    if request.method == 'GET':
        limit = request.args.get('limit', 20, type=int)
        reviews = firebase_service.get_restaurant_reviews(limit)
        return jsonify({
            'success': True,
            'reviews': reviews
        })

# Admin API Endpoints
@app.route('/api/admin/users')
@login_required
def admin_get_users():
    """Get all users for admin panel"""
    user_id = session.get('user_id')
    user_info = firebase_service.get_user_by_uid(user_id)
    
    if not user_info or user_info.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        users = firebase_service.get_all_users()
        return jsonify(users)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/users/lookup', methods=['POST'])
@login_required
def admin_lookup_user():
    """Look up user by email for auto-filling forms"""
    user_id = session.get('user_id')
    user_info = firebase_service.get_user_by_uid(user_id)
    
    if not user_info or user_info.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({'error': 'Email is required'}), 400
        
        # Find user by email
        user = firebase_service._find_user_by_email(email)
        if user:
            return jsonify({'user': user})
        else:
            return jsonify({'user': None})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/users/<uid>/role', methods=['PUT'])
@login_required
def admin_update_user_role(uid):
    """Update user role"""
    user_id = session.get('user_id')
    user_info = firebase_service.get_user_by_uid(user_id)
    
    if not user_info or user_info.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        new_role = data.get('role')
        
        if not new_role or new_role not in ['admin', 'editor', 'owner', 'subscriber']:
            return jsonify({'error': 'Invalid role'}), 400
        
        success = firebase_service.set_user_role(uid, new_role)
        if success:
            return jsonify({'message': 'User role updated successfully'})
        else:
            return jsonify({'error': 'Failed to update user role'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/restaurants')
@login_required
def admin_get_restaurants():
    """Get all restaurants for admin panel"""
    user_id = session.get('user_id')
    user_info = firebase_service.get_user_by_uid(user_id)
    
    if not user_info or user_info.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        restaurants = firebase_service.get_all_restaurants()
        return jsonify(restaurants)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/restaurants', methods=['POST'])
@login_required
def admin_create_restaurant():
    """Create new restaurant"""
    user_id = session.get('user_id')
    user_info = firebase_service.get_user_by_uid(user_id)
    
    if not user_info or user_info.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('name'):
            return jsonify({'error': 'Restaurant name is required'}), 400
        
        # Create restaurant
        success = firebase_service.create_restaurant(data)
        if success:
            return jsonify({'message': 'Restaurant created successfully'})
        else:
            return jsonify({'error': 'Failed to create restaurant'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/restaurants/<restaurant_slug>/assign-role', methods=['POST'])
@login_required
def admin_assign_restaurant_role(restaurant_slug):
    """Assign editor or owner role to restaurant"""
    user_id = session.get('user_id')
    user_info = firebase_service.get_user_by_uid(user_id)
    
    if not user_info or user_info.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        email = data.get('email')
        role = data.get('role')
        
        if not email or not role:
            return jsonify({'error': 'Email and role are required'}), 400
        
        if role not in ['editor', 'owner']:
            return jsonify({'error': 'Invalid role. Must be editor or owner'}), 400
        
        success = firebase_service.assign_restaurant_role(restaurant_slug, email, role)
        if success:
            return jsonify({'message': f'{role.title()} role assigned successfully'})
        else:
            return jsonify({'error': f'Failed to assign {role} role'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/restaurants/<restaurant_slug>', methods=['PUT'])
@login_required
def admin_update_restaurant(restaurant_slug):
    """Update restaurant"""
    user_id = session.get('user_id')
    user_info = firebase_service.get_user_by_uid(user_id)
    
    if not user_info or user_info.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        success = firebase_service.update_restaurant(restaurant_slug, data)
        if success:
            return jsonify({'message': 'Restaurant updated successfully'})
        else:
            return jsonify({'error': 'Failed to update restaurant'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/restaurants/<restaurant_slug>', methods=['DELETE'])
@login_required
def admin_delete_restaurant(restaurant_slug):
    """Delete restaurant"""
    user_id = session.get('user_id')
    user_info = firebase_service.get_user_by_uid(user_id)
    
    if not user_info or user_info.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 500
    
    try:
        success = firebase_service.delete_restaurant(restaurant_slug)
        if success:
            return jsonify({'message': 'Restaurant deleted successfully'})
        else:
            return jsonify({'error': 'Failed to delete restaurant'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Cuisine Management API Endpoints
@app.route('/api/admin/cuisines', methods=['GET'])
@login_required
def admin_get_cuisines():
    """Get all cuisines"""
    user_id = session.get('user_id')
    user_info = firebase_service.get_user_by_uid(user_id)
    
    if not user_info or user_info.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        cuisines = firebase_service.get_all_cuisines()
        return jsonify({'cuisines': cuisines})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/cuisines', methods=['POST'])
@login_required
def admin_create_cuisine():
    """Create a new cuisine"""
    user_id = session.get('user_id')
    user_info = firebase_service.get_user_by_uid(user_id)
    
    if not user_info or user_info.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        cuisine_id = firebase_service.create_cuisine(data)
        return jsonify({'message': 'Cuisine created successfully', 'id': cuisine_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/cuisines/<cuisine_id>', methods=['PUT'])
@login_required
def admin_update_cuisine(cuisine_id):
    """Update a cuisine"""
    user_id = session.get('user_id')
    user_info = firebase_service.get_user_by_uid(user_id)
    
    if not user_info or user_info.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        success = firebase_service.update_cuisine(cuisine_id, data)
        if success:
            return jsonify({'message': 'Cuisine updated successfully'})
        else:
            return jsonify({'error': 'Failed to update cuisine'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/cuisines/<cuisine_id>', methods=['DELETE'])
@login_required
def admin_delete_cuisine(cuisine_id):
    """Delete a cuisine"""
    user_id = session.get('user_id')
    user_info = firebase_service.get_user_by_uid(user_id)
    
    if not user_info or user_info.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        success = firebase_service.delete_cuisine(cuisine_id)
        if success:
            return jsonify({'message': 'Cuisine deleted successfully'})
        else:
            return jsonify({'error': 'Failed to delete cuisine'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Public Cuisines Endpoint (for editors and other users)
@app.route('/api/cuisines', methods=['GET'])
@login_required
def get_cuisines():
    """Get all active cuisines (for editors and other users)"""
    try:
        cuisines = firebase_service.get_all_cuisines()
        # Filter only active cuisines for non-admin users
        active_cuisines = [cuisine for cuisine in cuisines if cuisine.get('isActive', True)]
        return jsonify({'cuisines': active_cuisines})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Editor API Endpoints
@app.route('/api/editor/stats')
@login_required
def editor_get_stats():
    """Get editor statistics"""
    user_id = session.get('user_id')
    user_info = firebase_service.get_user_by_uid(user_id)
    
    if not user_info or user_info.get('role') not in ['editor', 'admin']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        stats = firebase_service.get_editor_stats(user_id)
        return jsonify({'stats': stats})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/editor/restaurants')
@login_required
def editor_get_restaurants():
    """Get restaurants assigned to editor"""
    user_id = session.get('user_id')
    user_info = firebase_service.get_user_by_uid(user_id)
    
    if not user_info or user_info.get('role') not in ['editor', 'admin']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        restaurants = firebase_service.get_editor_restaurants(user_id)
        return jsonify({'restaurants': restaurants})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/editor/restaurants/recent')
@login_required
def editor_get_recent_restaurants():
    """Get recent restaurants assigned to editor"""
    user_id = session.get('user_id')
    user_info = firebase_service.get_user_by_uid(user_id)
    
    if not user_info or user_info.get('role') not in ['editor', 'admin']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        restaurants = firebase_service.get_editor_recent_restaurants(user_id)
        return jsonify({'restaurants': restaurants})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/editor/restaurants', methods=['POST'])
@login_required
def editor_create_restaurant():
    """Create a new restaurant as editor"""
    user_id = session.get('user_id')
    user_info = firebase_service.get_user_by_uid(user_id)
    
    if not user_info or user_info.get('role') not in ['editor', 'admin']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        # Add editor information to restaurant data
        data['editor'] = {
            'userId': user_id,
            'email': user_info.get('email'),
            'name': user_info.get('displayName', '')
        }
        
        restaurant_id = firebase_service.create_restaurant(data)
        return jsonify({'message': 'Restaurant created successfully', 'id': restaurant_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/editor/restaurants/<restaurant_slug>', methods=['PUT'])
@login_required
def editor_update_restaurant(restaurant_slug):
    """Update restaurant as editor"""
    user_id = session.get('user_id')
    user_info = firebase_service.get_user_by_uid(user_id)
    
    if not user_info or user_info.get('role') not in ['editor', 'admin']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        # Check if editor has permission to edit this restaurant
        if not firebase_service.can_editor_edit_restaurant(user_id, restaurant_slug):
            return jsonify({'error': 'Unauthorized to edit this restaurant'}), 403
        
        data = request.get_json()
        success = firebase_service.update_restaurant(restaurant_slug, data)
        if success:
            return jsonify({'message': 'Restaurant updated successfully'})
        else:
            return jsonify({'error': 'Failed to update restaurant'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/editor/restaurants/<restaurant_slug>', methods=['DELETE'])
@login_required
def editor_delete_restaurant(restaurant_slug):
    """Delete restaurant as editor"""
    user_id = session.get('user_id')
    user_info = firebase_service.get_user_by_uid(user_id)
    
    if not user_info or user_info.get('role') not in ['editor', 'admin']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        # Check if editor has permission to delete this restaurant
        if not firebase_service.can_editor_edit_restaurant(user_id, restaurant_slug):
            return jsonify({'error': 'Unauthorized to delete this restaurant'}), 403
        
        success = firebase_service.delete_restaurant(restaurant_slug)
        if success:
            return jsonify({'message': 'Restaurant deleted successfully'})
        else:
            return jsonify({'error': 'Failed to delete restaurant'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# AI Image Analysis API Endpoint
@app.route('/api/ai/analyze-menu-image', methods=['POST'])
@login_required
def analyze_menu_image():
    """Analyze menu image using Gemini AI"""
    try:
        data = request.get_json()
        image_base64 = data.get('image')
        language = data.get('language', 'tr')
        
        print(f"🔍 AI analysis request received: language={language}, image_size={len(image_base64) if image_base64 else 0}")
        
        if not image_base64:
            return jsonify({'error': 'Image data is required'}), 400
        
        # Analyze image with Gemini AI
        suggestions = gemini_service.analyze_menu_image(image_base64, language)
        
        print(f"🔍 AI analysis result: {suggestions}")
        
        return jsonify(suggestions)
        
    except Exception as e:
        print(f"❌ Error analyzing menu image: {e}")
        return jsonify({'error': str(e)}), 500

# Test AI endpoint
@app.route('/api/ai/test', methods=['GET'])
def test_ai():
    """Test if AI service is working"""
    try:
        status = gemini_service.get_status()
        basic_test = gemini_service.test_basic_functionality()
        
        return jsonify({
            'success': True,
            'ai_status': status,
            'basic_test': basic_test,
            'message': 'AI service is working'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Editor Menu API Endpoints
@app.route('/api/editor/menus')
@login_required
def editor_get_menus():
    """Get menus for restaurants assigned to editor"""
    user_id = session.get('user_id')
    user_info = firebase_service.get_user_by_uid(user_id)
    
    if not user_info or user_info.get('role') not in ['editor', 'admin']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        menus = firebase_service.get_editor_menus(user_id)
        return jsonify({'menus': menus})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/editor/menus', methods=['POST'])
@login_required
def editor_create_menu():
    """Create a new menu as editor"""
    user_id = session.get('user_id')
    user_info = firebase_service.get_user_by_uid(user_id)
    
    if not user_info or user_info.get('role') not in ['editor', 'admin']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        # Check if editor has permission to create menu for this restaurant
        if not firebase_service.can_editor_edit_restaurant(user_id, data.get('restaurantId')):
            return jsonify({'error': 'Unauthorized to create menu for this restaurant'}), 403
        
        menu_id = firebase_service.create_menu(data)
        return jsonify({'message': 'Menu created successfully', 'id': menu_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/editor/menus/<menu_id>', methods=['PUT'])
@login_required
def editor_update_menu(menu_id):
    """Update menu as editor"""
    user_id = session.get('user_id')
    user_info = firebase_service.get_user_by_uid(user_id)
    
    if not user_info or user_info.get('role') not in ['editor', 'admin']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        # Check if editor has permission to edit this menu
        if not firebase_service.can_editor_edit_menu(user_id, menu_id):
            return jsonify({'error': 'Unauthorized to edit this menu'}), 403
        
        data = request.get_json()
        success = firebase_service.update_menu(menu_id, data)
        if success:
            return jsonify({'message': 'Menu updated successfully'})
        else:
            return jsonify({'error': 'Failed to update menu'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/editor/menus/<menu_id>', methods=['DELETE'])
@login_required
def editor_delete_menu(menu_id):
    """Delete menu as editor"""
    user_id = session.get('user_id')
    user_info = firebase_service.get_user_by_uid(user_id)
    
    if not user_info or user_info.get('role') not in ['editor', 'admin']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        # Check if editor has permission to delete this menu
        if not firebase_service.can_editor_edit_menu(user_id, menu_id):
            return jsonify({'error': 'Unauthorized to delete this menu'}), 403
        
        success = firebase_service.delete_menu(menu_id)
        if success:
            return jsonify({'message': 'Menu deleted successfully'})
        else:
            return jsonify({'error': 'Failed to delete menu'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@app.route('/api/usage/stats')
@login_required
def get_usage_stats():
    """Get current user's usage statistics"""
    user_id = session.get('user_id')
    usage_stats = firebase_service.get_user_usage_stats(user_id)
    
    return jsonify({
        'success': True,
        'usage_stats': usage_stats
    })

@app.route('/api/hello', methods=['POST'])
def hello():
    data = request.get_json()
    name = data.get('name', 'World') if data else 'World'
    return jsonify({'message': f'Hello, {name}!'})

if __name__ == '__main__':
    # Validate configuration
    Config.validate_config()
    
    # Show AI service status
    ai_status = gemini_service.get_status()
    if ai_status['available']:
        print(f"🚀 Gemini AI hazır! Model: {ai_status['model']}")
    else:
        print("⚠️ Gemini AI devre dışı. GEMINI_API_KEY ayarlayın.")
    
    # Show Firebase service status
    firebase_status = firebase_service.get_status()
    if firebase_status['available']:
        print(f"🔥 Firebase hazır! Authentication aktif.")
    else:
        print("⚠️ Firebase devre dışı. Authentication özellikleri sınırlı.")
    
    app.run(debug=True, host='0.0.0.0', port=5001)
