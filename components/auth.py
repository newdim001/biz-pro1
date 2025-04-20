import streamlit as st
import hashlib
import sqlite3
from datetime import datetime, timedelta

# Database setup
def init_db():
    conn = sqlite3.connect('bizmaster_users.db')
    c = conn.cursor()
    
    # Create users table if not exists
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT,
            role TEXT NOT NULL,
            business_unit TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')
    
    # Create sessions table
    c.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            user_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database on import
init_db()

# Password hashing
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# User roles and permissions
ROLES = {
    'admin': {
        'description': 'Full access to all features and user management',
        'permissions': {
            'dashboard': True,
            'inventory': True,
            'investments': True,
            'expenses': True,
            'partnership': True,
            'reports': True,
            'user_management': True,
            'data_export': True,
            'data_reset': True
        }
    },
    'manager': {
        'description': 'Can manage business operations but not user accounts',
        'permissions': {
            'dashboard': True,
            'inventory': True,
            'investments': True,
            'expenses': True,
            'partnership': True,
            'reports': True,
            'user_management': False,
            'data_export': True,
            'data_reset': False
        }
    },
    'accountant': {
        'description': 'Can view financial data and generate reports',
        'permissions': {
            'dashboard': True,
            'inventory': False,
            'investments': True,
            'expenses': True,
            'partnership': False,
            'reports': True,
            'user_management': False,
            'data_export': True,
            'data_reset': False
        }
    }
}

# Default admin user (change password after first login)
DEFAULT_ADMIN = {
    'username': 'admin',
    'password': 'admin123',  # Should be changed immediately
    'full_name': 'System Administrator',
    'role': 'admin',
    'business_unit': 'All'
}

def create_default_admin():
    conn = sqlite3.connect('bizmaster_users.db')
    c = conn.cursor()
    
    # Check if admin exists
    c.execute("SELECT id FROM users WHERE username = ?", (DEFAULT_ADMIN['username'],))
    if not c.fetchone():
        # Create default admin
        c.execute('''
            INSERT INTO users (username, password_hash, full_name, role, business_unit)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            DEFAULT_ADMIN['username'],
            hash_password(DEFAULT_ADMIN['password']),
            DEFAULT_ADMIN['full_name'],
            DEFAULT_ADMIN['role'],
            DEFAULT_ADMIN['business_unit']
        ))
        conn.commit()
    
    conn.close()

# Call this function to ensure default admin exists
create_default_admin()

# Authentication functions
def authenticate(username, password):
    conn = sqlite3.connect('bizmaster_users.db')
    c = conn.cursor()
    
    c.execute('''
        SELECT id, username, password_hash, role, business_unit, full_name 
        FROM users 
        WHERE username = ?
    ''', (username,))
    
    user = c.fetchone()
    conn.close()
    
    if user and user[2] == hash_password(password):
        return {
            'id': user[0],
            'username': user[1],
            'role': user[3],
            'business_unit': user[4],
            'full_name': user[5]
        }
    return None

def create_session(user_id):
    import secrets
    session_id = secrets.token_hex(16)
    expires_at = datetime.now() + timedelta(hours=8)  # 8-hour session
    
    conn = sqlite3.connect('bizmaster_users.db')
    c = conn.cursor()
    
    c.execute('''
        INSERT INTO sessions (session_id, user_id, expires_at)
        VALUES (?, ?, ?)
    ''', (session_id, user_id, expires_at))
    
    # Update last login time
    c.execute('''
        UPDATE users 
        SET last_login = CURRENT_TIMESTAMP 
        WHERE id = ?
    ''', (user_id,))
    
    conn.commit()
    conn.close()
    
    return session_id

def validate_session(session_id):
    conn = sqlite3.connect('bizmaster_users.db')
    c = conn.cursor()
    
    c.execute('''
        SELECT u.id, u.username, u.role, u.business_unit, u.full_name, s.expires_at
        FROM sessions s
        JOIN users u ON s.user_id = u.id
        WHERE s.session_id = ? AND s.expires_at > CURRENT_TIMESTAMP
    ''', (session_id,))
    
    session = c.fetchone()
    conn.close()
    
    if session:
        return {
            'id': session[0],
            'username': session[1],
            'role': session[2],
            'business_unit': session[3],
            'full_name': session[4]
        }
    return None

def logout(session_id):
    conn = sqlite3.connect('bizmaster_users.db')
    c = conn.cursor()
    
    c.execute('DELETE FROM sessions WHERE session_id = ?', (session_id,))
    conn.commit()
    conn.close()

# User management functions
def create_user(username, password, full_name, role, business_unit):
    conn = sqlite3.connect('bizmaster_users.db')
    c = conn.cursor()
    
    try:
        c.execute('''
            INSERT INTO users (username, password_hash, full_name, role, business_unit)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            username,
            hash_password(password),
            full_name,
            role,
            business_unit
        ))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_users():
    conn = sqlite3.connect('bizmaster_users.db')
    c = conn.cursor()
    
    c.execute('''
        SELECT id, username, full_name, role, business_unit, created_at, last_login
        FROM users
        ORDER BY created_at DESC
    ''')
    
    users = c.fetchall()
    conn.close()
    
    return [{
        'id': user[0],
        'username': user[1],
        'full_name': user[2],
        'role': user[3],
        'business_unit': user[4],
        'created_at': user[5],
        'last_login': user[6]
    } for user in users]

def delete_user(user_id):
    conn = sqlite3.connect('bizmaster_users.db')
    c = conn.cursor()
    
    c.execute('DELETE FROM users WHERE id = ?', (user_id,))
    c.execute('DELETE FROM sessions WHERE user_id = ?', (user_id,))
    
    conn.commit()
    conn.close()

def update_user(user_id, full_name=None, role=None, business_unit=None, password=None):
    conn = sqlite3.connect('bizmaster_users.db')
    c = conn.cursor()
    
    updates = []
    params = []
    
    if full_name:
        updates.append("full_name = ?")
        params.append(full_name)
    if role:
        updates.append("role = ?")
        params.append(role)
    if business_unit:
        updates.append("business_unit = ?")
        params.append(business_unit)
    if password:
        updates.append("password_hash = ?")
        params.append(hash_password(password))
    
    if updates:
        update_query = "UPDATE users SET " + ", ".join(updates) + " WHERE id = ?"
        params.append(user_id)
        c.execute(update_query, params)
        conn.commit()
    
    conn.close()

# Permission checking
def has_permission(role, permission):
    return ROLES.get(role, {}).get('permissions', {}).get(permission, False)