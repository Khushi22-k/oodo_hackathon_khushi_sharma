import sqlite3
from sqlite3 import Error
from flask import Flask, request, jsonify

app = Flask(__name__)

class SimpleSQLiteDatabase:
    def __init__(self, db_file="my_simple_app.db"):
        self.db_file = db_file
        self.conn = None
        self.cur = None
        self._connect()
        self.create_users_table()

    def _connect(self):
        try:
            self.conn = sqlite3.connect(self.db_file, check_same_thread=False)
            self.cur = self.conn.cursor()
            print(f"Connected to SQLite database: {self.db_file}")
        except Error as e:
            print(f"Error connecting to SQLite database: {e}")
            self.conn = None
            self.cur = None

    def _close(self):
        if self.cur:
            self.cur.close()
            self.cur = None
        if self.conn:
            self.conn.close()
            self.conn = None
            print("SQLite database connection closed.")

    def _execute_query(self, query, params=None, fetch=False):
        if not self.conn or not self.cur:
            self._connect()
            if not self.conn:
                return None
        try:
            self.cur.execute(query, params or ())
            if fetch:
                return self.cur.fetchall()
            else:
                self.conn.commit()
                return True
        except Error as e:
            print(f"Error executing query: {e}")
            self.conn.rollback()
            return None

    def create_users_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            age INTEGER,
            password TEXT NOT NULL,
            skills_offer TEXT,
            skills_require TEXT
        );
        """
        print("Attempting to create 'users' table with skills fields.")
        return self._execute_query(query)

    def add_user(self, name, email, password, age=None, skills_offer="", skills_require=""):
        query = "INSERT INTO users (name, email, password, age, skills_offer, skills_require) VALUES (?, ?, ?, ?, ?, ?);"
        params = (name, email, password, age, skills_offer, skills_require)
        print(f"Attempting to add user: {name} ({email})")
        return self._execute_query(query, params)

    def get_user_by_email(self, email):
        query = "SELECT * FROM users WHERE email = ?;"
        print(f"Attempting to get user by email: {email}")
        user = self._execute_query(query, (email,), fetch=True)
        return user[0] if user else None

    def get_all_users(self):
        query = "SELECT * FROM users;"
        print("Attempting to get all users.")
        return self._execute_query(query, fetch=True)

    def update_user_age(self, email, new_age):
        query = "UPDATE users SET age = ? WHERE email = ?;"
        params = (new_age, email)
        print(f"Attempting to update age for user {email} to {new_age}")
        return self._execute_query(query, params)

    def delete_user(self, email):
        query = "DELETE FROM users WHERE email = ?;"
        print(f"Attempting to delete user: {email}")
        return self._execute_query(query, (email,))

db = SimpleSQLiteDatabase("my_simple_app.db")

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    user = db.get_user_by_email(email)
    if user and user[4] == password:
        return jsonify({'success': True})
    return jsonify({'success': False})

@app.route('/user_profile')
def user_profile():
    email = request.args.get('email')
    user = db.get_user_by_email(email)
    if user:
        return jsonify({
            'name': user[1],
            'skills_offer': user[5],
            'skills_require': user[6]
        })
    return jsonify({'error': 'User not found'}), 404

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    age = data.get('age') if 'age' in data else None
    skills_offer = data.get('skills_offer') if 'skills_offer' in data else ""
    skills_require = data.get('skills_require') if 'skills_require' in data else ""
    result = db.add_user(name, email, password, age, skills_offer, skills_require)
    if result:
        return jsonify({'success': True})
    else:
        print("Error: Could not create user. Possible duplicate email or DB error.")
        return jsonify({'success': False, 'error': 'User already exists or DB error'})

@app.route('/all_users')
def all_users():
    users = db.get_all_users()
    user_list = []
    if users:
        for user in users:
            user_list.append({
                'id': user[0],
                'name': user[1],
                'skills_offer': user[5],
                'skills_require': user[6]
            })
    return jsonify(user_list)

@app.route('/user_by_id')
def user_by_id():
    user_id = request.args.get('id')
    query = "SELECT id, name, skills_offer, skills_require FROM users WHERE id = ?;"
    user = db._execute_query(query, (user_id,), fetch=True)
    if user:
        user = user[0]
        return jsonify({
            'id': user[0],
            'name': user[1],
            'skills_offer': user[2],
            'skills_require': user[3]
        })
    return jsonify({'error': 'User not found'}), 404

@app.route('/swap_skills', methods=['POST'])
def swap_skills():
    data = request.get_json()
    login_email = data.get('login_email')
    viewed_user_id = data.get('viewed_user_id')
    offered_skill = data.get('offered_skill')
    wanted_skill = data.get('wanted_skill')
    login_user = db.get_user_by_email(login_email)
    viewed_user = db._execute_query("SELECT * FROM users WHERE id = ?", (viewed_user_id,), fetch=True)
    if not login_user or not viewed_user:
        return jsonify({'success': False, 'error': 'User not found'})
    viewed_user = viewed_user[0]
    login_skills_offer = [s.strip() for s in login_user[5].split(',') if s.strip() != offered_skill]
    viewed_skills_require = [s.strip() for s in viewed_user[6].split(',') if s.strip() != wanted_skill]
    db._execute_query("UPDATE users SET skills_offer = ? WHERE email = ?", (','.join(login_skills_offer), login_email))
    db._execute_query("UPDATE users SET skills_require = ? WHERE id = ?", (','.join(viewed_skills_require), viewed_user_id))
    return jsonify({'success': True})

if __name__ == "__main__":
    db._connect()
    db.create_users_table()
    print("Database setup complete.")
