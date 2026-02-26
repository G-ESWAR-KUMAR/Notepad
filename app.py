import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
# from flask_session import Session
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///notepad.db')
if os.environ.get('VERCEL'):
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/notepad.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# app.config['SESSION_TYPE'] = 'filesystem'
# if os.environ.get('VERCEL'):
#     app.config['SESSION_FILE_DIR'] = '/tmp/flask_session'

db = SQLAlchemy(app)
# Session(app)

# Supabase Setup
url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")
supabase: Client = None
if url and key and "your_supabase" not in url:
    supabase = create_client(url, key)

# Models
class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=True)
    last_modified = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_synced = db.Column(db.Boolean, default=False)
    supabase_id = db.Column(db.String(100), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'last_modified': self.last_modified.isoformat(),
            'is_synced': self.is_synced
        }

with app.app_context():
    try:
        db.create_all()
    except Exception as e:
        print(f"Database creation error: {e}")

# Auth Middleware
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == os.getenv('ADMIN_USERNAME') and password == os.getenv('ADMIN_PASSWORD'):
            session['logged_in'] = True
            return redirect(url_for('index'))
        return render_template('login.html', error="Invalid credentials")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    return render_template('index.html')

# API Routes
@app.route('/api/notes', methods=['GET'])
@login_required
def get_notes():
    notes = Note.query.order_by(Note.last_modified.desc()).all()
    return jsonify([n.to_dict() for n in notes])

@app.route('/api/notes', methods=['POST'])
@login_required
def create_note():
    data = request.json
    new_note = Note(title=data.get('title', 'Untitled'), content=data.get('content', ''))
    db.session.add(new_note)
    db.session.commit()
    return jsonify(new_note.to_dict())

@app.route('/api/notes/<int:note_id>', methods=['PUT'])
@login_required
def update_note(note_id):
    note = Note.query.get_or_404(note_id)
    data = request.json
    note.title = data.get('title', note.title)
    note.content = data.get('content', note.content)
    note.is_synced = False
    db.session.commit()
    return jsonify(note.to_dict())

@app.route('/api/notes/<int:note_id>', methods=['DELETE'])
@login_required
def delete_note(note_id):
    note = Note.query.get_or_404(note_id)
    db.session.delete(note)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/sync', methods=['POST'])
@login_required
def sync():
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 400
    
    # Simple sync logic: Push local changes unsynced to Supabase
    unsynced_notes = Note.query.filter_by(is_synced=False).all()
    for note in unsynced_notes:
        try:
            data = {
                'title': note.title,
                'content': note.content,
                'last_modified': note.last_modified.isoformat()
            }
            if note.supabase_id:
                supabase.table('notes').update(data).eq('id', note.supabase_id).execute()
            else:
                res = supabase.table('notes').insert(data).execute()
                if res.data:
                    note.supabase_id = res.data[0]['id']
            
            note.is_synced = True
        except Exception as e:
            print(f"Sync error: {e}")
            continue
    
    db.session.commit()
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(debug=True)
