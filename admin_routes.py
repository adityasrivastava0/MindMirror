import sqlite3
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash, generate_password_hash

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin'):
            return redirect(url_for('admin.admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        with sqlite3.connect('mindmirror.db') as conn:
            c = conn.cursor()
            c.execute("SELECT password FROM admins WHERE username = ?", (username,))
            row = c.fetchone()
            if row and check_password_hash(row[0], password):
                session['admin'] = username
                return redirect(url_for('admin.admin_dashboard'))
            else:
                flash('Invalid credentials', 'error')
    return render_template('admin_login.html')

@admin_bp.route('/logout')
@admin_login_required
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('admin.admin_login'))

@admin_bp.route('/dashboard')
@admin_login_required
def admin_dashboard():
    with sqlite3.connect('mindmirror.db') as conn:
        c = conn.cursor()
        c.execute("SELECT id, name, email FROM users")
        users = c.fetchall()
    return render_template('admin_dashboard.html', users=users)

@admin_bp.route('/user/<int:user_id>')
@admin_login_required
def user_detail(user_id):
    with sqlite3.connect('mindmirror.db') as conn:
        c = conn.cursor()
        c.execute("SELECT id, name, email FROM users WHERE id = ?", (user_id,))
        user = c.fetchone()
        c.execute("SELECT id, score, level, created_at FROM assessments WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
        assessments = c.fetchall()
    return render_template('user_detail.html', user=user, assessments=assessments)

@admin_bp.route('/user/<int:user_id>/reset_password', methods=['GET', 'POST'])
@admin_login_required
def reset_password(user_id):
    if request.method == 'POST':
        new_password = request.form['new_password']
        hashed = generate_password_hash(new_password)
        with sqlite3.connect('mindmirror.db') as conn:
            c = conn.cursor()
            c.execute("UPDATE users SET password = ? WHERE id = ?", (hashed, user_id))
            conn.commit()
        flash('Password reset successfully!', 'success')
        return redirect(url_for('admin.user_detail', user_id=user_id))
    return render_template('reset_password.html', user_id=user_id)

@admin_bp.route('/user/<int:user_id>/delete', methods=['POST'])
@admin_login_required
def delete_user(user_id):
    with sqlite3.connect('mindmirror.db') as conn:
        c = conn.cursor()
        c.execute("DELETE FROM users WHERE id = ?", (user_id,))
        c.execute("DELETE FROM assessments WHERE user_id = ?", (user_id,))
        conn.commit()
    flash('User deleted.', 'success')
    return redirect(url_for('admin.admin_dashboard'))

def init_admin_db():
    with sqlite3.connect('mindmirror.db') as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS admins (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL UNIQUE,
                        password TEXT NOT NULL
                    )''')
        c.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        email TEXT NOT NULL UNIQUE,
                        password TEXT NOT NULL
                    )''')
        c.execute('''CREATE TABLE IF NOT EXISTS assessments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        score INTEGER,
                        level INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                    )''')
        conn.commit()

init_admin_db()