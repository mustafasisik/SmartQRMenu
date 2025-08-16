from flask import Flask, render_template, request, jsonify
import os
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')

# Restaurant verilerini yükle
def load_restaurant_data():
    try:
        with open('restaurant.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return None

@app.route('/')
def index():
    return render_template('pages/home.html')

@app.route('/api/health')
def health_check():
    return jsonify({'status': 'healthy', 'message': 'Flask app is running!'})

@app.route('/restaurant')
def restaurant():
    restaurant_data = load_restaurant_data()
    if not restaurant_data:
        return "Restoran verileri yüklenemedi", 500
    return render_template('pages/restaurant.html', data=restaurant_data)


@app.route('/api/hello', methods=['POST'])
def hello():
    data = request.get_json()
    name = data.get('name', 'World') if data else 'World'
    return jsonify({'message': f'Hello, {name}!'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
