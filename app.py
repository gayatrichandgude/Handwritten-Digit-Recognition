import os
import csv
import zipfile
import io
import base64
import secrets
import sqlite3
import numpy as np
from PIL import Image
from flask import flash
from datetime import datetime
from flask import make_response
from reportlab.lib import colors
from backend.db import get_db, init_db
from werkzeug.utils import secure_filename
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, Paragraph
from werkzeug.security import check_password_hash, generate_password_hash
from backend.auth import register_user, login_user, change_user_password, delete_user_account
from backend.predict import predict_digit, predict_digit_from_canvas, predict_digit_from_voice
from flask import Flask, render_template, request, redirect, session, jsonify, flash, Response, send_file, url_for

# Ensure 'profile_pic' column exists
def ensure_profile_pic_column():
    db = get_db()
    cursor = db.cursor()
    # Check if column exists
    cursor.execute("PRAGMA table_info(users)")
    columns = [info[1] for info in cursor.fetchall()]
    if 'profile_pic' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN profile_pic TEXT")
        db.commit()

# Call this once when app starts
ensure_profile_pic_column()

app = Flask(__name__)
app.config.from_object('config.Config')

# Initialize database on startup
init_db()

UPLOAD_FOLDER = app.config['UPLOAD_FOLDER']
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ------------------- CACHE PREVENTION FOR AUTHENTICATED PAGES -------------------
@app.after_request
def prevent_cache_for_authenticated_pages(response):
    """
    Prevent caching of authenticated pages to force re-authentication on logout.
    This ensures that when a user logs out, the back button won't show cached
    versions of protected pages with sensitive data.
    """
    # Check if user or admin is logged in
    is_user_authenticated = 'user_id' in session
    is_admin_authenticated = 'admin_username' in session
    
    # Only prevent caching for authenticated sessions
    if is_user_authenticated or is_admin_authenticated:
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0, private'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    
    return response

# ------------------- HOME -------------------
@app.route('/')
def home():
    return render_template("home.html")

# ------------------- USER AUTH -------------------
@app.route('/login_page')
def login_page():
    return render_template("user/login.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE email=?", (email,))
        user = cursor.fetchone()

        # ✅ Use check_password_hash for login
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            flash("Login successful!", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid email or password!", "error")
            return redirect(url_for('login'))

    return render_template("user/login.html")

# ----------Forgot password page----------
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE email=?", (email,))
        user = cursor.fetchone()

        if not user:
            flash("Email not found!", "error")
            return redirect('/forgot_password')

        # Generate reset token
        token = secrets.token_urlsafe(16)
        cursor.execute("UPDATE users SET reset_token=? WHERE email=?", (token, email))
        db.commit()

        reset_link = f"http://localhost:5000/reset_password/{token}"
        print("Reset link:", reset_link)  # In real app, send via email
        flash(f"Reset link sent! Check console or email: {reset_link}", "success")
        return redirect('/login')

    return render_template("user/forgot_password.html")

# -------------------- Forgot Password: generate token -----------
@app.route('/reset_password', methods=['POST'])
def forgot_password_request():
    email = request.form.get('email')
    if not email:
        return "Email required", 400

    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id FROM users WHERE email=?", (email,))
    user = cursor.fetchone()

    if not user:
        return "Email not found", 404

    import secrets
    token = secrets.token_urlsafe(16)
    cursor.execute("UPDATE users SET reset_token=? WHERE id=?", (token, user['id']))
    db.commit()

    reset_link = f"http://localhost:5000/reset_password/{token}"
    print("Reset link:", reset_link)  # Send via email in real app

    return f"Reset link sent! Check console or email: {reset_link}"

# ---------------------- Reset Password Form -----------------
@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id FROM users WHERE reset_token=?", (token,))
    user = cursor.fetchone()
    
    if not user:
        return render_template("user/reset_password.html", token=None, message="✅ Password reset successful! Redirecting to login...", redirect_login=True)

    message = None

    if request.method == 'POST':
        new = request.form.get('new_password')
        confirm = request.form.get('confirm_password')
        
        if new != confirm:
            message = "❌ Passwords do not match!"
        else:
            from werkzeug.security import generate_password_hash
            hashed = generate_password_hash(new)
            cursor.execute(
                "UPDATE users SET password=?, reset_token=NULL WHERE id=?",
                (hashed, user['id'])
            )
            db.commit()
            message = "✅ Password reset successful! Redirecting to login..."

            # After successful reset, we can pass a flag to template
            return render_template("user/reset_password.html", token=None, message=message, redirect_login=True)

    return render_template("user/reset_password.html", token=token, message=message)

#----------------------Register page --------------------
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash("Passwords do not match!", "error")
            return redirect('/register')

        file = request.files.get('profile_pic')
        filename = None

        if file and file.filename != "":
            from werkzeug.utils import secure_filename
            import os, time

            upload_path = os.path.join('static', 'profile_pics')
            os.makedirs(upload_path, exist_ok=True)

            filename = secure_filename(file.filename)
            name_part, ext = os.path.splitext(filename)
            filename = f"{name_part}_{int(time.time())}{ext}"
            file.save(os.path.join(upload_path, filename))

        db = get_db()
        cursor = db.cursor()

        cursor.execute("SELECT * FROM users WHERE email=?", (email,))
        if cursor.fetchone():
            flash("Email already exists!", "error")
            return redirect('/register')

        hashed_password = generate_password_hash(password)

        cursor.execute(
         "INSERT INTO users (name,email,password,profile_pic) VALUES (?,?,?,?)",
         (name, email, hashed_password, filename)
         )
        db.commit()

        flash("Registration successful!", "success")
        return redirect('/register')

    return render_template("user/register.html")

@app.route('/get_user_photo')
def get_user_photo():
    email = request.args.get('email')

    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT profile_pic FROM users WHERE email=?", (email,))
    user = cursor.fetchone()

    if user:
        return jsonify({'photo': user['profile_pic']})
    else:
        return jsonify({'photo': None})

# ------------------- USER DASHBOARD & PREDICTIONS -------------------
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Correct redirect

    db = get_db()
    cursor = db.cursor()
    
    cursor.execute("SELECT id, name, email, profile_pic FROM users WHERE id = ?", (session['user_id'],))
    row = cursor.fetchone()

    if row is None:
        flash("User not found!", "error")
        return redirect(url_for('login'))

    # Convert Row to dict for dot notation in Jinja2
    user = {
        'id': row['id'],
        'name': row['name'],
        'email': row['email'],
        'profile_pic': row['profile_pic'] if row['profile_pic'] else 'default.png'
    }

    return render_template("user/dashboard.html", user=user)

# ------------------- PREDICTION PAGES -------------------
@app.route("/predict_page")
def predict_page():
    if 'user_id' not in session:
        return redirect('/login_page')
    return render_template("user/predict.html", user={'name': session.get('user_name')})


@app.route('/predict', methods=['POST'])
def predict():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    if 'image' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['image']
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    # Save file
    filename = secure_filename(file.filename)
    path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(path)

    # Prediction
    digit, confidence = predict_digit(path)

    # Store relative path in DB
    relative_path = f"uploads/{filename}"
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO predictions (user_id, prediction_type, image_path, predicted_digit, confidence) VALUES (?, ?, ?, ?, ?)",
        (session['user_id'], 'upload', relative_path, int(digit), float(confidence))
    )
    db.commit()

    return jsonify({"digit": digit, "confidence": confidence, "image": relative_path})

@app.route("/predict_canvas", methods=["POST"])
def predict_canvas():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    result = predict_digit_from_canvas(data["image"])

    # Store relative path
    relative_path = f"uploads/{result['image_path']}"

    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO predictions (user_id, prediction_type, image_path, predicted_digit, confidence) VALUES (?, ?, ?, ?, ?)",
        (session['user_id'], 'draw', relative_path, int(result['digit']), float(result['confidence']))
    )
    db.commit()

    # Return result including relative path
    return jsonify({
        "digit": result['digit'],
        "confidence": result['confidence'],
        "image_path": relative_path
    })


@app.route('/predict_voice', methods=['POST'])
def predict_voice():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    if 'voice' not in request.files:
        return jsonify({"error": "No voice file"}), 400

    file = request.files['voice']
    filename = secure_filename(file.filename)

    # Ensure filename ends with .wav
    if not filename.endswith('.wav'):
        filename = filename.rsplit('.', 1)[0] + f"_{session['user_id']}.wav"

    path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(path)

    print(f"[INFO] Saved voice file: {path}")

    digit, confidence = predict_digit_from_voice(path)

    relative_path = f"uploads/{filename}"
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO predictions (user_id, prediction_type, image_path, predicted_digit, confidence) VALUES (?, ?, ?, ?, ?)",
        (session['user_id'], 'voice', relative_path, int(digit), float(confidence))
    )
    db.commit()

    return jsonify({"digit": digit, "confidence": confidence, "audio": relative_path})

# ------------------- USER HISTORY & ANALYTICS -------------------
@app.route('/history')
def history():
    if 'user_id' not in session:
        return redirect('/login_page')

    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM predictions WHERE user_id = ? ORDER BY id DESC", (session['user_id'],))
    data = cursor.fetchall()
    return render_template("user/history.html", data=data)


# ------------------- DOWNLOAD -------------------
@app.route('/download/<path:filename>')
def download(filename):
    if 'user_id' not in session:
        return redirect('/login_page')

    import os
    from flask import send_file

    # 🔥 फक्त filename
    filename = filename.split('/')[-1]

    upload_folder = os.path.join('static', 'uploads')

    # 🔴 1. Direct file check
    file_path = os.path.join(upload_folder, filename)
    print("Trying:", file_path)

    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)

    # 🔴 2. Voice case handle
    name, ext = os.path.splitext(filename)
    converted_filename = name + "_converted.wav"
    converted_path = os.path.join(upload_folder, converted_filename)

    print("Trying converted:", converted_path)

    if os.path.exists(converted_path):
        return send_file(converted_path, as_attachment=True)

    # ❌ not found
    return f"File not found: {file_path}", 404
# ------------------- DELETE -------------------
@app.route('/delete/<int:id>')
def delete(id):
    if 'user_id' not in session:
        return redirect('/login_page')

    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM predictions WHERE id = ? AND user_id = ?", (id, session['user_id']))
    prediction = cursor.fetchone()
    if not prediction:
        return "Prediction not found or access denied", 404

    # Delete file from disk
    if prediction['image_path']:
        try:
            file_path = os.path.join('static', prediction['image_path'])
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print("Error deleting file:", e)

    cursor.execute("DELETE FROM predictions WHERE id = ?", (id,))
    db.commit()
    return redirect('/history')

#------------Analytics Page --------------
@app.route('/analytics')
def analytics():
    if 'user_id' not in session:
        return redirect('/login_page')
    db = get_db()
    cursor = db.cursor()
    
    # 🔹 Get filters
    filter_type = request.args.get('type', '')
    start_date = request.args.get('start', '')
    end_date = request.args.get('end', '')
    
    # 🔹 Base queries
    base_params = [session['user_id']]
    count_params = [session['user_id']]
    
    type_filter = ""
    if filter_type and filter_type != 'all':
        db_type = 'upload' if filter_type == 'image' else filter_type
        type_filter = " AND prediction_type = ?"
        base_params.append(db_type)
        count_params.append(db_type)
    
    date_filter = ""
    if start_date:
        date_filter += " AND DATE(created_at) >= ?"
        base_params.append(start_date)
        count_params.append(start_date)
    if end_date:
        date_filter += " AND DATE(created_at) <= ?"
        base_params.append(end_date)
        count_params.append(end_date)
    
    # 🔹 Total predictions
    count_query = "SELECT COUNT(*) as total FROM predictions WHERE user_id = ?" + type_filter + date_filter
    cursor.execute(count_query, tuple(count_params))
    total = cursor.fetchone()['total']
    
    # 🔹 Digit statistics for charts
    digit_query = "SELECT predicted_digit, COUNT(*) AS count FROM predictions WHERE user_id = ?" + type_filter + date_filter + " GROUP BY predicted_digit"
    cursor.execute(digit_query, tuple(base_params))
    rows = cursor.fetchall()
    
    digits = [str(r['predicted_digit']) for r in rows]
    counts = [r['count'] for r in rows]
    
    most_digit = digits[counts.index(max(counts))] if counts else 0
    accuracy = round((sum(counts)/total)*100, 2) if total > 0 else 0
    
    return render_template("user/analytics.html",
                           total=total,
                           most_digit=most_digit,
                           accuracy=accuracy,
                           digits=digits,
                           counts=counts)
    
#----------top Predictions--------------
@app.route('/top_predictions')
def top_predictions():
    user_id = session.get('user_id')  # current user
    if not user_id:
        return redirect('/login_page')

    type_filter = request.args.get('type')
    digit_filter = request.args.get('digit')
    limit = int(request.args.get('limit', 5))

    db = get_db()
    cursor = db.cursor()

    # 🔹 Top confidence (filtered)
    query = "SELECT * FROM predictions WHERE user_id=?"
    params = [user_id]

    if type_filter:
        query += " AND prediction_type=?"
        params.append(type_filter)
    if digit_filter:
        query += " AND predicted_digit=?"
        params.append(digit_filter)

    query += " ORDER BY confidence DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    top_conf = cursor.fetchall()

    # 🔹 Most frequent digit (current user / filtered)
    freq_query = "SELECT predicted_digit, COUNT(*) as count FROM predictions WHERE user_id=?"
    freq_params = [user_id]

    if type_filter:
        freq_query += " AND prediction_type=?"
        freq_params.append(type_filter)
    if digit_filter:
        freq_query += " AND predicted_digit=?"
        freq_params.append(digit_filter)

    freq_query += " GROUP BY predicted_digit ORDER BY count DESC LIMIT 1"
    cursor.execute(freq_query, freq_params)
    top_digits = cursor.fetchall()

    return render_template("user/top_predictions.html",
                           top_conf=top_conf,
                           top_digits=top_digits)
    
# ------------------- USER PROFILE, CHANGE PASSWORD, DELETE ACCOUNT -------------------
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect('/login_page')
    db = get_db()
    cursor = db.cursor()
    # Profile page is GET only now - name cannot be edited
    cursor.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],))
    user = cursor.fetchone()
    cursor.execute("SELECT COUNT(*) as total FROM predictions WHERE user_id = ?", (session['user_id'],))
    total = cursor.fetchone()['total']
    return render_template("user/profile.html", user=user, total=total)

@app.route('/change_password', methods=['POST'])
def change_password():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    old = request.form['old_password']
    new = request.form['new_password']
    confirm = request.form['confirm_password']

    if new != confirm:
        return jsonify({"error": "New passwords do not match"}), 400

    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT password FROM users WHERE id=?", (session['user_id'],))
    user = cursor.fetchone()

    if not user or not check_password_hash(user['password'], old):
        return jsonify({"error": "Old password is incorrect"}), 400

    hashed = generate_password_hash(new)
    cursor.execute("UPDATE users SET password=? WHERE id=?", (hashed, session['user_id']))
    db.commit()

    return jsonify({"success": True, "message": "Password changed successfully!"})

@app.route('/delete_account', methods=['POST'])
def delete_account():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    password = (data.get('password') if data else "").strip()  # remove extra spaces

    if not password:
        return jsonify({"error": "Password required"}), 400

    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT password FROM users WHERE id=?", (session['user_id'],))
    user = cursor.fetchone()

    if not user:
        return jsonify({"error": "User not found"}), 404

    # SQLite sometimes returns bytes for password
    hashed_password = user['password']
    if isinstance(hashed_password, bytes):
        hashed_password = hashed_password.decode('utf-8')

    # ✅ Only check password for account deletion
    if not check_password_hash(hashed_password, password):
        return jsonify({"error": "Incorrect password"}), 401

    # Delete predictions + user
    cursor.execute("DELETE FROM predictions WHERE user_id=?", (session['user_id'],))
    cursor.execute("DELETE FROM users WHERE id=?", (session['user_id'],))
    db.commit()

    session.clear()
    return jsonify({"success": True, "message": "Account deleted successfully!"})

# ------------------- DOWNLOAD ROUTES (unchanged logic, just SQLite) -------------------
@app.route('/download')
def download_page():
    if 'user_id' not in session:
        return redirect('/login_page')
    return render_template("user/download.html")

@app.route('/download/<path:filepath>')
def download_file(filepath):
    """Download a specific prediction image file"""
    if 'user_id' not in session:
        return redirect('/login_page')
    
    try:
        # Verify file exists and user owns it
        db = get_db()
        cursor = db.cursor()
        
        # Check if prediction belongs to this user
        cursor.execute(
            "SELECT * FROM predictions WHERE user_id = ? AND image_path = ?",
            (session['user_id'], filepath)
        )
        prediction = cursor.fetchone()
        
        if not prediction:
            return "File not found or access denied", 404
        
        # Check if file exists
        import os
        if not os.path.exists(filepath):
            return "File not found", 404
        
        # Send file
        return send_file(filepath, as_attachment=True)
    except Exception as e:
        return str(e), 400

#--------------reports---------------
@app.route('/reports')
def reports_page():
    """User reports page"""
    if 'user_id' not in session:
        return redirect('/login_page')
    
    db = get_db()
    cursor = db.cursor()
    
    # 🔹 Get prediction statistics
    cursor.execute(
        "SELECT COUNT(*), AVG(confidence) FROM predictions WHERE user_id = ?",
        (session['user_id'],)
    )
    stats = cursor.fetchone()

    total = stats[0] if stats[0] else 0
    avg_confidence = round(stats[1]) if stats[1] else 0

    # 🔹 Get top predicted digit (FIXED)
    from collections import Counter

    cursor.execute(
        "SELECT predicted_digit FROM predictions WHERE user_id = ?",
        (session['user_id'],)
    )
    rows = cursor.fetchall()

    digits = []
    for r in rows:
        if r[0] is not None:
            digits.append(int(r[0]))

    if digits:
        top_digit = Counter(digits).most_common(1)[0][0]
    else:
        top_digit = "N/A"

    print("DEBUG DIGITS:", digits)
    print("TOP DIGIT:", top_digit)

    # 🔹 Accuracy
    accuracy = avg_confidence

    # 🔹 Get predictions per type
    cursor.execute(
        "SELECT prediction_type, COUNT(*) FROM predictions WHERE user_id = ? GROUP BY prediction_type",
        (session['user_id'],)
    )
    type_data = cursor.fetchall()

    type_counts = dict(type_data) if type_data else {}

    draw_count = type_counts.get('draw', 0)
    image_count = type_counts.get('upload', 0)
    voice_count = type_counts.get('voice', 0)

    return render_template(
        "user/reports.html",
        total=total,
        avg_confidence=avg_confidence,
        top_digit=top_digit,
        accuracy=accuracy,
        draw_count=draw_count,
        image_count=image_count,
        voice_count=voice_count
    )
@app.route('/download_csv')
def download_csv():
    """Download all user predictions as CSV"""
    if 'user_id' not in session:
        return redirect('/login_page')
    
    db = get_db()
    cursor = db.cursor()
    
    # Get all predictions for user
    cursor.execute(
        "SELECT id, predicted_digit, confidence, prediction_type, created_at FROM predictions WHERE user_id = ? ORDER BY created_at DESC",
        (session['user_id'],)
    )
    predictions = cursor.fetchall()
    
    # Create CSV
    output = io.StringIO()
    output.write("ID,Digit,Confidence,Type,Date\n")
    for pred in predictions:
        output.write(f"{pred[0]},{pred[1]},{pred[2]:.2f},{pred[3]},{pred[4]}\n")
    
    # Return as download
    output.seek(0)
    return Response(output.getvalue(), mimetype="text/csv", 
                   headers={"Content-Disposition": "attachment;filename=predictions.csv"})

@app.route('/download_filtered', methods=['POST'])
def download_filtered():
    """Download predictions filtered by date range as CSV"""
    if 'user_id' not in session:
        return redirect('/login_page')
    
    start_date = request.form.get('start')
    end_date = request.form.get('end')
    
    db = get_db()
    cursor = db.cursor()
    
    # Get filtered predictions
    cursor.execute(
        "SELECT id, predicted_digit, confidence, prediction_type, created_at FROM predictions WHERE user_id = ? AND DATE(created_at) BETWEEN ? AND ? ORDER BY created_at DESC",
        (session['user_id'], start_date, end_date)
    )
    predictions = cursor.fetchall()
    
    # Create CSV
    output = io.StringIO()
    output.write(f"Predictions from {start_date} to {end_date}\n")
    output.write("ID,Digit,Confidence,Type,Date\n")
    for pred in predictions:
        output.write(f"{pred[0]},{pred[1]},{pred[2]:.2f},{pred[3]},{pred[4]}\n")
    
    output.seek(0)
    return Response(output.getvalue(), mimetype="text/csv",
                   headers={"Content-Disposition": f"attachment;filename=predictions_{start_date}_to_{end_date}.csv"})

@app.route('/download_filtered_type', methods=['POST'])
def download_filtered_type():
    """Download predictions filtered by type and/or digit as CSV"""
    if 'user_id' not in session:
        return redirect('/login_page')
    
    pred_type = request.form.get('type')
    digit = request.form.get('digit')
    
    db = get_db()
    cursor = db.cursor()
    
    # Build query
    if pred_type == 'all' and not digit:
        query = "SELECT id, predicted_digit, confidence, prediction_type, created_at FROM predictions WHERE user_id = ? ORDER BY created_at DESC"
        params = (session['user_id'],)
    elif pred_type != 'all' and digit:
        # Map 'image' to 'upload' for database
        db_type = 'upload' if pred_type == 'image' else pred_type
        query = "SELECT id, predicted_digit, confidence, prediction_type, created_at FROM predictions WHERE user_id = ? AND prediction_type = ? AND predicted_digit = ? ORDER BY created_at DESC"
        params = (session['user_id'], db_type, int(digit))
    elif pred_type != 'all':
        db_type = 'upload' if pred_type == 'image' else pred_type
        query = "SELECT id, predicted_digit, confidence, prediction_type, created_at FROM predictions WHERE user_id = ? AND prediction_type = ? ORDER BY created_at DESC"
        params = (session['user_id'], db_type)
    else:
        query = "SELECT id, predicted_digit, confidence, prediction_type, created_at FROM predictions WHERE user_id = ? AND predicted_digit = ? ORDER BY created_at DESC"
        params = (session['user_id'], int(digit))
    
    cursor.execute(query, params)
    predictions = cursor.fetchall()
    
    # Create CSV
    output = io.StringIO()
    output.write(f"Filtered Predictions - Type: {pred_type}, Digit: {digit if digit else 'All'}\n")
    output.write("ID,Digit,Confidence,Type,Date\n")
    for pred in predictions:
        output.write(f"{pred[0]},{pred[1]},{pred[2]:.2f},{pred[3]},{pred[4]}\n")
    
    output.seek(0)
    filename = f"predictions_filtered_{pred_type}_{digit}.csv" if digit else f"predictions_filtered_{pred_type}.csv"
    return Response(output.getvalue(), mimetype="text/csv",
                   headers={"Content-Disposition": f"attachment;filename={filename}"})

@app.route('/download/canvas_image/<int:prediction_id>')
def download_canvas_image(prediction_id):
    """Download a canvas prediction as an image"""
    if 'user_id' not in session:
        return redirect('/login_page')
    
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Get prediction
        cursor.execute(
            "SELECT * FROM predictions WHERE id = ? AND user_id = ? AND prediction_type = 'draw'",
            (prediction_id, session['user_id'])
        )
        prediction = cursor.fetchone()
        
        if not prediction:
            return "Canvas image not found", 404
        
        # Create a simple image file with the prediction info
        from PIL import Image, ImageDraw
        
        # Create placeholder image with prediction info
        img = Image.new('RGB', (400, 300), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        text = f"Digit Prediction: {prediction['predicted_digit']}\nConfidence: {prediction['confidence']}%\nDate: {prediction['created_at']}"
        draw.text((50, 50), text, fill=(0, 0, 0))
        
        # Save to bytes
        img_io = io.BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)
        
        return send_file(img_io, mimetype='image/png',
                        as_attachment=True, download_name=f'canvas_prediction_{prediction_id}.png')
    
    except Exception as e:
        return str(e), 400

@app.route('/download_images')
def download_images():
    """Download all user's prediction images as ZIP"""
    if 'user_id' not in session:
        return redirect('/login_page')
    
    db = get_db()
    cursor = db.cursor()
    
    # Get all predictions for user
    cursor.execute(
        "SELECT image_path FROM predictions WHERE user_id = ?",
        (session['user_id'],)
    )
    predictions = cursor.fetchall()
    
    if not predictions:
        return "No predictions found", 404
    
    # Create ZIP file
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for pred in predictions:
            image_path = pred[0]
            if os.path.exists(image_path):
                # Get just the filename for the zip
                filename = os.path.basename(image_path)
                zf.write(image_path, arcname=filename)
    
    memory_file.seek(0)
    return send_file(memory_file, mimetype='application/zip',
                    as_attachment=True, download_name='predictions_images.zip')

@app.route('/download_report')
def download_report():
    """Download user report as PDF"""
    if 'user_id' not in session:
        return redirect('/login_page')
    
    db = get_db()
    cursor = db.cursor()
    
    # Get user info
    cursor.execute("SELECT name, email FROM users WHERE id = ?", (session['user_id'],))
    user = cursor.fetchone()
    
    # Get prediction statistics
    cursor.execute(
        "SELECT COUNT(*) as total, AVG(confidence) as avg_conf FROM predictions WHERE user_id = ?",
        (session['user_id'],)
    )
    stats = cursor.fetchone()
    
    # Get predictions by digit
    cursor.execute(
        "SELECT predicted_digit, COUNT(*) as count FROM predictions WHERE user_id = ? GROUP BY predicted_digit ORDER BY predicted_digit",
        (session['user_id'],)
    )
    digit_stats = cursor.fetchall()
    
    # Get predictions by type
    cursor.execute(
        "SELECT prediction_type, COUNT(*) as count FROM predictions WHERE user_id = ? GROUP BY prediction_type",
        (session['user_id'],)
    )
    type_stats = cursor.fetchall()
    
    # Create PDF report
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, title="Prediction Report", pagesize=(600, 800))
    elements = []
    
    # Title
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import Paragraph, Spacer, PageBreak
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(name='CustomTitle', parent=styles['Heading1'], fontSize=24, textColor=colors.HexColor('#22c55e'), alignment=1)
    
    elements.append(Paragraph("Digit Recognition Report", title_style))
    elements.append(Spacer(1, 12))
    
    # User info
    elements.append(Paragraph(f"<b>User:</b> {user[0]}", styles['Normal']))
    elements.append(Paragraph(f"<b>Email:</b> {user[1]}", styles['Normal']))
    elements.append(Spacer(1, 12))
    
    # Statistics
    elements.append(Paragraph(f"<b>Total Predictions:</b> {stats[0]}", styles['Normal']))
    elements.append(Paragraph(f"<b>Average Confidence:</b> {stats[1]:.2f}%" if stats[1] else "N/A", styles['Normal']))
    elements.append(Spacer(1, 12))
    
    # Digit breakdown table
    elements.append(Paragraph("<b>Predictions by Digit</b>", styles['Heading2']))
    digit_data = [['Digit', 'Count']] + [[str(d[0]), str(d[1])] for d in digit_stats]
    digit_table = Table(digit_data)
    digit_table.setStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#22c55e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey)
    ])
    elements.append(digit_table)
    elements.append(Spacer(1, 12))
    
    # Type breakdown table
    elements.append(Paragraph("<b>Predictions by Type</b>", styles['Heading2']))
    type_data = [['Type', 'Count']] + [[d[0], str(d[1])] for d in type_stats]
    type_table = Table(type_data)
    type_table.setStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#22c55e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey)
    ])
    elements.append(type_table)
    
    # Build PDF
    doc.build(elements)
    pdf_buffer.seek(0)
    
    return send_file(pdf_buffer, mimetype='application/pdf',
                    as_attachment=True, download_name='prediction_report.pdf')

# ------------------- ADMIN ROUTES (with hashed password) -------------------
@app.route('/admin')
def admin_login():
    return render_template("admin/admin_login.html", error=None)

@app.route('/admin_login', methods=['POST'])
def admin_login_post():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM admin WHERE username = ?", (request.form['username'],))
    admin = cursor.fetchone()
    if admin and check_password_hash(admin['password'], request.form['password']):
        session['admin'] = True
        session['admin_username'] = admin['username']
        return redirect('/admin_dashboard')
    return render_template("admin/admin_login.html", error="Invalid Credentials")

@app.route('/admin/change_password', methods=['POST'])
def admin_change_password():
    if 'admin_username' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    old = request.form['old_password']
    new = request.form['new_password']
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT password FROM admin WHERE username = ?", (session['admin_username'],))
    admin = cursor.fetchone()
    if not check_password_hash(admin['password'], old):
        return jsonify({"error": "Old password incorrect"}), 400
    hashed_new = generate_password_hash(new)
    cursor.execute("UPDATE admin SET password = ? WHERE username = ?", (hashed_new, session['admin_username']))
    db.commit()
    return jsonify({"success": True})

@app.route('/admin_logout')
def admin_logout():
    session.pop('admin_username', None)
    session.pop('admin', None)
    return redirect('/admin')


# ------------------- ADMIN DASHBOARD & MANAGEMENT -------------------
@app.route("/admin_dashboard")
def admin_dashboard():
    if 'admin_username' not in session:
        return redirect('/admin')

    db = get_db()
    cursor = db.cursor()

    # Users
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()

    # Predictions with user name
    cursor.execute("""
        SELECT p.*, u.name AS user_name
        FROM predictions p
        JOIN users u ON p.user_id = u.id
        ORDER BY p.id ASC
    """)
    predictions = cursor.fetchall()

    # Totals
    total_users = len(users)
    total_predictions = len(predictions)

     # Most predicted digit (based on current predictions)
    cursor.execute("""
        SELECT predicted_digit, COUNT(*) as count
        FROM predictions p
        JOIN users u ON p.user_id = u.id
        WHERE predicted_digit IS NOT NULL
        GROUP BY predicted_digit
        ORDER BY count DESC
        LIMIT 1
    """)
    res = cursor.fetchone()
    most_digit = int(res['predicted_digit']) if res else "-"

    # Highest confidence
    cursor.execute("SELECT MAX(confidence) as max_conf FROM predictions")
    res2 = cursor.fetchone()
    highest_pred = res2['max_conf'] if res2 and res2['max_conf'] else 0

    # Graph data
    cursor.execute("""
        SELECT predicted_digit, COUNT(*) as count
        FROM predictions
        GROUP BY predicted_digit
        ORDER BY predicted_digit ASC
    """)
    data = cursor.fetchall()
    digits = [str(d['predicted_digit']) for d in data]
    counts = [d['count'] for d in data]

    cursor.close()
    db.close()

    return render_template(
        "admin/admin_dashboard.html",
        users=users,
        predictions=predictions,
        total_users=total_users,
        total_predictions=total_predictions,
        most_digit=most_digit,
        highest_pred=highest_pred,
        digits=digits,
        counts=counts
    )
# --- Additional Admin Routes for Sidebar Navigation ---
@app.route('/admin/users')
def admin_users():
    if 'admin_username' not in session:
        return redirect('/admin')
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    return render_template("admin/users.html", users=users)

@app.route('/admin/analytics')
def admin_analytics():
    if 'admin_username' not in session:
        return redirect('/admin')

    db = get_db()
    cursor = db.cursor()

    # Total users
    cursor.execute("SELECT COUNT(*) as total_users FROM users")
    total_users = cursor.fetchone()['total_users']

    # Total predictions — only active predictions
    cursor.execute("""
        SELECT COUNT(*) as total_predictions
        FROM predictions p
        JOIN users u ON p.user_id = u.id
    """)
    total_predictions = cursor.fetchone()['total_predictions']

    # Most predicted digit (based on current predictions)
    cursor.execute("""
        SELECT predicted_digit, COUNT(*) as count
        FROM predictions p
        JOIN users u ON p.user_id = u.id
        WHERE predicted_digit IS NOT NULL
        GROUP BY predicted_digit
        ORDER BY count DESC
        LIMIT 1
    """)
    res = cursor.fetchone()
    most_digit = int(res['predicted_digit']) if res else "-"

    # Highest confidence
    cursor.execute("SELECT MAX(confidence) as max_conf FROM predictions")
    res2 = cursor.fetchone()
    highest_conf = res2['max_conf'] if res2 and res2['max_conf'] else 0

    # Chart data
    cursor.execute("""
        SELECT predicted_digit, COUNT(*) as count
        FROM predictions p
        JOIN users u ON p.user_id = u.id
        GROUP BY predicted_digit
        ORDER BY predicted_digit ASC
    """)
    data = cursor.fetchall()
    digits = [str(d['predicted_digit']) for d in data]
    counts = [d['count'] for d in data]

    cursor.close()
    db.close()

    return render_template(
        "admin/admin_analytics.html",
        total_users=total_users,
        total_predictions=total_predictions,
        most_digit=most_digit,
        highest_conf=highest_conf,
        digits=digits,
        counts=counts
    )
@app.route('/admin/reports')
def admin_reports_list():
    if 'admin_username' not in session:
        return redirect('/admin')

    db = get_db()
    cursor = db.cursor()

    # ✅ All predictions with user name
    cursor.execute("""
        SELECT p.*, u.name AS user_name
        FROM predictions p
        JOIN users u ON p.user_id = u.id
        ORDER BY p.id ASC
    """)

    predictions = []
    for row in cursor.fetchall():
        r = dict(row)

        if 'created_at' in r and r['created_at'] and not isinstance(r['created_at'], str):
            r['created_at'] = str(r['created_at'])

        predictions.append(r)
    # =========================
    # 🔥 STATS
    # =========================
    # ✅ Total Predictions
    total_predictions = len(predictions)

    # ✅ Top Digit (FIXED)
    digit_count = {}

    for p in predictions:
        digit = p.get('predicted_digit')   # ✅ FIX
        if digit is not None:
            digit = int(digit)
            digit_count[digit] = digit_count.get(digit, 0) + 1

    if digit_count:
        top_digit = max(digit_count, key=digit_count.get)
    else:
        top_digit = "-"

    # ✅ Average Confidence
    total_conf = 0
    count_conf = 0

    for p in predictions:
        conf = p.get('confidence')
        if conf is not None:
            total_conf += float(conf)
            count_conf += 1

    avg_confidence = round(total_conf / count_conf, 2) if count_conf > 0 else 0

    # ✅ Accuracy
    accuracy = avg_confidence

    # =========================

    return render_template(
        "admin/admin_reports.html",
        predictions=predictions,
        total_predictions=total_predictions,
        top_digit=top_digit,
        avg_confidence=avg_confidence,
        accuracy=accuracy
    )
    
@app.route('/admin/download_report')
def admin_download_report():
    if 'admin_username' not in session:
        return redirect('/admin')

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT p.id, u.name, p.predicted_digit, p.confidence, p.prediction_type, p.created_at
        FROM predictions p
        JOIN users u ON p.user_id = u.id
        ORDER BY p.id DESC
    """)

    data = cursor.fetchall()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer)

    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("Admin Report", styles['Title']))

    for row in data:
        text = f"ID: {row[0]} | User: {row[1]} | Digit: {row[2]} | Confidence: {row[3]}% | Type: {row[4]}"
        elements.append(Paragraph(text, styles['Normal']))

    doc.build(elements)

    buffer.seek(0)

    return make_response(buffer.getvalue(), {
        'Content-Type': 'application/pdf',
        'Content-Disposition': 'attachment; filename=admin_report.pdf'
    })

@app.route('/admin/predictions')
def admin_predictions():
    if 'admin_username' not in session:
        return redirect('/admin')
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT p.*, u.name AS user_name
        FROM predictions p
        INNER JOIN users u ON p.user_id = u.id
        ORDER BY p.id ASC
    """)
    predictions = []
    for row in cursor.fetchall():
        r = dict(row)
        # created_at string format
        if 'created_at' in r and r['created_at']:
            if not isinstance(r['created_at'], str):
                r['created_at'] = str(r['created_at'])

        # file path for images / voice
        if r.get('prediction_type') in ['draw', 'upload'] and r.get('image_path'):
            r['file_path'] = url_for('static', filename=f'uploads/{r["image_path"]}')
        elif r.get('prediction_type') == 'voice' and r.get('image_path'):
            r['file_path'] = url_for('static', filename=f'uploads/{r["image_path"]}')
        else:
            r['file_path'] = None

        predictions.append(r)

    cursor.close()
    db.close()

    return render_template("admin/admin_predictions.html", predictions=predictions)

@app.route('/admin/settings', methods=['GET', 'POST'])
def admin_settings():
    if 'admin_username' not in session:
        return redirect('/admin')
    
    message = None
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('password')
        
        # Verify current password
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT password FROM admin WHERE username = ?", (session['admin_username'],))
        admin = cursor.fetchone()
        
        if not admin or not check_password_hash(admin['password'], current_password):
            message = "Current password is incorrect"
        elif new_password:
            # Update password
            hashed_new = generate_password_hash(new_password)
            cursor.execute("UPDATE admin SET password = ? WHERE username = ?", (hashed_new, session['admin_username']))
            db.commit()
            message = "Password updated successfully"
        else:
            message = "Please enter a new password"
    
    # Dummy admin object for template rendering
    admin = type('Admin', (), {'username': 'admin'})()
    return render_template("admin/admin_settings.html", admin=admin, message=message)

@app.route('/admin/view_user/<int:user_id>')
def view_user(user_id):
    if 'admin_username' not in session:
        return redirect('/admin')
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    cursor.execute("SELECT * FROM predictions WHERE user_id = ?", (user_id,))
    predictions = cursor.fetchall()
    return render_template("admin/view_user.html", user=user, predictions=predictions)

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
def delete_user_by_admin(user_id):
    """Admin endpoint to delete a user and all their predictions"""
    if 'admin_username' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Delete all predictions for this user first
        cursor.execute("DELETE FROM predictions WHERE user_id = ?", (user_id,))
        
        # Delete the user
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        db.commit()
        
        return jsonify({"success": True, "message": "User deleted successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# ------------------- LOGOUT -------------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)
