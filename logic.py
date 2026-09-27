import sqlite3
from datetime import datetime
import os
import cv2

class DatabaseManager:
    def __init__(self, database):
        self.database = database

    def create_tables(self):
        conn = sqlite3.connect(self.database)
        with conn:
            # Добавлена колонка points (по умолчанию 10 бонусов при регистрации)
            conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                user_name TEXT,
                points INTEGER DEFAULT 10
            )
        ''')

            conn.execute('''
            CREATE TABLE IF NOT EXISTS prizes (
                prize_id INTEGER PRIMARY KEY,
                image TEXT,
                used INTEGER DEFAULT 0
            )
        ''')

            conn.execute('''
            CREATE TABLE IF NOT EXISTS winners (
                user_id INTEGER,
                prize_id INTEGER,
                win_time TEXT,
                FOREIGN KEY(user_id) REFERENCES users(user_id),
                FOREIGN KEY(prize_id) REFERENCES prizes(prize_id)
            )
        ''')
            conn.commit()

    def add_user(self, user_id, user_name):
        conn = sqlite3.connect(self.database)
        with conn:
            # Изначально даем 10 бонусов
            conn.execute('INSERT OR IGNORE INTO users (user_id, user_name, points) VALUES (?, ?, 10)', (user_id, user_name))
            conn.commit()

    def add_prize(self, data):
        conn = sqlite3.connect(self.database)
        with conn:
            conn.executemany('''INSERT INTO prizes (image) VALUES (?)''', data)
            conn.commit()

    def add_winner(self, user_id, prize_id):
        win_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor() 
            cur.execute("SELECT * FROM winners WHERE user_id = ? AND prize_id = ?", (user_id, prize_id))
            if cur.fetchall():
                return 0
            else:
                conn.execute('''INSERT INTO winners (user_id, prize_id, win_time) VALUES (?, ?, ?)''', (user_id, prize_id, win_time))
                # За каждую быструю победу начисляем, например, 5 бонусов
                conn.execute('UPDATE users SET points = points + 5 WHERE user_id = ?', (user_id,))
                conn.commit()
                return 1

    def mark_prize_used(self, prize_id):
        conn = sqlite3.connect(self.database)
        with conn:
            conn.execute('''UPDATE prizes SET used = 1 WHERE prize_id = ?''', (prize_id,))
            conn.commit()

    def get_users(self):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute('SELECT user_id FROM users')
            return [x[0] for x in cur.fetchall()] 
        
    def get_user_points(self, user_id):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute('SELECT points FROM users WHERE user_id = ?', (user_id,))
            res = cur.fetchone()
            return res[0] if res else 0

    def change_user_points(self, user_id, amount):
        conn = sqlite3.connect(self.database)
        with conn:
            conn.execute('UPDATE users SET points = points + ? WHERE user_id = ?', (amount, user_id))
            conn.commit()

    def get_prize_img(self, prize_id):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute('SELECT image FROM prizes WHERE prize_id = ?', (prize_id, ))
            res = cur.fetchone()
            return res[0] if res else None
            
    def get_random_prize(self):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute('SELECT * FROM prizes WHERE used = 0 ORDER BY RANDOM()')
            res = cur.fetchone()
            return res if res else (None, None, None)

    def get_winners_count(self, prize_id):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute('SELECT COUNT(*) FROM winners WHERE prize_id = ?', (prize_id, ))
            return cur.fetchone()[0]

    def get_lost_prizes(self, user_id):
        """Возвращает призы, которые уже отправлялись (used=1), но данный юзер их НЕ выиграл."""
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute('''
                SELECT prize_id, image FROM prizes 
                WHERE used = 1 AND prize_id NOT IN (
                    SELECT prize_id FROM winners WHERE user_id = ?
                )
            ''', (user_id,))
            return cur.fetchall()
        
    def get_rating(self):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute('''
            SELECT users.user_name, COUNT(winners.prize_id)
            FROM winners INNER JOIN users ON users.user_id = winners.user_id
            GROUP BY winners.user_id
            ORDER BY COUNT(winners.prize_id) DESC
            LIMIT 10
            ''')
            return cur.fetchall()
  
def hide_img(img_name):
    if not img_name: return
    image = cv2.imread(f'img/{img_name}')
    if image is None: return
    blurred_image = cv2.GaussianBlur(image, (15, 15), 0)
    pixelated_image = cv2.resize(blurred_image, (30, 30), interpolation=cv2.INTER_NEAREST)
    pixelated_image = cv2.resize(pixelated_image, (image.shape[1], image.shape[0]), interpolation=cv2.INTER_NEAREST)
    os.makedirs('hidden_img', exist_ok=True)
    cv2.imwrite(f'hidden_img/{img_name}', pixelated_image)