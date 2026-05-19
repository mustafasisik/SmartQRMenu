from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import os
import json
from config import Config
from rag_service import RestaurantRAGService
from firebase_config import firebase_service
from functools import wraps
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.config['SECRET_KEY'] = Config.SECRET_KEY

# Production behind HTTPS proxy (Render, Cloud Run, etc.)
if os.environ.get('RENDER') or os.environ.get('K_SERVICE'):
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

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

# Initialize RAG service (Groq + Pinecone menu search)
ai_service = RestaurantRAGService()

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
        menu_data = firebase_service.get_restaurant_menu(restaurant_slug)
        
        response_data = {
            'restaurant_slug': restaurant_slug,
            'menu': menu_data
        }
        return jsonify(response_data)
    except Exception as e:
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
        
        restaurant['id'] = restaurant_slug
        restaurant['slug'] = restaurant_slug

        service = firebase_service.ai_service or ai_service
        if service and service.is_available:
            try:
                usage_stats = firebase_service.get_user_usage_stats(session.get('user_id'))
                extra = f"\n{frontend_context}\n{restaurant_info}".strip()
                full_question = f"{question}\n{extra}" if extra else question

                result = service.ask_question(
                    question=full_question,
                    restaurant_data=restaurant,
                    get_menu_fn=firebase_service.get_restaurant_menu,
                    chat_history=[],
                    usage_stats=usage_stats,
                )

                if not result.get('success'):
                    return jsonify({
                        'answer': result.get('error', 'AI yanıtı alınamadı.'),
                        'restaurant_slug': restaurant_slug,
                    }), 500

                response = result['answer']
                firebase_service.save_chat_message(session.get('user_id'), question, response)
                usage_stats = firebase_service.get_user_usage_stats(session.get('user_id'))

                return jsonify({
                    'answer': response,
                    'restaurant_slug': restaurant_slug,
                    'usage_stats': usage_stats,
                    'sources': result.get('sources', []),
                })
            except Exception:
                return jsonify({
                    'answer': 'Üzgünüm, şu anda AI servisimiz meşgul. Lütfen daha sonra tekrar deneyin.',
                    'restaurant_slug': restaurant_slug,
                })
        else:
            return jsonify({
                'answer': 'Üzgünüm, AI servisimiz şu anda kullanılamıyor. Lütfen daha sonra tekrar deneyin.',
                'restaurant_slug': restaurant_slug,
            })
            
    except Exception as e:
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
        
        if decoded_token:
            # Ensure user document exists in Firestore
            firebase_service.ensure_user_document_exists(
                decoded_token['uid'],
                decoded_token.get('email', ''),
                decoded_token.get('name', '')
            )
            
            # Store user info in session
            session['user_id'] = decoded_token['uid']
            session['user_email'] = decoded_token.get('email', '')
            session['user_display_name'] = decoded_token.get('name', '')
            session['user_photo_url'] = decoded_token.get('picture', '')
            
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'redirect': '/',
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
            # Ensure user document exists in Firestore
            firebase_service.ensure_user_document_exists(
                decoded_token['uid'],
                decoded_token.get('email', ''),
                decoded_token.get('name', '')
            )
            
            # Store user info in session
            session['user_id'] = decoded_token['uid']
            session['user_email'] = decoded_token.get('email', '')
            session['user_display_name'] = decoded_token.get('name', '')
            session['user_photo_url'] = decoded_token.get('picture', '')
            
            return jsonify({
                'success': True,
                'message': 'Registration successful',
                'redirect': '/',
                'user': {
                    'uid': decoded_token['uid'],
                    'email': decoded_token.get('email', ''),
                    'display_name': decoded_token.get('name', ''),
                    'handle': decoded_token.get('name', ''),
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
        return redirect(url_for('index'))
    
    return render_template('admin/dashboard.html', user=user_info)

@app.route('/admin/users')
@login_required
def admin_users():
    """Admin users management page"""
    user_id = session.get('user_id')
    user_info = firebase_service.get_user_by_uid(user_id)
    
    if not user_info or user_info.get('role') != 'admin':
        return redirect(url_for('index'))
    
    return render_template('admin/users.html', user=user_info)

@app.route('/admin/restaurants')
@login_required
def admin_restaurants():
    """Admin restaurants management page"""
    user_id = session.get('user_id')
    user_info = firebase_service.get_user_by_uid(user_id)
    
    if not user_info or user_info.get('role') != 'admin':
        return redirect(url_for('index'))
    
    return render_template('admin/restaurants.html', user=user_info)

@app.route('/admin/cuisines')
@login_required
def admin_cuisines():
    """Admin cuisines management page"""
    user_id = session.get('user_id')
    user_info = firebase_service.get_user_by_uid(user_id)
    
    if not user_info or user_info.get('role') != 'admin':
        return redirect(url_for('index'))
    
    return render_template('admin/cuisines.html', user=user_info)

# Editor Panel Routes
@app.route('/editor')
@login_required
def editor_dashboard():
    """Editor dashboard page"""
    user_id = session.get('user_id')
    user_info = firebase_service.get_user_by_uid(user_id)
    
    if not user_info or user_info.get('role') not in ['editor', 'admin']:
        return redirect(url_for('index'))
    
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
        
        restaurant['id'] = restaurant_slug
        restaurant['slug'] = restaurant_slug

        current_usage_stats = firebase_service.get_user_usage_stats(user_id)

        response = ai_service.ask_question(
            question=question,
            restaurant_data=restaurant,
            get_menu_fn=firebase_service.get_restaurant_menu,
            chat_history=chat_history,
            usage_stats=current_usage_stats,
        )

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
                'usage_stats': usage_stats,
                'sources': response.get('sources', []),
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
    return jsonify(ai_service.get_status())

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
            # Ensure user document exists in Firestore
            firebase_service.ensure_user_document_exists(
                decoded_token['uid'],
                decoded_token.get('email', ''),
                decoded_token.get('name', '')
            )
            
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
        user_email = session.get('user_email', '')
        print(f"✅ User ID in session: {user_id}")
        print(f"📧 User email in session: {user_email}")
        
        # Get user info from Firebase (includes role from Firestore users collection)
        user_info = firebase_service.get_user_by_uid(user_id)
        
        if user_info:
            user_role = user_info.get('role', 'subscriber')
            print(f"🔐 User role from Firestore: {user_role}")
            print(f"📧 User email from service: {user_info.get('email', '')}")
            
            response_data = {
                'authenticated': True,
                'user_id': user_id,
                'user': {
                    'uid': user_id,
                    'email': user_info.get('email', ''),
                    'display_name': user_info.get('display_name', ''),
                    'photo_url': user_info.get('photo_url', ''),
                    'role': user_role
                }
            }
            print(f"📤 Auth status response: {response_data}")
            return jsonify(response_data)
        else:
            # Fallback to session data
            print("⚠️ User info not found in Firebase, using session fallback")
            response_data = {
                'authenticated': True,
                'user_id': user_id,
                'user': {
                    'uid': user_id,
                    'email': session.get('user_email', ''),
                    'display_name': session.get('user_display_name', ''),
                    'photo_url': session.get('user_photo_url', ''),
                    'role': 'subscriber'  # Default role for session fallback
                }
            }
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

@app.route('/api/user/role', methods=['GET', 'POST'])
@login_required
def user_role():
    """Get or update user role (admin only for updates)"""
    user_id = session.get('user_id')
    current_user = firebase_service.get_user_by_uid(user_id)
    
    if request.method == 'GET':
        return jsonify({
            'success': True,
            'role': current_user.get('role', 'subscriber') if current_user else 'subscriber'
        })
    
    elif request.method == 'POST':
        # Only admins can update roles
        if not current_user or current_user.get('role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        
        try:
            data = request.get_json()
            target_user_id = data.get('user_id')
            new_role = data.get('role')
            
            if not target_user_id or not new_role:
                return jsonify({'error': 'user_id and role required'}), 400
            
            # Validate role
            valid_roles = ['admin', 'editor', 'owner', 'subscriber']
            if new_role not in valid_roles:
                return jsonify({'error': f'Invalid role. Must be one of: {valid_roles}'}), 400
            
            # Update user role
            if firebase_service.set_user_role(target_user_id, new_role):
                return jsonify({
                    'success': True,
                    'message': f'User role updated to {new_role}'
                })
            else:
                return jsonify({'error': 'Failed to update user role'}), 500
                
        except Exception as e:
            return jsonify({'error': f'Error updating role: {str(e)}'}), 500

@app.route('/api/debug/user-info')
@login_required
def debug_user_info():
    """Debug endpoint to check user information and role"""
    user_id = session.get('user_id')
    user_email = session.get('user_email')
    
    # Get user info from Firebase Auth
    auth_user = None
    if user_email:
        auth_user = firebase_service._find_user_by_email(user_email)
    
    # Get user info from Firestore
    firestore_user = None
    if user_email:
        firestore_user = firebase_service.find_user_by_email_in_firestore(user_email)
    
    # Get user info from our service
    service_user = firebase_service.get_user_by_uid(user_id)
    
    return jsonify({
        'session': {
            'user_id': user_id,
            'user_email': user_email
        },
        'auth_user': auth_user,
        'firestore_user': firestore_user,
        'service_user': service_user,
        'role_from_service': service_user.get('role', 'subscriber') if service_user else 'subscriber'
    })

@app.route('/api/debug/users')
@login_required
def debug_users():
    """Debug endpoint to list all users and their roles (admin only)"""
    user_id = session.get('user_id')
    current_user = firebase_service.get_user_by_uid(user_id)
    
    # Only admins can see all users
    if not current_user or current_user.get('role') != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    # List all users with roles
    firebase_service.list_users_with_roles()
    
    # Get all users data
    users = firebase_service.get_all_users()
    
    return jsonify({
        'success': True,
        'users': users,
        'count': len(users)
    })

@app.route('/test-roles')
def test_roles_page():
    """Test page to check role-based navigation"""
    return render_template('pages/test_roles.html')

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

@app.route('/api/menu/index/<restaurant_slug>', methods=['POST'])
@login_required
def index_restaurant_menu(restaurant_slug):
    """Sync restaurant menu from Firestore into Pinecone vector index."""
    user_id = session.get('user_id')
    user_info = firebase_service.get_user_by_uid(user_id)
    role = (user_info or {}).get('role', 'subscriber')

    if role not in ('admin', 'editor', 'owner'):
        if not firebase_service.can_editor_edit_restaurant(user_id, restaurant_slug):
            return jsonify({'error': 'Unauthorized'}), 403

    force = request.get_json(silent=True) or {}
    force_reindex = bool(force.get('force', False))

    result = ai_service.sync_menu_from_firestore(
        restaurant_slug,
        firebase_service.get_restaurant_menu,
        force=force_reindex,
    )
    status_code = 200 if result.get('success') else 400
    return jsonify(result), status_code


@app.route('/api/menu/index-status/<restaurant_slug>')
@login_required
def menu_index_status(restaurant_slug):
    """Return Pinecone + Groq service status for debugging."""
    return jsonify({
        'ai': ai_service.get_status(),
        'restaurant_slug': restaurant_slug,
    })


# AI Image Analysis API Endpoint
@app.route('/api/ai/analyze-menu-image', methods=['POST'])
@login_required
def analyze_menu_image():
    """Analyze menu image using Groq vision"""
    try:
        data = request.get_json()
        image_base64 = data.get('image')
        language = data.get('language', 'tr')
                
        if not image_base64:
            return jsonify({'error': 'Image data is required'}), 400
        
        suggestions = ai_service.analyze_menu_image(image_base64, language)
        
        print(f"🔍 AI analysis result: {suggestions}")
        
        return jsonify(suggestions)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Test AI endpoint
@app.route('/api/ai/test', methods=['GET'])
def test_ai():
    """Test if AI service is working"""
    try:
        status = ai_service.get_status()
        basic_test = ai_service.test_basic_functionality()
        
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
        restaurant_id = data.get('restaurantId')
        if restaurant_id:
            ai_service.sync_menu_from_firestore(
                restaurant_id,
                firebase_service.get_restaurant_menu,
                force=True,
            )
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
            restaurant_id = data.get('restaurantId')
            if restaurant_id:
                ai_service.sync_menu_from_firestore(
                    restaurant_id,
                    firebase_service.get_restaurant_menu,
                    force=True,
                )
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
    ai_status = ai_service.get_status()
    if ai_status.get('available'):
        groq = ai_status.get('groq', {})
        pinecone = ai_status.get('pinecone', {})
        print(
            f"🚀 AI RAG hazır! Groq={groq.get('chat_model')}, "
            f"Pinecone={pinecone.get('index_name')}"
        )
    else:
        print("⚠️ AI devre dışı. GROQ_API_KEY ve PINECONE_API_KEY ayarlayın.")
    
    # Show Firebase service status
    firebase_status = firebase_service.get_status()
    if firebase_status['available']:
        print(f"🔥 Firebase hazır! Authentication aktif.")
    else:
        print("⚠️ Firebase devre dışı. Authentication özellikleri sınırlı.")
    
    port = int(os.environ.get('PORT', 5001))
    debug = os.environ.get('FLASK_DEBUG', '1') == '1'
    app.run(debug=debug, host='0.0.0.0', port=port)
