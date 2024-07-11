from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from functools import wraps
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_key'

# 用戶資料
users = {
    "admin": generate_password_hash("password")
}

# 基於 Cookie 的登錄驗證
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# 初始化數據庫
def init_db():
    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scores (
                id INTEGER PRIMARY KEY,
                score1 INTEGER NOT NULL,
                score2 INTEGER NOT NULL,
                score3 INTEGER NOT NULL,
                score4 INTEGER NOT NULL
            )
        ''')
        # 確保有五筆數據
        for i in range(1, 6):
            cursor.execute('INSERT OR IGNORE INTO scores (id, score1, score2, score3, score4) VALUES (?, ?, ?, ?, ?)', (i, 0, 0, 0, 0))
        conn.commit()

# 登錄頁面
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users and check_password_hash(users.get(username), password):
            session['username'] = username
            return redirect(url_for('index'))
        else:
            return 'Invalid credentials', 401
    return render_template('login.html')

# 登出
@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

# 獲取分數
@app.route('/score/<int:id>', methods=['GET'])
@login_required
def get_score(id):
    try:
        with sqlite3.connect('database.db') as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT score1, score2, score3, score4 FROM scores WHERE id = ?', (id,))
            scores = cursor.fetchone()
            if scores:
                return jsonify({'id': id, 'scores': scores})
            else:
                return jsonify({'error': 'Score not found'}), 404
    except Exception as e:
        print(f"Error fetching score: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# 更新分數
@app.route('/score/<int:id>', methods=['POST'])
@login_required
def update_score(id):
    try:
        new_scores = request.json.get('scores')
        if not new_scores or len(new_scores) != 4:
            return jsonify({'error': 'Invalid scores provided'}), 400

        with sqlite3.connect('database.db') as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE scores SET score1 = ?, score2 = ?, score3 = ?, score4 = ? WHERE id = ?', (*new_scores, id))
            conn.commit()
            return jsonify({'id': id, 'scores': new_scores})
    except Exception as e:
        print(f"Error updating score: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# 獲取所有分數
@app.route('/scores', methods=['GET'])
@login_required
def get_all_scores():
    try:
        with sqlite3.connect('database.db') as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, score1, score2, score3, score4 FROM scores')
            scores = cursor.fetchall()
            return jsonify(scores)
    except Exception as e:
        print(f"Error fetching all scores: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# 渲染首頁
@app.route('/')
@login_required
def index():
    return render_template('index.html')

# 渲染分數頁面
@app.route('/scorepage/<int:id>')
@login_required
def score_page(id):
    return render_template('score.html', id=id)

# 渲染管理頁面
@app.route('/admin')
@login_required
def admin_page():
    return render_template('admin.html')

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=8080)