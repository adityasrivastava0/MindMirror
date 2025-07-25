import os
import platform
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, make_response
import pdfkit
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import google.generativeai as genai
from admin_routes import admin_bp

# --------- Load .env ---------
load_dotenv()
GENAI_API_KEY = os.getenv("GEMINI_API_KEY")

# --------- PDF Configuration ---------
if platform.system() == "Windows":
    PDFKIT_PATH = r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
else:
    PDFKIT_PATH = "/usr/bin/wkhtmltopdf"
config = pdfkit.configuration(wkhtmltopdf=PDFKIT_PATH)

# --------- Flask App ---------
app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
app.register_blueprint(admin_bp)

# --------- Init Database ---------
def init_db():
    if not os.path.exists('mindmirror.db'):
        with sqlite3.connect('mindmirror.db') as conn:
            c = conn.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL
                )
            ''')
            c.execute('''
                CREATE TABLE IF NOT EXISTS assessments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    answers TEXT,
                    score INTEGER,
                    level TEXT,
                    created_at TIMESTAMP
                )
            ''')
            conn.commit()

def init_admin_db():
    with sqlite3.connect('mindmirror.db') as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        # Insert default admin if not exists
        c.execute("SELECT * FROM admins WHERE username = ?", ('admin',))
        if not c.fetchone():
            c.execute("INSERT INTO admins (username, password) VALUES (?, ?)", ('admin', generate_password_hash('admin123')))
        conn.commit()

# --------- Questions ---------
QUESTIONS = [
    "Little interest or pleasure in doing things",
    "Feeling down, depressed, or hopeless",
    "Trouble falling or staying asleep, or sleeping too much",
    "Feeling tired or having little energy",
    "Poor appetite or overeating",
    "Feeling bad about yourself or like a failure",
    "Trouble concentrating on things",
    "Moving or speaking slowly or being restless",
    "Thoughts of being better off dead or hurting yourself",
    "Do you feel lonely even when with others?",
    "Do you feel no one understands you?",
    "Are you facing any financial/relationship/work stress?",
    "Do you have someone to talk to freely?",
    "Do you struggle to feel hopeful about your future?"
]

# --------- AI Analysis Generator (Gemini AI) ---------
def generate_ai_insights(score, level, answers):
    try:
        genai.configure(api_key=GENAI_API_KEY)
        prompt = f"""
        A user completed a mental health assessment with the following results:

        - Score: {score}/42
        - Severity Level: {level}
        - Answers: {answers}

        Based on these, provide a short paragraph summary (100 words max) analyzing the user's mental state, possible causes, and suggest a few positive coping actions. Keep tone gentle and professional.
        """
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print("Gemini AI Error:", e)
        return "AI analysis could not be generated at the moment. Please try again later."

# --------- Suggestion Logic ---------
def generate_suggestions(level, answers):
    suggestions = []
    if level == "Normal":
        suggestions.append("Continue with your healthy habits and self-care routine.")
    elif level == "Mild":
        suggestions.append("Consider practicing mindfulness or journaling.")
        suggestions.append("Reach out to friends or family for support.")
    elif level == "Moderate":
        suggestions.append("We recommend speaking with a counselor or therapist.")
        suggestions.append("Establish a daily routine with self-care activities.")
    else:
        suggestions.append("Strongly consider seeking professional mental health support.")
        suggestions.append("Contact a crisis hotline if needed.")

    if answers[9] >= 2 or answers[10] >= 2:
        suggestions.append("Consider joining social groups or activities to combat loneliness.")
    if answers[11] >= 2:
        suggestions.append("Try stress-reduction techniques like deep breathing exercises.")
    if answers[12] <= 1:
        suggestions.append("Building a support network is important—consider reaching out to old friends.")
    return suggestions

# --------- Routes ---------
@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        try:
            with sqlite3.connect('mindmirror.db') as conn:
                c = conn.cursor()
                c.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)", (name, email, password))
                conn.commit()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return "Email already registered. Please login."
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        with sqlite3.connect('mindmirror.db') as conn:
            c = conn.cursor()
            c.execute("SELECT id, password FROM users WHERE email = ?", (email,))
            user = c.fetchone()

        if user and check_password_hash(user[1], password):
            session['user_id'] = user[0]
            return redirect(url_for('home'))
        else:
            return "Invalid email or password."
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/assessment', methods=['GET', 'POST'])
def assessment():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        answers = [int(request.form.get(f'q{i}', 0)) for i in range(len(QUESTIONS))]
        score = sum(answers)

        if score <= 7:
            level = "Normal"
        elif score <= 14:
            level = "Mild"
        elif score <= 21:
            level = "Moderate"
        else:
            level = "Severe"

        ai_analysis = generate_ai_insights(score, level, answers)
        suggestions = generate_suggestions(level, answers)

        session['results'] = {
            'score': score,
            'level': level,
            'analysis': [ai_analysis],
            'suggestions': suggestions
        }

        with sqlite3.connect('mindmirror.db') as conn:
            c = conn.cursor()
            c.execute("INSERT INTO assessments (user_id, answers, score, level, created_at) VALUES (?, ?, ?, ?, ?)",
                      (session['user_id'], str(answers), score, level, datetime.now()))
            conn.commit()

        return redirect(url_for('results'))

    return render_template('assessment.html', questions=QUESTIONS)

@app.route('/results')
def results():
    if 'user_id' not in session or 'results' not in session:
        return redirect(url_for('login'))
    return render_template('results.html',
                           score=session['results']['score'],
                           level=session['results']['level'],
                           analysis=session['results']['analysis'],
                           suggestions=session['results']['suggestions'],
                           now=datetime.now())

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    with sqlite3.connect('mindmirror.db') as conn:
        c = conn.cursor()
        c.execute("SELECT id, score, level, created_at FROM assessments WHERE user_id = ? ORDER BY created_at DESC", (session['user_id'],))
        assessments = c.fetchall()
    return render_template('dashboard.html', assessments=assessments)

@app.route('/download_pdf')
def download_pdf():
    if 'user_id' not in session or 'results' not in session:
        return redirect(url_for('login'))

    # Get user info for personalization
    with sqlite3.connect('mindmirror.db') as conn:
        c = conn.cursor()
        c.execute("SELECT name, email FROM users WHERE id = ?", (session['user_id'],))
        user = c.fetchone()
        user_name = user[0] if user else "Unknown"
        user_email = user[1] if user else "Unknown"

    html = render_template('results.html',
                           score=session['results']['score'],
                           level=session['results']['level'],
                           analysis=session['results']['analysis'],
                           suggestions=session['results']['suggestions'],
                           now=datetime.now(),
                           user_name=user_name,
                           user_email=user_email)
    pdf = pdfkit.from_string(html, False, configuration=config, options={'enable-local-file-access': ''})
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=MindMirror_Report_{user_name}.pdf'
    return response

@app.route('/resources')
def resources():
    return render_template('resources.html')

@app.route('/chat', methods=['GET', 'POST'])
def chat():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    response = None
    if request.method == 'POST':
        user_message = request.form['message']
        try:
            genai.configure(api_key=GENAI_API_KEY)
            model = genai.GenerativeModel('gemini-1.5-flash')
            chat = model.start_chat()
            ai_response = chat.send_message(user_message)
            response = ai_response.text.strip()
        except Exception as e:
            print("Gemini Chat Error:", e)
            response = "Sorry, I'm unable to reply right now."
    return render_template('chat.html', response=response)

@app.route('/mood')
def mood():
    return render_template('mood.html')

# --------- Run App ---------
if __name__ == '__main__':
    init_db()
    init_admin_db()
    app.run(debug=True)
