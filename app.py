import os
import requests
from flask import Flask, request, jsonify, render_template
from supabase import create_client, Client
import base64
import requests
from io import BytesIO
import time
from PIL import Image
from dotenv import load_dotenv
app = Flask(__name__)

# Together API key
TOGETHER_API_KEY = "f5d391dcc7223e9f78bd4523f9bd35236742b1c31a3d58cf597e8386de2d406e"

# Supabase Config
from supabase import create_client, Client
load_dotenv()

# Get Supabase credentials from .env
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Create Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


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

def generate_ai_avatar(prompt_text):
    try:
        response = requests.post(
            "https://api.together.xyz/v1/images/generations",
            headers={"Authorization": f"Bearer {TOGETHER_API_KEY}"},
            json={
                "model": "black-forest-labs/FLUX.1-schnell-Free",
                "prompt": prompt_text,
                "width": 512,
                "height": 512,
                "steps": 4
            },
            timeout=60
        )

        result = response.json()
        short_url = result["data"][0]["url"]
        resolved = requests.head(short_url, allow_redirects=True)
        long_url = resolved.url

        img_response = requests.get(long_url)
        img = Image.open(BytesIO(img_response.content)).convert("RGB")

        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=90)
        buffer.seek(0)

        filename = f"avatar_{int(time.time())}.jpg"
        path = filename  # ✅ Fix here: just filename

        # Upload to Supabase
        upload = supabase.storage.from_('avatars').upload(
            path,
            buffer.getvalue(),
            {"content-type": "image/jpeg"}
        )

        if upload:
            public_url = f"{SUPABASE_URL}/storage/v1/object/public/avatars/{filename}"
            print("✅ Uploaded avatar:", public_url)
            return public_url
        else:
            print("❌ Upload failed")
            return None

    except Exception as e:
        print("❌ Error:", e)
        return None


@app.route('/api/generate-avatar', methods=['POST'])
def api_generate_avatar():
    data = request.get_json(silent=True)  # ✅ avoid crashing if not JSON
    if not data:
        return jsonify({"error": "Invalid or missing JSON"}), 400

    prompt = data.get("prompt")
    if not prompt:
        return jsonify({"error": "Prompt required"}), 400

    avatar_url = generate_ai_avatar(prompt)
    if avatar_url:
        return jsonify({"avatar_url": avatar_url})
    return jsonify({"error": "Avatar generation failed"}), 500

@app.route('/api/avatars')
def list_avatars():
    try:
        response = supabase.storage.from_('avatars').list()
        files = response or []

        public_urls = [
            f"{SUPABASE_URL}/storage/v1/object/public/avatars/{f['name']}"
            for f in files
        ]

        return jsonify(public_urls)
    except Exception as e:
        print("Error loading avatars:", e)
        return jsonify([]), 500

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

# --------------------- Admin Page ---------------------
@app.route('/admin/shops')
def admin_shops():
    return render_template('admin_shops.html')


# --------------------- Shop API ---------------------
@app.route('/api/shops', methods=['GET'])
def get_all_shops():
    response = supabase.table('gift_shops').select('*').order('id', desc=True).execute()
    return jsonify(response.data or [])


# ✅ Add Shop (with socials, map, timings, homepage flag)
@app.route('/api/shops', methods=['POST'])
def add_shop():
    data = request.json
    required_fields = ['name', 'location', 'contact']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing fields"}), 400

    shop_data = {
        "name": data['name'],
        "location": data['location'],
        "contact": data['contact'],
        "whatsapp": data.get('whatsapp'),
        "instagram": data.get('instagram'),
        "website": data.get('website'),
        "image": data.get('image'),
        "map_url": data.get('map_url'),
        "timings": data.get('timings'),
        "show_on_homepage": bool(data.get('show_on_homepage', False))
    }

    supabase.table('gift_shops').insert([shop_data]).execute()
    return jsonify({"status": "success"})


# ✅ Get single shop
@app.route('/api/shops/<int:shop_id>', methods=['GET'])
def get_shop(shop_id):
    response = supabase.table('gift_shops').select('*').eq('id', shop_id).single().execute()
    if response.data:
        return jsonify(response.data)
    return jsonify({'error': 'Shop not found'}), 404


# ✅ Update shop

@app.route('/api/shops/<int:shop_id>', methods=['PUT'])
def update_shop(shop_id):
    data = request.json
    shop_data = {}

    allowed_fields = [
        "name", "location", "contact", "whatsapp", "instagram",
        "website", "image", "map_url", "timings", "show_on_homepage"
    ]

    for field in allowed_fields:
        if field in data:   # ✅ only update fields that are sent
            if field == "show_on_homepage":
                shop_data[field] = bool(data[field])
            else:
                shop_data[field] = data[field]

    if not shop_data:
        return jsonify({"error": "No valid fields provided"}), 400

    supabase.table('gift_shops').update(shop_data).eq('id', shop_id).execute()
    return jsonify({"status": "updated"})

# ✅ Delete shop
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
    # 1. Get all products for this shop
    products_res = supabase.table('shop_products').select('*').eq('shop_id', shop_id).execute()
    products = products_res.data or []

    # 2. For each product, get its images
    for p in products:
        images_res = supabase.table('product_images').select('image_url').eq('product_id', p['id']).execute()
        p['images'] = [img['image_url'] for img in images_res.data]

        # Add main image also
        if p.get('image'):
            p['images'].insert(0, p['image'])

    return jsonify(products)

@app.route('/api/products', methods=['POST'])
def add_product():
    data = request.json
    required_fields = ['shop_id', 'name', 'images', 'description']  # images is now a list
    if not all(field in data for field in required_fields):
        return "Missing fields", 400

    # 1️⃣ Insert into shop_products
    res = supabase.table('shop_products').insert({
        'shop_id': data['shop_id'],
        'name': data['name'],
        'description': data['description']
    }).execute()

    if not res.data:
        return "Failed to insert product", 500

    product_id = res.data[0]['id']

    # 2️⃣ Insert multiple images into product_images
    images_data = [{'product_id': product_id, 'image_url': url} for url in data['images']]
    supabase.table('product_images').insert(images_data).execute()

    return jsonify({'status': 'success', 'product_id': product_id})


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


# --------------------- Offers API ---------------------
@app.route('/api/offers')
def get_offers():
    response = supabase.table('shop_offers').select('*, gift_shops(name, website)').execute()
    
    offers = []
    for o in response.data:
        shop_data = o.get('gift_shops') or {}
        
        offers.append({
            "id": o['id'],
            "title": o['title'],
            "image": o.get('image', ''),
            "shop_id": o['shop_id'],
            "shop_name": shop_data.get('name', ''),
            "shop_url": shop_data.get('website', f"/shop/{o['shop_id']}"),
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
        "percentage": data.get('percentage', ''),
        "image": data.get('image', '')
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
        "percentage": data.get('percentage', ''),
        "image": data.get('image', '')
    }).eq('id', offer_id).execute()
    return jsonify({"status": "updated"})


@app.route('/api/offers/<int:offer_id>', methods=['DELETE'])
def delete_offer(offer_id):
    supabase.table('shop_offers').delete().eq('id', offer_id).execute()
    return jsonify({"status": "deleted"})


# --------------------- celebration ---------------------

@app.route("/celebration")
def celebration_page():
    return render_template("celebration.html")

@app.route("/api/generate-celebration-text", methods=["POST"])
def generate_celebration_text():
    data = request.get_json()
    event = data.get("event")
    style = data.get("style")
    extra = data.get("extra", "")

    if not event or not style:
        return jsonify({"error": "Event and style are required"}), 400

    prompt = f"Suggest 3 unique {style} style ideas for a {event} celebration. Include decorations, theme, and photography ideas. Extra details: {extra}"

    try:
        response = requests.post(
            "https://api.together.xyz/v1/chat/completions",
            headers={"Authorization": f"Bearer {TOGETHER_API_KEY}"},
            json={
                "model": "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 300
            },
            timeout=60
        )
        result = response.json()
        text = result["choices"][0]["message"]["content"]

        # Split into ideas
        ideas = [line.strip("•-123. ") for line in text.split("\n") if line.strip()]
        return jsonify({"ideas": ideas})

    except Exception as e:
        print("❌ Error:", e)
        return jsonify({"error": "Generation failed"}), 500

# ------------------- End Supabase Gift Shop API ------------------- #
if __name__ == '__main__':
    # Only runs locally for debugging
    app.run(debug=True)

