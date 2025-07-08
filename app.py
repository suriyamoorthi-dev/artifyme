import os
import requests
from flask import Flask, request, jsonify, render_template
from supabase import create_client, Client

app = Flask(__name__)

# Together API key
TOGETHER_API_KEY = "f5d391dcc7223e9f78bd4523f9bd35236742b1c31a3d58cf597e8386de2d406e"

# Supabase Config
SUPABASE_URL = "https://mmhvljqdyzskxnzkrgql.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1taHZsanFkeXpza3huemtyZ3FsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTEyMTAwOTcsImV4cCI6MjA2Njc4NjA5N30.gtVE8Dg4fdf37xEAAghgrMjyIpOZOTnIuOFn0qk59uM"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.route('/')
def home():
    return render_template('landing.html')

@app.route('/avatar')
def avatar_page():
    response = supabase.table('shop_offers').select('*, gift_shops(link)').execute()
    
    offers = []
    for o in response.data:
        shop_data = o.get('gift_shops') or {}

        offers.append({
            "id": o['id'],
            "title": o['title'],
            "description": o.get('description', ''),
            "shop_url": shop_data.get('link') if shop_data else '#',
            "color": o.get('color', 'bg-white')
        })
    
    return render_template('avatar.html', offers=offers)

@app.route('/gifts')
def gifts_page():
    return render_template('gifts_shops.html')


@app.route('/contact')
def contact():
    return render_template('contact.html')


@app.route('/terms')
def terms():
    return render_template('terms.html')


@app.route('/privacy')
def privacy():
    return render_template('privacy.html')


@app.route('/api/generate-avatar', methods=['POST'])
def api_generate_avatar():
    data = request.get_json()
    prompt_text = data.get('prompt')

    if not prompt_text:
        return jsonify({"error": "Prompt required"}), 400

    image_url = generate_ai_avatar(prompt_text)

    if image_url:
        return jsonify({"avatar_url": image_url})
    else:
        return jsonify({"error": "Error generating avatar"}), 500

import requests
def generate_ai_avatar(prompt_text):
    response = requests.post(
        "https://api.together.xyz/v1/images/generations",
        headers={"Authorization": f"Bearer {TOGETHER_API_KEY}"},
        json={
            "model": "black-forest-labs/FLUX.1-schnell-Free",
            "prompt": prompt_text,
            "width": 512,
            "height": 512,
            "steps": 4
        }
    )

    try:
        result = response.json()
    except:
        return None

    if response.status_code == 200 and "data" in result and len(result["data"]) > 0:
        short_url = result["data"][0]["url"]
        return short_url  # Return the short link only

    return None




@app.route('/gifts')
def gifts():
    return render_template('gifts_shops.html')


@app.route('/order')
def order():
    avatar_url = request.args.get('avatar')

    if not avatar_url:
        return "Invalid request", 400

    return render_template('order.html', avatar_url=avatar_url)


@app.route('/place_order', methods=['POST'])
def place_order():
    name = request.form.get('name')
    address = request.form.get('address')
    phone = request.form.get('phone')
    product = request.form.get('product')
    avatar_url = request.form.get('avatar_url')

    print(f"New Order: {product}, {name}, {address}, {phone}, {avatar_url}")
    return "Thank you for your order! We will contact you soon."


# ------------------- Supabase Gift Shop API ------------------- #

# --------------------- Admin Shop Page ---------------------
@app.route('/admin/shops')
def admin_shops():
    return render_template('admin_shops.html')


# --------------------- Shop API ---------------------
@app.route('/api/shops', methods=['GET'])
def get_all_shops():
    response = supabase.table('gift_shops').select('*').order('id', desc=True).execute()
    return jsonify(response.data or [])


@app.route('/api/shops', methods=['POST'])
def add_shop():
    data = request.json
    required_fields = ['name', 'location', 'contact', 'link']
    if not all(field in data for field in required_fields):
        return "Missing fields", 400

    supabase.table('gift_shops').insert([{
        "name": data['name'],
        "location": data['location'],
        "contact": data['contact'],
        "link": data['link'],
        "image": data.get('image', '')
    }]).execute()

    return jsonify({"status": "success"})


@app.route('/api/shops/<int:shop_id>', methods=['GET'])
def get_shop(shop_id):
    response = supabase.table('gift_shops').select('*').eq('id', shop_id).single().execute()
    if response.data:
        return jsonify(response.data)
    return jsonify({'error': 'Shop not found'}), 404


@app.route('/api/shops/<int:shop_id>', methods=['PUT'])
def update_shop(shop_id):
    data = request.json
    supabase.table('gift_shops').update(data).eq('id', shop_id).execute()
    return jsonify({"status": "updated"})


@app.route('/api/shops/<int:shop_id>', methods=['DELETE'])
def delete_shop(shop_id):
    supabase.table('gift_shops').delete().eq('id', shop_id).execute()
    return jsonify({"status": "deleted"})


# --------------------- Shop Details Page ---------------------
@app.route('/shop/<int:shop_id>')
def shop_page(shop_id):
    return render_template('shop_details.html', shop_id=shop_id)


# --------------------- Shop Product API ---------------------
@app.route('/api/shops/<int:shop_id>/products', methods=['GET'])
def get_shop_products(shop_id):
    response = supabase.table('shop_products').select('*').eq('shop_id', shop_id).order('id', desc=True).execute()
    return jsonify(response.data or [])


@app.route('/api/products', methods=['POST'])
def add_product():
    data = request.json
    required_fields = ['shop_id', 'name', 'image', 'description']
    if not all(field in data for field in required_fields):
        return "Missing fields", 400

    supabase.table('shop_products').insert({
        'shop_id': data['shop_id'],
        'name': data['name'],
        'image': data['image'],
        'description': data['description']
    }).execute()

    return jsonify({'status': 'success'})


@app.route('/api/products/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    data = request.json
    supabase.table('shop_products').update(data).eq('id', product_id).execute()
    return jsonify({'status': 'updated'})


@app.route('/api/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    supabase.table('shop_products').delete().eq('id', product_id).execute()
    return jsonify({'status': 'deleted'})


# --------------------- Shop Review API ---------------------
@app.route('/api/reviews', methods=['GET'])
def get_reviews():
    shop_id = request.args.get('shop_id')
    response = supabase.table('shop_reviews').select('*').eq('shop_id', shop_id).order('id', desc=True).execute()
    return jsonify(response.data or [])


@app.route('/api/reviews', methods=['POST'])
def post_review():
    data = request.json
    shop_id = data.get('shop_id')
    review_text = data.get('review')

    if not shop_id or not review_text:
        return jsonify({'error': 'Missing data'}), 400

    supabase.table('shop_reviews').insert({
        'shop_id': shop_id,
        'review': review_text
    }).execute()

    return jsonify({'message': 'Review added'}), 201
@app.route('/api/offers')
def get_offers():
    response = supabase.table('shop_offers').select('*, gift_shops(name, link)').execute()
    
    offers = []
    for o in response.data:
        shop_data = o.get('gift_shops') or {}
        
        offers.append({
            "id": o['id'],
            "title": o['title'],
            "image": o.get('image', ''),
            "shop_id": o['shop_id'],
            "shop_name": shop_data.get('name', ''),
            "shop_url": shop_data.get('link', f"/shop/{o['shop_id']}"),
            "description": o.get('description', ''),
            "color": o.get('color', 'bg-white'),
            "percentage": o.get('percentage', '')
        })
        
    return jsonify(offers)

@app.route('/api/offers', methods=['POST'])
def add_offer():
    data = request.json
    supabase.table('shop_offers').insert({
        "title": data.get('title', ''),
        "description": data.get('description', ''),
        "color": data.get('color', 'bg-white'),
        "shop_id": data.get('shop_id'),
        "percentage": data.get('percentage', '')
    }).execute()
    return jsonify({"status": "added"})


@app.route('/api/offers/<int:offer_id>', methods=['PUT'])
def update_offer(offer_id):
    data = request.json
    supabase.table('shop_offers').update({
        "title": data.get('title', ''),
        "description": data.get('description', ''),
        "color": data.get('color', 'bg-white'),
        "shop_id": data.get('shop_id'),
        "percentage": data.get('percentage', '')
    }).eq('id', offer_id).execute()
    return jsonify({"status": "updated"})

@app.route('/api/offers/<int:offer_id>', methods=['DELETE'])
def delete_offer(offer_id):
    supabase.table('shop_offers').delete().eq('id', offer_id).execute()
    return jsonify({"status": "deleted"})


# ------------------- End Supabase Gift Shop API ------------------- #

import os

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
