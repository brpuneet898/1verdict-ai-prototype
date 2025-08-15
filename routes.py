import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from models import User, db
# Import all our logic functions
from logics import summarize_text, review_key_clauses, query_document

main = Blueprint('main', __name__)

ALLOWED_EXTENSIONS = {'pdf', 'docx'}

def allowed_file(filename):
    """Checks if the uploaded file has an allowed extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@main.route("/")
def index():
    return render_template("index.html")

@main.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered. Please log in.', 'danger')
            return redirect(url_for('main.register'))
        hashed_password = generate_password_hash(password)
        new_user = User(name=name, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('main.login'))
    return render_template('register.html')

@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['user_name'] = user.name
            session.pop('filepath', None)
            session.pop('filename', None)
            session.pop('chat_history', None)
            flash('Login successful!', 'success')
            return redirect(url_for('main.dashboard'))
        else:
            flash('Invalid email or password.', 'danger')
            return redirect(url_for('main.login'))
    return render_template('login.html')

@main.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        flash('Please log in to access the dashboard.', 'warning')
        return redirect(url_for('main.login'))
    
    summary = None
    clauses = None
    show_chat = request.args.get('view') == 'chat'
    
    if request.method == 'POST':
        action = request.form.get('action')
        file = request.files.get('file')

        if file and file.filename:
            if allowed_file(file.filename):
                if 'filepath' in session and os.path.exists(session['filepath']):
                    os.remove(session['filepath'])
                filename = secure_filename(file.filename)
                filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], f"{session['user_id']}_{filename}")
                file.save(filepath)
                session['filepath'] = filepath
                session['filename'] = filename
                session['chat_history'] = []
                flash(f"File '{filename}' uploaded successfully.", 'success')
            else:
                flash('Invalid file type. Please upload a .pdf or .docx file.', 'danger')
            return redirect(url_for('main.dashboard'))
        
        if 'filepath' in session and os.path.exists(session['filepath']):
            filepath = session['filepath']
            llm = current_app.llm
            try:
                if action == 'summarize':
                    summary = summarize_text(filepath, llm)
                elif action == 'review':
                    clauses = review_key_clauses(filepath, llm)
            except Exception as e:
                flash(f'An error occurred: {e}', 'danger')
                print(f"Error during processing: {e}")
        elif action:
            flash('No file has been uploaded. Please choose a file first.', 'warning')

    return render_template('dashboard.html', 
                           user_name=session.get('user_name'), 
                           summary=summary, 
                           clauses=clauses,
                           filename=session.get('filename'),
                           chat_history=session.get('chat_history', []),
                           show_chat=show_chat)

# --- NEW ASYNCHRONOUS ROUTE FOR CHAT QUERIES ---
@main.route('/query', methods=['POST'])
def query():
    if 'user_id' not in session or 'filepath' not in session:
        return jsonify({'error': 'Authentication or file missing'}), 400

    question = request.json.get('question')
    filepath = session['filepath']
    llm = current_app.llm

    if not question or not os.path.exists(filepath):
        return jsonify({'error': 'Invalid request'}), 400

    try:
        answer = query_document(filepath, llm, question)
        # We still save the history to the session
        if 'chat_history' not in session:
            session['chat_history'] = []
        session['chat_history'].append({'role': 'user', 'text': question})
        session['chat_history'].append({'role': 'ai', 'text': answer})
        session.modified = True
        # Return only the answer as JSON
        return jsonify({'answer': answer})
    except Exception as e:
        print(f"Error during query: {e}")
        return jsonify({'error': str(e)}), 500


@main.route('/remove_file')
def remove_file():
    if 'user_id' not in session:
        return redirect(url_for('main.login'))

    filepath = session.pop('filepath', None)
    session.pop('filename', None)
    session.pop('chat_history', None)

    if filepath and os.path.exists(filepath):
        os.remove(filepath)
        flash('File removed successfully.', 'info')
    
    return redirect(url_for('main.dashboard'))

@main.route('/logout')
def logout():
    filepath = session.pop('filepath', None)
    if filepath and os.path.exists(filepath):
        os.remove(filepath)
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.login'))
