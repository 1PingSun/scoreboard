from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from functools import wraps
from datetime import datetime
import logging

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_key'

# 設置日誌記錄
logging.basicConfig(filename='app.log', level=logging.INFO, 
                    format='%(asctime)s %(levelname)s %(message)s')

# 用戶資料
users = {
    "admin": generate_password_hash("password1")
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
                team1_name TEXT NOT NULL,
                team2_name TEXT NOT NULL,
                score1 INTEGER NOT NULL,
                score2 INTEGER NOT NULL,
                score3 INTEGER NOT NULL,
                score4 INTEGER NOT NULL
            )
        ''')
        # 確保有五筆數據
        for i in range(1, 6):
            cursor.execute('INSERT OR IGNORE INTO scores (id, team1_name, team2_name, score1, score2, score3, score4) VALUES (?, ?, ?, ?, ?, ?, ?)', (i, f'Team {i}A', f'Team {i}B', 0, 0, 0, 0))
        conn.commit()

# 獲取客戶端 IP
@app.route('/get-ip', methods=['GET'])
def get_ip():
    client_ip = request.remote_addr
    return jsonify({'ip': client_ip})

# 日誌記錄請求
def log_request(action):
    client_ip = request.remote_addr
    logging.info(f"Client IP: {client_ip}, Action: {action}")

# 登錄頁面
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users and check_password_hash(users.get(username), password):
            session['username'] = username
            log_request(f'{username} is login')
            return redirect(url_for('index'))
        else:
            log_request(f'failed login attempt, the username is {username}')
            return 'Invalid credentials', 401
    return render_template('login.html')

# 登出
@app.route('/logout')
def logout():
    session.pop('username', None)
    log_request(f'logout')
    return redirect(url_for('login'))

# 獲取分數
@app.route('/score/<int:id>', methods=['GET'])
@login_required
def get_score(id):
    try:
        with sqlite3.connect('database.db') as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT team1_name, team2_name, score1, score2, score3, score4 FROM scores WHERE id = ?', (id,))
            scores = cursor.fetchone()
            if scores:
                return jsonify({'id': id, 'team1_name': scores[0], 'team2_name': scores[1], 'scores': scores[2:]})
            else:
                log_request(f'failed to get score for id {id}')
                return jsonify({'error': 'Score not found'}), 404
    except Exception as e:
        logging.error(f"Error fetching score: {e}")
        log_request('error fetching score')
        print(f"Error fetching score: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# 獲取所有分數
@app.route('/scores', methods=['GET'])
@login_required
def get_all_scores():
    try:
        with sqlite3.connect('database.db') as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, team1_name, team2_name, score1, score2, score3, score4 FROM scores')
            scores = cursor.fetchall()
            return jsonify(scores)
    except Exception as e:
        logging.error(f"Error fetching all scores: {e}")
        log_request('error fetching all scores')
        print(f"Error fetching all scores: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# 更新分數
@app.route('/score/<int:id>', methods=['POST'])
@login_required
def update_score(id):
    try:
        new_scores = request.json.get('scores')
        if not new_scores or len(new_scores) != 4:
            log_request(f'invalid scores provided for id {id}')
            return jsonify({'error': 'Invalid scores provided'}), 400

        with sqlite3.connect('database.db') as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE scores SET score1 = ?, score2 = ?, score3 = ?, score4 = ? WHERE id = ?', (*new_scores, id))
            conn.commit()
            log_request(f'update score for id {id}, new scores is {new_scores}')
            return jsonify({'id': id, 'scores': new_scores})
    except Exception as e:
        print(f"Error updating score: {e}")
        logging.error(f"Error updating score: {e}")
        log_request('error updating score')
        return jsonify({'error': 'Internal server error'}), 500
    
# 更新隊伍名稱
@app.route('/update-team-name/<int:id>', methods=['POST'])
@login_required
def update_team_name(id):
    try:
        team_index = request.json.get('teamIndex')
        new_name = request.json.get('newName')
        if team_index not in [1, 2] or not new_name:
            log_request(f'invalid team index or name for id {id}')
            return jsonify({'error': 'Invalid team index or name'}), 400

        with sqlite3.connect('database.db') as conn:
            cursor = conn.cursor()
            if team_index == 1:
                cursor.execute('SELECT team1_name FROM scores WHERE id = ?', (id,))
                original_name = cursor.fetchall()
                cursor.execute('UPDATE scores SET team1_name = ? WHERE id = ?', (new_name, id))
            elif team_index == 2:
                cursor.execute('SELECT team2_name FROM scores WHERE id = ?', (id,))
                original_name = cursor.fetchall()
                cursor.execute('UPDATE scores SET team2_name = ? WHERE id = ?', (new_name, id))
            conn.commit()
            log_request(f'update team name for id {id}, change {original_name} into {new_name}')
            return jsonify({'id': id, 'teamIndex': team_index, 'newName': new_name})
    except Exception as e:
        logging.error(f"Error updating team name: {e}")
        log_request('error updating team name')
        print(f"Error updating team name: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# 渲染首頁
@app.route('/')
@login_required
def index():
    log_request('access index page')
    return render_template('index.html')

# 渲染分數頁面
@app.route('/scorepage/<int:id>')
@login_required
def score_page(id):
    log_request(f'access score page for id {id}')
    return render_template('score.html', id=id)

# 渲染管理頁面
@app.route('/admin')
@login_required
def admin_page():
    log_request('access admin page')
    return render_template('admin.html')

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=8082, debug = True)