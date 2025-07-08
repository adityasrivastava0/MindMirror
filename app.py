
import pdfkit

# Linux path inside Docker container
PDFKIT_PATH = "/usr/bin/wkhtmltopdf"
config = pdfkit.configuration(wkhtmltopdf=PDFKIT_PATH)


from flask import Flask, render_template, request, redirect, url_for, session, make_response
from datetime import datetime
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Questions list
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

# Initialize DB
def init_db():
    with sqlite3.connect('mindmirror.db') as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS assessments
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      answers TEXT,
                      score INTEGER,
                      level TEXT,
                      created_at TIMESTAMP)''')
        conn.commit()

# Home Page
@app.route('/')
def home():
    return render_template('index.html')

# Assessment Page
@app.route('/assessment', methods=['GET', 'POST'])
def assessment():
    if request.method == 'POST':
        answers = [int(request.form.get(f'q{i}', 0)) for i in range(len(QUESTIONS))]
        score = sum(answers)

        # Level Classification
        if score <= 7:
            level = "Normal"
        elif score <= 14:
            level = "Mild"
        elif score <= 21:
            level = "Moderate"
        else:
            level = "Severe"

        # AI-style analysis
        analysis = []
        if answers[9] >= 2 and answers[10] >= 2 and answers[12] <= 1:
            analysis.append("Social isolation suspected")
        if answers[11] >= 2:
            analysis.append("Significant stress factors detected")
        if answers[3] >= 2 and answers[4] >= 2 and answers[6] >= 2:
            analysis.append("Possible burnout pattern")
        if answers[8] >= 2:
            analysis.append("Urgent: Please seek professional help immediately")

        # Suggestions
        suggestions = generate_suggestions(level, answers)

        # Save in session
        session['results'] = {
            'score': score,
            'level': level,
            'analysis': analysis,
            'suggestions': suggestions
        }

        # Optionally save to DB
        if request.form.get('save_results'):
            with sqlite3.connect('mindmirror.db') as conn:
                c = conn.cursor()
                c.execute("INSERT INTO assessments (answers, score, level, created_at) VALUES (?, ?, ?, ?)",
                          (str(answers), score, level, datetime.now()))
                conn.commit()

        return redirect(url_for('results'))

    return render_template('assessment.html', questions=QUESTIONS)

# Suggestions based on score
def generate_suggestions(level, answers):
    suggestions = []

    if level == "Normal":
        suggestions.append("Continue with your healthy habits and self-care routine")
    elif level == "Mild":
        suggestions.append("Consider practicing mindfulness or journaling")
        suggestions.append("Reach out to friends or family for support")
    elif level == "Moderate":
        suggestions.append("Recommend speaking with a counselor or therapist")
        suggestions.append("Establish a daily routine with self-care activities")
    else:
        suggestions.append("Strongly recommend professional mental health support")
        suggestions.append("Contact a crisis hotline if needed")

    if answers[9] >= 2 or answers[10] >= 2:
        suggestions.append("Consider joining social groups or activities to combat loneliness")
    if answers[11] >= 2:
        suggestions.append("Try stress-reduction techniques like deep breathing exercises")
    if answers[12] <= 1:
        suggestions.append("Building a support network is important - consider reaching out to old friends")

    return suggestions

# Results Page
@app.route('/results')
def results():
    if 'results' not in session:
        return redirect(url_for('home'))

    session['results']['now'] = datetime.now()
    return render_template('results.html',
                           score=session['results']['score'],
                           level=session['results']['level'],
                           analysis=session['results']['analysis'],
                           suggestions=session['results']['suggestions'])

# Resources Page
@app.route('/resources')
def resources():
    return render_template('resources.html')

# PDF Download Route
@app.route('/download_pdf')
def download_pdf():
    if 'results' not in session:
        return redirect(url_for('home'))

    score = session['results']['score']
    level = session['results']['level']
    analysis = session['results']['analysis']
    suggestions = session['results']['suggestions']
    now = datetime.now()

    html = render_template('results.html',
                           score=score,
                           level=level,
                           analysis=analysis,
                           suggestions=suggestions,
                           now=now)

    # Important PDFKit options
    options = { 'enable-local-file-access': '' }

    # Generate PDF
    pdf = pdfkit.from_string(html, False, configuration=config, options=options)

    # Prepare response
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=report.pdf'
    return response

# Run the app
if __name__ == '__main__':
    init_db()
    app.run(debug=True)
