from multiprocessing.resource_tracker import getfd  
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from markupsafe import Markup
from datetime import date, datetime
import re
import os

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# --- UPLOAD_FOLDER (CTF, intentionally unsafe) ---
UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Flags for CTF triggers
UPLOAD_CTF_FLAG = "THM{file_upload_successful}"
PROFILE_UPLOAD_CTF_FLAG = "THM{profile_upload_successful}"

# Contact SQLi flags (multiple)
CONTACT_FLAGS = {
    "or_single": "Flag: THM{contact_sqli_success}",
}

# --- In-memory "database" ---
users = []  # Stores registered users
vehicles = [
    {"id": 1, "name": "Honda Civic", "description": "Reliable and fuel-efficient sedan, perfect for city drives and comfortable journeys.", "price_per_day": 50, "image": "sedan.jpeg"},
    {"id": 2, "name": "Toyota RAV4", "description": "Spacious SUV with powerful performance. Great for long trips and group travel.", "price_per_day": 70, "image": "suv.webp"},
    {"id": 3, "name": "BMW 5 Series", "description": "Luxury sedan with premium interiors, smooth handling, and stylish design.", "price_per_day": 120, "image": "luxury.jpg"},
    {"id": 4, "name": "Ford Ranger", "description": "Versatile pickup truck with durability and strength. Perfect for off-road travel and moving goods.", "price_per_day": 80, "image": "truck.jpg"},
    {"id": 5, "name": "Volkswagen Golf", "description": "Stylish hatchback with excellent handling and great fuel economy. Ideal for daily commutes.", "price_per_day": 45, "image": "hatchback.jpg"},
    {"id": 6, "name": "Chrysler Pacifica", "description": "Spacious minivan designed for families. Comfortable seating, safety features, and plenty of storage.", "price_per_day": 90, "image": "minivan.webp"},
    {"id": 7, "name": "Porsche 911", "description": "Legendary sports car offering exhilarating speed and top-notch performance. Perfect for thrill-seekers.", "price_per_day": 200, "image": "sports.jpg"},
    {"id": 8, "name": "Tesla Model 3", "description": "Fully electric sedan combining innovation with sustainability. Features autopilot and zero emissions driving.", "price_per_day": 110, "image": "electric.jpg"}
]

bookings = []  # Stores booking records

# --- Hidden CTF booking for IDOR challenge ---
dummy_user = {"name": "SecretUser", "email": "secret@drivenow.com", "phone": "0000000000", "password": "notused"}

bookings.append({
    "id": 999,  # static and predictable
    "user": dummy_user,
    "vehicle": {
        "id": 999,
        "name": "CTF Vehicle",
        "description": "🎉 Congrats! You exploited IDOR. FLAG: THM{idor_exploited_successfully}",
        "price_per_day": 120,
        "image": "hacker.webp"
    },
    "start_date": "2025-09-01",
    "end_date": "2025-09-10",
    "days": 10,
    "total_price": 1200
})

next_booking_id = 0  # <- incremental booking ID (predictable — used for the IDOR lab)

# Simple admin credentials
ADMIN_EMAIL = "admin@gmail.com"
ADMIN_PASSWORD = "admin123"

# --- Routes ---

@app.route('/')
def index():
    # index template will optionally show contact_flag if provided by contact POST render
    return render_template('index.html')

@app.route('/show_vehicles')
def show_vehicles():
    return render_template('vehicles.html', vehicles=vehicles)

@app.route('/profile')
def profile():
    # require login
    if 'user' not in session:
        flash("Please login to view your profile.")
        return redirect(url_for('login'))

    user = session['user']
    # only keep this user's bookings
    user_bookings = [b for b in bookings if b['user']['email'] == user['email']]

    # show profile; profile template will optionally display profile_upload_flag if given (none here)
    return render_template('profile.html', user=user, bookings=user_bookings, profile_upload_flag=None)

# -------------------------
# Generic upload endpoint (example: re-renders a book page)
# -------------------------
@app.route('/upload', methods=['POST'])
def upload():
    """
    CTF/demo: save uploaded file unsafely and return upload_flag when a .txt is uploaded.
    Intentionally unsafe: using file.filename as-is.
    This example re-renders the 'booking' page (non-destructive example).
    """
    file = request.files.get('file')
    upload_flag = None

    if file:
        filename = file.filename  # intentionally unsafe for CTF
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        # ensure folder exists (should already)
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        file.save(save_path)

        # Trigger the flag if any .txt file is uploaded
        if filename.lower().endswith(".txt"):
            upload_flag = UPLOAD_CTF_FLAG

    # Re-render booking page with upload_flag (we pass vehicles so template can render)
    return render_template('booking.html', vehicles=vehicles, upload_flag=upload_flag)

# -------------------------
# Profile upload endpoint (CTF)
# -------------------------
@app.route('/upload_profile', methods=['POST'])
def upload_profile():
    """
    CTF/demo: save uploaded file unsafely (profile upload). If .txt uploaded, return flag on profile page.
    Intentionally unsafe: uses file.filename as given by client.
    """
    if 'user' not in session:
        flash("Please login to upload files on your profile.")
        return redirect(url_for('login'))

    file = request.files.get('file')
    profile_upload_flag = None

    if file:
        filename = file.filename  # intentionally unsafe for CTF
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        file.save(save_path)

        # Trigger the flag if the file is any .txt file
        if filename.lower().endswith(".txt"):
            profile_upload_flag = PROFILE_UPLOAD_CTF_FLAG

        # Optionally store the uploaded filename in the session (so profile can show it)
        session['user']['last_uploaded'] = filename
        # persist into users list if exists
        for u in users:
            if u.get('email') == session['user'].get('email'):
                u['last_uploaded'] = filename
                break

    # Re-render profile page for current user and show the profile_upload_flag (if any)
    user = session['user']
    user_bookings = [b for b in bookings if b['user']['email'] == user['email']]
    return render_template('profile.html', user=user, bookings=user_bookings, profile_upload_flag=profile_upload_flag)

# Static serve uploaded files for convenience in the CTF
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    # Serve files directly from the uploads folder
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash("Passwords do not match!")
            return redirect(url_for('register'))

        if any(u['email'] == email for u in users):
            flash("Email already registered!")
            return redirect(url_for('register'))

        users.append({"name": name, "email": email, "phone": phone, "password": password})
        flash("Registration successful! You can now login.")
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    sqli_flag = None
    query_value = ''

    if request.method == 'POST':
        email = request.form.get('email', '')
        password = request.form.get('password', '')

        query_value = email  # preserve email for re-rendering the form

        # Make password required (show message on same page)
        if not password:
            flash("Password is required!")
            return render_template('login.html', sqli_flag=None, query_value=query_value)

        # Simulated vulnerable SQL query (for demo / CTF purposes only)
        query = f"SELECT * FROM users WHERE email='{email}' AND password='{password}'"
        print("Simulated SQL query:", query)

        # --- SQLi CTF Challenge ---
        # If injection-like string is found in the email input, reveal flag inline
        if re.search(r"'[\s]*or[\s]*'1'='1", email, re.IGNORECASE):
            sqli_flag = "THM{sqli_bypass_login_success}"
            # Render login page with the flag visible (no redirect)
            return render_template('login.html', sqli_flag=sqli_flag, query_value=query_value)

        # --- Normal Admin login ---
        if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
            session['admin'] = True
            return redirect(url_for('admin'))

        # --- Normal User login ---
        user = next((u for u in users if u['email'] == email and u['password'] == password), None)
        if user:
            session['user'] = user
            return redirect(url_for('index'))

        # Fallback: invalid login (show message on same page)
        flash("Invalid email or password!")
        return render_template('login.html', sqli_flag=None, query_value=query_value)

    # GET -> render the login page normally
    return render_template('login.html', sqli_flag=None, query_value='')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/booking', methods=['GET', 'POST'])
def booking():
    global next_booking_id

    if 'user' not in session:
        flash("Please login first to book a vehicle.")
        return redirect(url_for('login'))

    if request.method == 'POST':
        try:
            vehicle_id = int(request.form['vehicle_id'])
        except (KeyError, ValueError):
            flash("Please select a valid vehicle.")
            return redirect(url_for('booking'))

        start_date = request.form.get('start_date', '')
        end_date = request.form.get('end_date', '')

        vehicle = next((v for v in vehicles if v['id'] == vehicle_id), None)
        if vehicle:
            try:
                start = datetime.strptime(start_date, "%Y-%m-%d").date()
                end = datetime.strptime(end_date, "%Y-%m-%d").date()
                days = (end - start).days
                if days < 1:
                    days = 1
            except Exception:
                days = 1

            total_price = days * vehicle["price_per_day"]

            booking_record = {
                "id": next_booking_id,
                "user": session['user'],
                "vehicle": vehicle,
                "start_date": start_date,
                "end_date": end_date,
                "days": days,
                "total_price": total_price
            }

            bookings.append(booking_record)
            next_booking_id += 1

            flash(f"Booking successful! Your booking id is {booking_record['id']}")
            return redirect(url_for('profile'))

    return render_template('booking.html', vehicles=vehicles)

# ---- Vulnerable IDOR endpoint ----
@app.route('/view_booking/<int:booking_id>')
def view_booking(booking_id):
    if 'user' not in session:
        flash("Please login to view booking details.")
        return redirect(url_for('login'))

    booking = next((b for b in bookings if b.get('id') == booking_id), None)
    if not booking:
        return "Booking not found", 404

    return render_template("view_booking.html", booking=booking)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'admin' not in session:
        flash("Admin login required!")
        return redirect(url_for('login'))

    upload_flag = None  # <--- add this

    if request.method == 'POST':
        new_id = max(v['id'] for v in vehicles) + 1 if vehicles else 1

        # Handle file upload
        image_filename = ""
        file = request.files.get('image') or request.files.get('file') or None
        if file and getattr(file, 'filename', ''):
            image_filename = file.filename  # intentionally unsafe
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            file.save(save_path)

            # 🔑 Add flag trigger here
            if image_filename.lower().endswith(".txt"):
                upload_flag = "THM{file_upload_successful}"
        else:
            image_filename = request.form.get('image', '').strip()

        name = request.form.get('name', '')
        description = request.form.get('description', '')
        price_raw = request.form.get('price', '0')

        try:
            price_val = float(price_raw)
        except Exception:
            price_val = 0.0

        vehicles.append({
            "id": new_id,
            "name": name,
            "description": description,
            "price_per_day": price_val,
            "image": image_filename
        })
        flash("Vehicle added successfully!")
        # ⬇️ pass upload_flag back to template
        return render_template('admin.html', vehicles=vehicles, bookings=bookings, upload_flag=upload_flag)

    return render_template('admin.html', vehicles=vehicles, bookings=bookings)


@app.route('/delete_vehicle/<int:vehicle_id>')
def delete_vehicle(vehicle_id):
    if 'admin' not in session:
        flash("Admin login required!")
        return redirect(url_for('login'))

    global vehicles
    vehicles = [v for v in vehicles if v['id'] != vehicle_id]
    flash("Vehicle deleted successfully!")
    return redirect(url_for('admin'))

@app.route('/delete_booking/<int:booking_id>')
def delete_booking(booking_id):
    global bookings
    bookings = [b for b in bookings if b.get('id') != booking_id]
    flash("Booking deleted (if it existed).")
    if 'admin' in session:
        return redirect(url_for('admin'))
    return redirect(url_for('profile'))

# ---- Search with XSS vulnerability ----
@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query', '')

    filtered_vehicles = vehicles
    if query:
        filtered_vehicles = [
            v for v in vehicles
            if query.lower() in v['name'].lower() or query.lower() in v['description'].lower()
        ]

    special_message = ""
    if re.search(r'<\s*script.*?>', query, re.IGNORECASE):
        special_message = Markup("<script>alert('XSS! FLAG: THM{reflected_xss_success}');</script>")
        
    return render_template('search.html', vehicles=filtered_vehicles, query=query, special_message=special_message)

# -------------------------
# Contact endpoint (vulnerable to SQLi) - multiple injections accepted
# -------------------------
@app.route('/contact', methods=['POST'])
def contact():
    """
    Vulnerable contact form: builds SQL-like string unsafely and detects multiple SQLi payload patterns.
    Returns the index.html with a contact_flag if a pattern matches.
    """
    name = request.form.get('name', '')
    email = request.form.get('email', '')
    message = request.form.get('message', '')

    # Simulate an unsafe insert (for debug/CTF)
    simulated_query = f"INSERT INTO contacts (name, email, message) VALUES ('{name}', '{email}', '{message}')"
    print("Simulated SQL query (Contact):", simulated_query)

    contact_flag = None

    # Patterns and associated flags (more than one injection type)
    patterns_to_keys = [
        (r"'[\s]*or[\s]*'1'='1", "or_single"),      # ' OR '1'='1
        (r"\"[\s]*or[\s]*\"1\"=\"1", "or_double"),  # " OR "1"="1
        (r"\bor\s+1\s*=\s*1\b", "or_1eq1"),         # OR 1=1 (word boundary)
    ]

    # Check both email and message fields for payloads (so attacker can put injection in either)
    combined_check = f"{email} {message}"

    for patt, key in patterns_to_keys:
        if re.search(patt, combined_check, re.IGNORECASE):
            contact_flag = CONTACT_FLAGS.get(key, "THM{contact_sqli_success}")
            break

    # Re-render index with contact_flag (so flag appears on same page)
    return render_template('index.html', contact_flag=contact_flag)

if __name__ == '__main__':
    app.run(debug=False)
