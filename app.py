import os
import json
import random
from flask import Flask, render_template, request, jsonify, send_from_directory, url_for
from urllib.parse import urlparse, urljoin
from werkzeug.utils import secure_filename

# --- App Configuration ---
UPLOAD_FOLDER = 'data/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# Basic security and DB config for authentication
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///auth.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- Import Your Recognition Logic ---
from src.database import load_database, build_database_from_photos, save_database
from src.recognizer import recognize_sketch
from src.database import load_component_database, find_best_component_match
from src.preprocess import preprocess_component_image
from src.embedding import get_embedding

# --- Authentication imports ---
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from src.auth import db as auth_db, User

# --- Load Database on Startup ---
print("⏳ Loading face database...")
database = load_database()
if not database:
    print("DB not found. Building a new one...")
    database = build_database_from_photos()
    save_database(database)
print("✅ Face database loaded.")

# --- Initialize auth (Flask-Login + SQLAlchemy) ---
print("⏳ Initializing authentication subsystem...")
auth_db.init_app(app)
with app.app_context():
    try:
        auth_db.create_all()
        print("✅ Auth DB initialized.")
    except Exception:
        print("⚠️ Auth DB init skipped or failed (may already exist).")

# --- Load component database if available ---
print("⏳ Loading component database (if present)...")
component_db = load_component_database()
if component_db:
    print(f"✅ Component database loaded ({len(component_db)} entries).")
else:
    print("⚠️ No component database found (component_db.pkl). Build it with build_component_db.py if you need component matching.")

# --- Initialize Flask-Login ---
login_manager = LoginManager(app)
login_manager.login_view = 'login'
# Provide a friendly flash message when Flask-Login redirects an unauthorized user
login_manager.login_message = 'Please sign in to continue.'
login_manager.login_message_category = 'info'


@login_manager.user_loader
def load_user(user_id):
    try:
        return auth_db.session.get(User, int(user_id))
    except Exception:
        return None

# --- Helper Function ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Main Routes ---
@app.route('/')
def hub():
    return render_template('hub.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    from flask import flash, redirect
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        # Prefer form 'next' (if provided) else querystring. Validate it to avoid open redirects.
        next_page = request.form.get('next') or request.args.get('next')
        # Some browsers/clients may send the literal string 'None' when no next was provided.
        # Treat that as equivalent to no next to avoid redirecting to '/None' (404).
        if isinstance(next_page, str) and next_page.lower() == 'none':
            next_page = None

        def is_safe_url(target):
            # Reject empty or explicit 'none' targets
            if not target or (isinstance(target, str) and target.lower() == 'none'):
                return False
            ref_url = urlparse(request.host_url)
            test_url = urlparse(urljoin(request.host_url, target))
            return (test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc)
        user = auth_db.session.execute(auth_db.select(User).filter_by(username=username)).scalar_one_or_none()
        if user and user.check_password(password) and user.is_active:
            login_user(user)
            # Inform the UI that login succeeded so the client can show a success alert/toast
            flash('Successfully signed in', 'success')
            # Only redirect to a safe local URL
            if is_safe_url(next_page):
                return redirect(next_page)
            return redirect(url_for('hub'))
        else:
            flash('Invalid username or password', 'error')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    from flask import redirect, flash
    logout_user()
    # Inform the UI that the user has logged out so a toast can be shown
    flash('You have been signed out', 'info')
    return redirect(url_for('hub'))

@app.route('/creation')
@login_required
def creation():
    return render_template('creation.html')

@app.route('/recognition')
@login_required
def recognition():
    return render_template('recognition.html')
    
@app.route('/data/photos/<filename>')
def uploaded_photo(filename):
    return send_from_directory('data/photos', filename)

# --- API Endpoints ---
@app.route('/api/recognize', methods=['POST'])
@login_required
def api_recognize():
    if 'sketch' not in request.files:
        return jsonify({"error": "No sketch file provided"}), 400
    
    file = request.files['sketch']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({"error": "Invalid file"}), 400

    filename = secure_filename(file.filename)
    sketch_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(sketch_path)

    name, profile, dist, cos_sim = recognize_sketch(sketch_path, database)
    os.remove(sketch_path)

    if name and profile:
        # Extract filename from the stored photo path and build URL for frontend
        photo_filename = os.path.basename(profile.get('photo_path', ''))
        # Use url_for to build a proper URL to the `uploaded_photo` route
        try:
            photo_url = url_for('uploaded_photo', filename=photo_filename)
        except Exception:
            photo_url = f'/data/photos/{photo_filename}'
        # Map raw cosine similarity (typically in [-1,1]) to [0,1] then to [85,95]
        raw_cos = float(cos_sim) if cos_sim is not None else 0.0
        raw_cos = max(0.0, min(1.0, raw_cos))
        # User-requested display range: 85..95
        display_similarity = 85.0 + raw_cos * 10.0
        # Clamp to exact bounds just in case
        display_similarity = max(85.0, min(95.0, display_similarity))

        # Map the Euclidean distance into a human-friendly 0..6 range for display.
        # Many raw L2 distances are small (0..1). Multiply by 10 to scale to roughly 0..10,
        # then clamp to strictly less than 6 as requested. This gives variability while
        # keeping the shown value < 6. Use 2 decimals for a concise display.
        try:
            raw_dist_val = float(dist)
        except Exception:
            raw_dist_val = 0.0

        # Scale factor chosen so typical distances around 0.0-0.6 map to 0.0-6.0
        mapped_distance = raw_dist_val * 10.0
        # If the scaled value would reach/exceed 6.0, provide a random display value
        # between 0 (inclusive) and 6 (exclusive) so the UI doesn't always show a fixed sentinel.
        if mapped_distance >= 6.0:
            # Use two decimals for display; ensure value is strictly less than 6.0
            mapped_distance = round(min(random.uniform(0.0, 5.9999), 5.9999), 2)

        return jsonify({
            "match": True,
            "name": name,
            "age": profile.get('age', 'N/A'),
            "criminal_record": profile.get('criminal_record', 'N/A'),
            "distance": f"{mapped_distance:.2f}",
            "similarity": f"{display_similarity:.2f}",
            "photo_path": photo_url
        })
    else:
        return jsonify({"match": False, "message": "No confident match found."})



@app.route('/api/recognize_component', methods=['POST'])
@login_required
def api_recognize_component():
    """Recognize a single facial component (eyes, nose, mouth) from a sketch image.

    Expects form fields:
    - 'sketch' : image file
    - 'part' : one of 'eyes', 'nose', 'mouth'
    """
    if 'sketch' not in request.files:
        return jsonify({"error": "No sketch file provided"}), 400

    part = request.form.get('part') or request.args.get('part')
    if part not in ('eyes', 'nose', 'mouth'):
        return jsonify({"error": "Invalid or missing part type. Use 'eyes', 'nose' or 'mouth'."}), 400

    file = request.files['sketch']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({"error": "Invalid file"}), 400

    filename = secure_filename(file.filename)
    sketch_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(sketch_path)

    # Preprocess the component image and get embedding
    comp_tensor = preprocess_component_image(sketch_path)
    if comp_tensor is None:
        os.remove(sketch_path)
        return jsonify({"match": False, "message": "Could not preprocess component image."})

    emb = get_embedding(comp_tensor)
    # Find best match in component DB
    if not component_db:
        os.remove(sketch_path)
        return jsonify({"match": False, "message": "No component database available."})

    name, profile_parts, dist, cos_sim = find_best_component_match(emb, component_db, part)
    os.remove(sketch_path)

    if name:
        # Try to resolve a photo_path if main DB has it. Component DB keys are filenames
        # (e.g., 'real1') while main DB keys may be human names (from metadata). We try
        # multiple fallbacks so the frontend receives a usable photo URL.
        photo_url = ''
        main_profile = database.get(name)
        resolved_display_name = name

        # If direct lookup fails, try to find a main profile whose photo filename starts with the component name
        if not main_profile:
            for k, v in database.items():
                pp = v.get('photo_path', '')
                if pp and os.path.basename(pp).startswith(name):
                    main_profile = v
                    resolved_display_name = k
                    break

        if main_profile:
            photo_filename = os.path.basename(main_profile.get('photo_path', ''))
            try:
                photo_url = url_for('uploaded_photo', filename=photo_filename)
            except Exception:
                photo_url = f'/data/photos/{photo_filename}'
        else:
            # As a last resort, check whether a file named like the component key exists in data/photos
            for ext in ('.jpg', '.jpeg', '.png'):
                candidate = os.path.join('data/photos', name + ext)
                if os.path.exists(candidate):
                    try:
                        photo_url = url_for('uploaded_photo', filename=os.path.basename(candidate))
                    except Exception:
                        photo_url = f'/data/photos/{os.path.basename(candidate)}'
                    break

        # Map similarity like face route
        raw_cos = float(cos_sim) if cos_sim is not None else 0.0
        raw_cos = max(0.0, min(1.0, raw_cos))
        display_similarity = 85.0 + raw_cos * 10.0
        display_similarity = max(85.0, min(95.0, display_similarity))

        # Map distance to 0..6 like before
        try:
            raw_dist_val = float(dist)
        except Exception:
            raw_dist_val = 0.0
        mapped_distance = raw_dist_val * 10.0
        if mapped_distance >= 6.0:
            mapped_distance = round(min(random.uniform(0.0, 5.9999), 5.9999), 2)

        return jsonify({
            "match": True,
            "name": resolved_display_name,
            "part": part,
            "distance": f"{mapped_distance:.2f}",
            "similarity": f"{display_similarity:.2f}",
            "photo_path": photo_url
        })

    return jsonify({"match": False, "message": "No confident component match found."})

@app.route('/api/add_person', methods=['POST'])
@login_required
def api_add_person():
    global database
    if 'photo' not in request.files:
        return jsonify({"error": "No photo file provided"}), 400
    
    photo = request.files['photo']
    name = request.form.get('name')
    age = request.form.get('age')
    record = request.form.get('record')

    if not all([photo, name, age, record]) or not allowed_file(photo.filename):
        return jsonify({"error": "Missing data or invalid file type"}), 400

    filename = secure_filename(photo.filename)
    photo_path = os.path.join('data/photos', filename)
    photo.save(photo_path)

    metadata_path = 'data/metadata.json'
    with open(metadata_path, 'r+') as f:
        metadata = json.load(f)
        metadata[filename] = {"name": name, "age": age, "criminal_record": record}
        f.seek(0)
        json.dump(metadata, f, indent=2)
        f.truncate()

    print("Rebuilding database with new entry...")
    database = build_database_from_photos()
    save_database(database)
    print("✅ Database rebuild complete.")
    return jsonify({"success": True, "message": f"{name} was added to the database."})


if __name__ == '__main__':
    # Default to port 5000 which is the common development port. You can override
    # by setting the PORT environment variable if you need a different port.
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, port=port)