
import sqlite3


class Databaser:

    def __init__(self, db_name='database.db'):
        self.connection = sqlite3.connect(db_name, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.cursor = self.connection.cursor()
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS videos (
                            id INTEGER PRIMARY KEY AUTOINCREMENT, 
                            name TEXT,
                            desc TEXT,
                            likes INT,
                            dislikes INT,
                            author_name TEXT)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            username TEXT UNIQUE NOT NULL,
                            password TEXT NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS reactions (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER NOT NULL,
                            video_id INTEGER NOT NULL,
                            reaction TEXT NOT NULL,
                            UNIQUE(user_id, video_id),
                            FOREIGN KEY (user_id) REFERENCES users(id),
                            FOREIGN KEY (video_id) REFERENCES videos(id))''')
        self.connection.commit()

    def add_video(self, name, desc, author_name):
        self.cursor.execute('''INSERT INTO videos (name, desc, likes, dislikes, author_name) 
        VALUES (?, ?, 0, 0, ?)''', (name, desc, author_name))
        self.connection.commit()
        return self.cursor.lastrowid

    def get_video(self, video_id):
        self.cursor.execute('SELECT * FROM videos WHERE id = ?', (video_id,))
        r = self.cursor.fetchone()

        if not r:
            return

        return dict(r)

    def change_video(self, video_id, name=None, desc=None, author_name=None):
        old = self.get_video(video_id)

        if name is None:
            name = old['name']
        if desc is None:
            desc = old['desc']
        if author_name is None:
            author_name = old['author_name']

        self.cursor.execute('UPDATE videos SET name = ?, desc = ?, author_name = ? WHERE id = ?', (name, desc, author_name, video_id))
        self.connection.commit()

    def like_video(self, video_id, user_id):
        # Проверяем текущую реакцию пользователя
        current_reaction = self.get_user_reaction(user_id, video_id)
        
        if current_reaction == 'like':
            # Если уже лайк, убираем его
            self.cursor.execute('DELETE FROM reactions WHERE user_id = ? AND video_id = ?', (user_id, video_id))
            self.cursor.execute('UPDATE videos SET likes = likes - 1 WHERE id = ?', (video_id,))
        elif current_reaction == 'dislike':
            # Если был дизлайк, меняем на лайк
            self.cursor.execute('UPDATE reactions SET reaction = ? WHERE user_id = ? AND video_id = ?', 
                              ('like', user_id, video_id))
            self.cursor.execute('UPDATE videos SET dislikes = dislikes - 1, likes = likes + 1 WHERE id = ?', (video_id,))
        else:
            # Если реакции не было, добавляем лайк
            self.cursor.execute('INSERT INTO reactions (user_id, video_id, reaction) VALUES (?, ?, ?)', 
                              (user_id, video_id, 'like'))
            self.cursor.execute('UPDATE videos SET likes = likes + 1 WHERE id = ?', (video_id,))
        
        self.connection.commit()

    def dislike_video(self, video_id, user_id):
        # Проверяем текущую реакцию пользователя
        current_reaction = self.get_user_reaction(user_id, video_id)
        
        if current_reaction == 'dislike':
            # Если уже дизлайк, убираем его
            self.cursor.execute('DELETE FROM reactions WHERE user_id = ? AND video_id = ?', (user_id, video_id))
            self.cursor.execute('UPDATE videos SET dislikes = dislikes - 1 WHERE id = ?', (video_id,))
        elif current_reaction == 'like':
            # Если был лайк, меняем на дизлайк
            self.cursor.execute('UPDATE reactions SET reaction = ? WHERE user_id = ? AND video_id = ?', 
                              ('dislike', user_id, video_id))
            self.cursor.execute('UPDATE videos SET likes = likes - 1, dislikes = dislikes + 1 WHERE id = ?', (video_id,))
        else:
            # Если реакции не было, добавляем дизлайк
            self.cursor.execute('INSERT INTO reactions (user_id, video_id, reaction) VALUES (?, ?, ?)', 
                              (user_id, video_id, 'dislike'))
            self.cursor.execute('UPDATE videos SET dislikes = dislikes + 1 WHERE id = ?', (video_id,))
        
        self.connection.commit()
    
    def get_user_reaction(self, user_id, video_id):
        """Получить реакцию пользователя на видео (like/dislike/None)"""
        self.cursor.execute('SELECT reaction FROM reactions WHERE user_id = ? AND video_id = ?', 
                          (user_id, video_id))
        r = self.cursor.fetchone()
        return r['reaction'] if r else None

    def get_videos(self):
        self.cursor.execute('SELECT * FROM videos')
        videos = self.cursor.fetchall()

        videos = list(map(dict, videos))
        videos.sort(key=lambda x: x['likes'] - x['dislikes'], reverse=True)

        return videos


    def create_user(self, username, password):
        try:
            self.cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', 
                              (username, password))
            self.connection.commit()
            return self.cursor.lastrowid
        except sqlite3.IntegrityError:
            return None
    
    def get_user_by_username(self, username):
        self.cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        r = self.cursor.fetchone()
        return dict(r) if r else None
    
    def get_user_by_id(self, user_id):
        self.cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        r = self.cursor.fetchone()
        return dict(r) if r else None


if __name__ == '__main__':
    db = Databaser()
    db.add_video('Как устроен PNG', 'Описание потом придумаю', 'eleday')
    db.add_video('Автомонтаж видео на Python', 'Описание потом придумаю', 'eleday')
