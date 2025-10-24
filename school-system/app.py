from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
import sqlite3
import os
from datetime import datetime, timedelta
import random
import string

app = Flask(__name__)
app.secret_key = 'school_system_secret_key_2024'
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
app.config['SESSION_REFRESH_EACH_REQUEST'] = True

# إنشاء مجلدات التخزين
if not os.path.exists('data'):
    os.makedirs('data')

# تهيئة قاعدة البيانات
def init_db():
    conn = sqlite3.connect('data/database.db')
    c = conn.cursor()
    
    # جدول المستخدمين
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  username TEXT UNIQUE NOT NULL,
                  password TEXT NOT NULL,
                  user_type TEXT NOT NULL,
                  grade TEXT,
                  section TEXT,
                  subject TEXT,
                  is_active BOOLEAN DEFAULT 1,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # جدول الغرف
    c.execute('''CREATE TABLE IF NOT EXISTS rooms
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  subject TEXT NOT NULL,
                  grade TEXT NOT NULL,
                  section TEXT NOT NULL,
                  code TEXT UNIQUE NOT NULL,
                  teacher_id INTEGER NOT NULL,
                  description TEXT,
                  max_students INTEGER DEFAULT 30,
                  is_active BOOLEAN DEFAULT 1,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # جدول طلاب الغرف
    c.execute('''CREATE TABLE IF NOT EXISTS room_students
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  room_id INTEGER NOT NULL,
                  student_id INTEGER NOT NULL,
                  joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  UNIQUE(room_id, student_id))''')
    
    # جدول رسائل الدردشة
    c.execute('''CREATE TABLE IF NOT EXISTS chat_messages
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  room_id INTEGER NOT NULL,
                  user_id INTEGER NOT NULL,
                  user_name TEXT NOT NULL,
                  message TEXT NOT NULL,
                  message_type TEXT DEFAULT 'text',
                  sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # جدول الواجبات
    c.execute('''CREATE TABLE IF NOT EXISTS assignments
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  title TEXT NOT NULL,
                  description TEXT NOT NULL,
                  subject TEXT NOT NULL,
                  grade TEXT NOT NULL,
                  section TEXT NOT NULL,
                  teacher_id INTEGER NOT NULL,
                  room_id INTEGER,
                  due_date DATE NOT NULL,
                  total_marks INTEGER NOT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # جدول حلول الواجبات
    c.execute('''CREATE TABLE IF NOT EXISTS assignment_submissions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  assignment_id INTEGER NOT NULL,
                  student_id INTEGER NOT NULL,
                  solution TEXT NOT NULL,
                  grade INTEGER,
                  feedback TEXT,
                  status TEXT DEFAULT 'submitted',
                  submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  graded_at TIMESTAMP)''')
    
    # إنشاء مستخدم المدير إذا لم يكن موجوداً
    c.execute('''INSERT OR IGNORE INTO users (name, username, password, user_type) 
                 VALUES (?, ?, ?, ?)''', 
              ('مدير النظام', 'admin', 'admin123', 'admin'))
    
    conn.commit()
    conn.close()

# دوال مساعدة
def generate_room_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def get_user_stats(user_id, user_type):
    conn = sqlite3.connect('data/database.db')
    c = conn.cursor()
    stats = {}
    
    if user_type == 'student':
        c.execute('SELECT grade, section FROM users WHERE id = ?', (user_id,))
        user = c.fetchone()
        grade, section = user if user else (None, None)
        
        c.execute('''SELECT COUNT(*) FROM room_students rs 
                     JOIN rooms r ON rs.room_id = r.id 
                     WHERE rs.student_id = ? AND r.is_active = 1''', (user_id,))
        stats['rooms_count'] = c.fetchone()[0]
        
        c.execute('''SELECT COUNT(*) FROM assignments 
                     WHERE grade = ? AND section = ?''', (grade, section))
        stats['assignments_count'] = c.fetchone()[0]
        
        c.execute('''SELECT COUNT(*) FROM assignments a
                     WHERE a.grade = ? AND a.section = ?
                     AND NOT EXISTS (SELECT 1 FROM assignment_submissions 
                                   WHERE assignment_id = a.id AND student_id = ?)''', 
                  (grade, section, user_id))
        stats['pending_assignments'] = c.fetchone()[0]
        
    elif user_type == 'teacher':
        c.execute('SELECT COUNT(*) FROM rooms WHERE teacher_id = ? AND is_active = 1', (user_id,))
        stats['rooms_count'] = c.fetchone()[0]
        
        c.execute('SELECT COUNT(*) FROM assignments WHERE teacher_id = ?', (user_id,))
        stats['assignments_count'] = c.fetchone()[0]
        
        c.execute('SELECT COUNT(*) FROM users WHERE user_type = "student"')
        stats['students_count'] = c.fetchone()[0]
        
        c.execute('''SELECT COUNT(*) FROM assignment_submissions s
                     JOIN assignments a ON s.assignment_id = a.id
                     WHERE a.teacher_id = ? AND s.status = "submitted"''', (user_id,))
        stats['pending_grading'] = c.fetchone()[0]
    
    elif user_type == 'admin':
        c.execute('SELECT COUNT(*) FROM users WHERE user_type = "student"')
        stats['students_count'] = c.fetchone()[0]
        
        c.execute('SELECT COUNT(*) FROM users WHERE user_type = "teacher"')
        stats['teachers_count'] = c.fetchone()[0]
        
        c.execute('SELECT COUNT(*) FROM rooms WHERE is_active = 1')
        stats['rooms_count'] = c.fetchone()[0]
        
        c.execute('SELECT COUNT(*) FROM chat_messages')
        stats['total_messages'] = c.fetchone()[0]
    
    conn.close()
    return stats

# إضافة رؤوس HTTP لمنع التخزين المؤقت
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.headers['Cache-Control'] = 'public, max-age=0'
    return response

# Routes
@app.route('/')
def index():
    session.modified = True
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    user_type = request.form['user_type']
    
    conn = sqlite3.connect('data/database.db')
    c = conn.cursor()
    
    c.execute('''SELECT * FROM users WHERE username = ? AND password = ? 
                 AND user_type = ? AND is_active = 1''', (username, password, user_type))
    user = c.fetchone()
    conn.close()
    
    if user:
        session.permanent = True
        session['user_id'] = user[0]
        session['username'] = user[2]
        session['user_type'] = user[4]
        session['name'] = user[1]
        session['grade'] = user[5]
        session['section'] = user[6]
        session.modified = True
        
        flash(f'مرحباً بعودتك، {user[1]}!', 'success')
        
        if user_type == 'student':
            return redirect('/student/dashboard')
        elif user_type == 'teacher':
            return redirect('/teacher/dashboard')
        elif user_type == 'admin':
            return redirect('/admin/dashboard')
    else:
        flash('بيانات الدخول غير صحيحة!', 'error')
    
    return redirect('/')

@app.route('/register', methods=['POST'])
def register():
    name = request.form['name']
    username = request.form['username']
    password = request.form['password']
    user_type = request.form['user_type']
    grade = request.form.get('grade', '')
    section = request.form.get('section', '')
    subject = request.form.get('subject', '')
    
    conn = sqlite3.connect('data/database.db')
    c = conn.cursor()
    
    try:
        c.execute('''INSERT INTO users (name, username, password, user_type, grade, section, subject)
                     VALUES (?, ?, ?, ?, ?, ?, ?)''',
                  (name, username, password, user_type, grade, section, subject))
        conn.commit()
        session.modified = True
        flash('تم إنشاء الحساب بنجاح! يمكنك الآن تسجيل الدخول.', 'success')
    except sqlite3.IntegrityError:
        flash('اسم المستخدم موجود مسبقاً!', 'error')
    finally:
        conn.close()
    
    return redirect('/')

# لوحة الطالب
@app.route('/student/dashboard')
def student_dashboard():
    if 'user_id' not in session or session['user_type'] != 'student':
        flash('يجب تسجيل الدخول أولاً!', 'error')
        return redirect('/')
    
    session.modified = True
    stats = get_user_stats(session['user_id'], 'student')
    
    conn = sqlite3.connect('data/database.db')
    c = conn.cursor()
    
    # الغرف الدراسية
    c.execute('''SELECT r.*, u.name as teacher_name FROM rooms r
                 JOIN room_students rs ON r.id = rs.room_id
                 JOIN users u ON r.teacher_id = u.id
                 WHERE rs.student_id = ? AND r.is_active = 1''', (session['user_id'],))
    rooms = [dict(zip([col[0] for col in c.description], row)) for row in c.fetchall()]
    
    conn.close()
    
    return render_template('student_dashboard.html',
                         stats=stats,
                         rooms=rooms,
                         session=session)

@app.route('/student/rooms')
def student_rooms():
    if 'user_id' not in session or session['user_type'] != 'student':
        flash('يجب تسجيل الدخول أولاً!', 'error')
        return redirect('/')
    
    session.modified = True
    conn = sqlite3.connect('data/database.db')
    c = conn.cursor()
    
    # غرف الطالب
    c.execute('''SELECT r.*, u.name as teacher_name FROM rooms r
                 JOIN room_students rs ON r.id = rs.room_id
                 JOIN users u ON r.teacher_id = u.id
                 WHERE rs.student_id = ? AND r.is_active = 1''', (session['user_id'],))
    rooms = [dict(zip([col[0] for col in c.description], row)) for row in c.fetchall()]
    
    # غرف متاحة
    c.execute('''SELECT r.*, u.name as teacher_name FROM rooms r
                 JOIN users u ON r.teacher_id = u.id
                 WHERE r.grade = ? AND r.section = ? AND r.is_active = 1
                 AND r.id NOT IN (SELECT room_id FROM room_students WHERE student_id = ?)''',
              (session['grade'], session['section'], session['user_id']))
    available_rooms = [dict(zip([col[0] for col in c.description], row)) for row in c.fetchall()]
    
    conn.close()
    
    return render_template('student_rooms.html',
                         rooms=rooms,
                         available_rooms=available_rooms,
                         session=session)

@app.route('/student/assignments')
def student_assignments():
    if 'user_id' not in session or session['user_type'] != 'student':
        flash('يجب تسجيل الدخول أولاً!', 'error')
        return redirect('/')
    
    session.modified = True
    conn = sqlite3.connect('data/database.db')
    c = conn.cursor()
    
    c.execute('''SELECT a.*, u.name as teacher_name FROM assignments a
                 JOIN users u ON a.teacher_id = u.id
                 WHERE a.grade = ? AND a.section = ?
                 ORDER BY a.due_date''', (session['grade'], session['section']))
    assignments = [dict(zip([col[0] for col in c.description], row)) for row in c.fetchall()]
    
    # إضافة حالة التسليم
    for assignment in assignments:
        c.execute('''SELECT status, grade, feedback FROM assignment_submissions 
                     WHERE assignment_id = ? AND student_id = ?''',
                  (assignment['id'], session['user_id']))
        submission = c.fetchone()
        if submission:
            assignment['submission_status'] = submission[0]
            assignment['submission_grade'] = submission[1]
            assignment['feedback'] = submission[2]
        else:
            assignment['submission_status'] = 'not_submitted'
            assignment['submission_grade'] = None
            assignment['feedback'] = None
    
    conn.close()
    
    return render_template('student_assignments.html',
                         assignments=assignments,
                         session=session)

@app.route('/student/room/<int:room_id>')
def student_room_chat(room_id):
    if 'user_id' not in session or session['user_type'] != 'student':
        flash('يجب تسجيل الدخول أولاً!', 'error')
        return redirect('/')
    
    session.modified = True
    conn = sqlite3.connect('data/database.db')
    c = conn.cursor()
    
    # التحقق من أن الطالب مسجل في الغرفة
    c.execute('''SELECT r.*, u.name as teacher_name FROM rooms r
                 JOIN room_students rs ON r.id = rs.room_id
                 JOIN users u ON r.teacher_id = u.id
                 WHERE r.id = ? AND rs.student_id = ? AND r.is_active = 1''',
              (room_id, session['user_id']))
    room = c.fetchone()
    
    if not room:
        conn.close()
        flash('غير مسموح لك بالدخول إلى هذه الغرفة!', 'error')
        return redirect('/student/rooms')
    
    room_dict = dict(zip([col[0] for col in c.description], room))
    
    # جلب رسائل الدردشة
    c.execute('''SELECT cm.*, u.user_type FROM chat_messages cm
                 JOIN users u ON cm.user_id = u.id
                 WHERE cm.room_id = ? ORDER BY cm.sent_at DESC LIMIT 50''', (room_id,))
    messages = [dict(zip([col[0] for col in c.description], row)) for row in c.fetchall()]
    messages.reverse()  # لعرض الرسائل من الأقدم إلى الأحدث
    
    conn.close()
    
    return render_template('student_room_chat.html',
                         room=room_dict,
                         messages=messages,
                         session=session)

# لوحة المعلم
@app.route('/teacher/dashboard')
def teacher_dashboard():
    if 'user_id' not in session or session['user_type'] != 'teacher':
        flash('يجب تسجيل الدخول أولاً!', 'error')
        return redirect('/')
    
    session.modified = True
    stats = get_user_stats(session['user_id'], 'teacher')
    
    conn = sqlite3.connect('data/database.db')
    c = conn.cursor()
    
    # الغرف النشطة
    c.execute('SELECT * FROM rooms WHERE teacher_id = ? AND is_active = 1', (session['user_id'],))
    rooms = [dict(zip([col[0] for col in c.description], row)) for row in c.fetchall()]
    
    conn.close()
    
    return render_template('teacher_dashboard.html',
                         stats=stats,
                         rooms=rooms,
                         session=session)

@app.route('/teacher/rooms')
def teacher_rooms():
    if 'user_id' not in session or session['user_type'] != 'teacher':
        flash('يجب تسجيل الدخول أولاً!', 'error')
        return redirect('/')
    
    session.modified = True
    conn = sqlite3.connect('data/database.db')
    c = conn.cursor()
    
    c.execute('''SELECT r.*, 
                 (SELECT COUNT(*) FROM room_students WHERE room_id = r.id) as student_count
                 FROM rooms r WHERE teacher_id = ? ORDER BY created_at DESC''',
              (session['user_id'],))
    rooms = [dict(zip([col[0] for col in c.description], row)) for row in c.fetchall()]
    
    conn.close()
    
    return render_template('teacher_rooms.html',
                         rooms=rooms,
                         session=session)

@app.route('/teacher/assignments')
def teacher_assignments():
    if 'user_id' not in session or session['user_type'] != 'teacher':
        flash('يجب تسجيل الدخول أولاً!', 'error')
        return redirect('/')
    
    session.modified = True
    conn = sqlite3.connect('data/database.db')
    c = conn.cursor()
    
    c.execute('''SELECT a.*,
                 (SELECT COUNT(*) FROM assignment_submissions WHERE assignment_id = a.id) as submissions_count,
                 (SELECT COUNT(*) FROM assignment_submissions WHERE assignment_id = a.id AND status = "graded") as graded_count
                 FROM assignments a WHERE teacher_id = ? ORDER BY created_at DESC''',
              (session['user_id'],))
    assignments = [dict(zip([col[0] for col in c.description], row)) for row in c.fetchall()]
    
    conn.close()
    
    return render_template('teacher_assignments.html',
                         assignments=assignments,
                         session=session,
                         today=datetime.now().strftime('%Y-%m-%d'))

@app.route('/teacher/assignment/<int:assignment_id>')
def teacher_assignment_submissions(assignment_id):
    if 'user_id' not in session or session['user_type'] != 'teacher':
        flash('يجب تسجيل الدخول أولاً!', 'error')
        return redirect('/')
    
    session.modified = True
    conn = sqlite3.connect('data/database.db')
    c = conn.cursor()
    
    # التحقق من أن المعلم صاحب الواجب
    c.execute('SELECT * FROM assignments WHERE id = ? AND teacher_id = ?', (assignment_id, session['user_id']))
    assignment = c.fetchone()
    
    if not assignment:
        conn.close()
        flash('غير مسموح لك بالوصول إلى هذا الواجب!', 'error')
        return redirect('/teacher/assignments')
    
    assignment_dict = dict(zip([col[0] for col in c.description], assignment))
    
    # جلب حلول الطلاب
    c.execute('''SELECT s.*, u.name as student_name, u.grade, u.section 
                 FROM assignment_submissions s
                 JOIN users u ON s.student_id = u.id
                 WHERE s.assignment_id = ? ORDER BY s.submitted_at DESC''', (assignment_id,))
    submissions = [dict(zip([col[0] for col in c.description], row)) for row in c.fetchall()]
    
    conn.close()
    
    return render_template('teacher_assignment_submissions.html',
                         assignment=assignment_dict,
                         submissions=submissions,
                         session=session)

@app.route('/teacher/students')
def teacher_students():
    if 'user_id' not in session or session['user_type'] != 'teacher':
        flash('يجب تسجيل الدخول أولاً!', 'error')
        return redirect('/')
    
    session.modified = True
    conn = sqlite3.connect('data/database.db')
    c = conn.cursor()
    
    c.execute('SELECT * FROM users WHERE user_type = "student" ORDER BY grade, section, name')
    students = [dict(zip([col[0] for col in c.description], row)) for row in c.fetchall()]
    
    conn.close()
    
    return render_template('teacher_students.html',
                         students=students,
                         session=session)

@app.route('/teacher/room/<int:room_id>')
def teacher_room_chat(room_id):
    if 'user_id' not in session or session['user_type'] != 'teacher':
        flash('يجب تسجيل الدخول أولاً!', 'error')
        return redirect('/')
    
    session.modified = True
    conn = sqlite3.connect('data/database.db')
    c = conn.cursor()
    
    # التحقق من أن المعلم صاحب الغرفة
    c.execute('''SELECT r.* FROM rooms r
                 WHERE r.id = ? AND r.teacher_id = ? AND r.is_active = 1''',
              (room_id, session['user_id']))
    room = c.fetchone()
    
    if not room:
        conn.close()
        flash('غير مسموح لك بالدخول إلى هذه الغرفة!', 'error')
        return redirect('/teacher/rooms')
    
    room_dict = dict(zip([col[0] for col in c.description], room))
    
    # جلب الطلاب في الغرفة
    c.execute('''SELECT u.id, u.name, u.grade, u.section FROM users u
                 JOIN room_students rs ON u.id = rs.student_id
                 WHERE rs.room_id = ? AND u.is_active = 1''', (room_id,))
    students = [dict(zip([col[0] for col in c.description], row)) for row in c.fetchall()]
    
    # جلب رسائل الدردشة
    c.execute('''SELECT cm.*, u.user_type FROM chat_messages cm
                 JOIN users u ON cm.user_id = u.id
                 WHERE cm.room_id = ? ORDER BY cm.sent_at DESC LIMIT 50''', (room_id,))
    messages = [dict(zip([col[0] for col in c.description], row)) for row in c.fetchall()]
    messages.reverse()  # لعرض الرسائل من الأقدم إلى الأحدث
    
    conn.close()
    
    return render_template('teacher_room_chat.html',
                         room=room_dict,
                         students=students,
                         messages=messages,
                         session=session)

# لوحة الإداري
@app.route('/admin/dashboard')
def admin_dashboard():
    if 'user_id' not in session or session['user_type'] != 'admin':
        flash('يجب تسجيل الدخول أولاً!', 'error')
        return redirect('/')
    
    session.modified = True
    stats = get_user_stats(session['user_id'], 'admin')
    
    conn = sqlite3.connect('data/database.db')
    c = conn.cursor()
    
    # آخر المستخدمين
    c.execute('SELECT * FROM users WHERE user_type != "admin" ORDER BY created_at DESC LIMIT 10')
    recent_users = [dict(zip([col[0] for col in c.description], row)) for row in c.fetchall()]
    
    # آخر الغرف
    c.execute('''SELECT r.*, u.name as teacher_name FROM rooms r
                 JOIN users u ON r.teacher_id = u.id
                 ORDER BY r.created_at DESC LIMIT 5''')
    recent_rooms = [dict(zip([col[0] for col in c.description], row)) for row in c.fetchall()]
    
    conn.close()
    
    return render_template('admin_dashboard.html',
                         stats=stats,
                         recent_users=recent_users,
                         recent_rooms=recent_rooms,
                         session=session)

@app.route('/admin/users')
def admin_users():
    if 'user_id' not in session or session['user_type'] != 'admin':
        flash('يجب تسجيل الدخول أولاً!', 'error')
        return redirect('/')
    
    session.modified = True
    conn = sqlite3.connect('data/database.db')
    c = conn.cursor()
    
    c.execute('SELECT * FROM users WHERE user_type != "admin" ORDER BY user_type, name')
    users = [dict(zip([col[0] for col in c.description], row)) for row in c.fetchall()]
    
    conn.close()
    
    return render_template('admin_users.html',
                         users=users,
                         session=session)

# APIs
@app.route('/api/create_room', methods=['POST'])
def api_create_room():
    if 'user_id' not in session or session['user_type'] != 'teacher':
        return jsonify({'success': False, 'error': 'غير مصرح'})
    
    name = request.form['name']
    subject = request.form['subject']
    grade = request.form['grade']
    section = request.form['section']
    description = request.form.get('description', '')
    
    try:
        code = generate_room_code()
        conn = sqlite3.connect('data/database.db')
        c = conn.cursor()
        
        c.execute('''INSERT INTO rooms (name, subject, grade, section, code, teacher_id, description)
                     VALUES (?, ?, ?, ?, ?, ?, ?)''',
                  (name, subject, grade, section, code, session['user_id'], description))
        conn.commit()
        session.modified = True
        conn.close()
        
        return jsonify({'success': True, 'code': code})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/join_room', methods=['POST'])
def api_join_room():
    if 'user_id' not in session or session['user_type'] != 'student':
        return jsonify({'success': False, 'error': 'غير مصرح'})
    
    room_code = request.form['room_code']
    
    conn = sqlite3.connect('data/database.db')
    c = conn.cursor()
    
    c.execute('SELECT * FROM rooms WHERE code = ? AND is_active = 1', (room_code,))
    room = c.fetchone()
    
    if not room:
        conn.close()
        return jsonify({'success': False, 'error': 'رمز الغرفة غير صحيح'})
    
    # التحقق من التسجيل المسبق
    c.execute('SELECT * FROM room_students WHERE room_id = ? AND student_id = ?', (room[0], session['user_id']))
    if c.fetchone():
        conn.close()
        return jsonify({'success': False, 'error': 'أنت مسجل في هذه الغرفة مسبقاً'})
    
    try:
        c.execute('INSERT INTO room_students (room_id, student_id) VALUES (?, ?)', (room[0], session['user_id']))
        conn.commit()
        session.modified = True
        conn.close()
        return jsonify({'success': True, 'room_name': room[1]})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/send_message', methods=['POST'])
def api_send_message():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'غير مصرح'})
    
    room_id = request.form['room_id']
    message = request.form['message']
    
    conn = sqlite3.connect('data/database.db')
    c = conn.cursor()
    
    try:
        c.execute('''INSERT INTO chat_messages (room_id, user_id, user_name, message)
                     VALUES (?, ?, ?, ?)''',
                  (room_id, session['user_id'], session['name'], message))
        conn.commit()
        
        # جلب الرسالة الجديدة مع معلومات المستخدم
        c.execute('''SELECT cm.*, u.user_type FROM chat_messages cm
                     JOIN users u ON cm.user_id = u.id
                     WHERE cm.id = last_insert_rowid()''')
        new_message = c.fetchone()
        
        session.modified = True
        conn.close()
        
        if new_message:
            message_dict = dict(zip([col[0] for col in c.description], new_message))
            return jsonify({'success': True, 'message': message_dict})
        else:
            return jsonify({'success': True})
            
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/get_messages/<int:room_id>')
def api_get_messages(room_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'غير مصرح'})
    
    # إضافة timestamp لمنع التخزين المؤقت
    timestamp = request.args.get('t', '')
    
    conn = sqlite3.connect('data/database.db')
    c = conn.cursor()
    
    c.execute('''SELECT cm.*, u.user_type FROM chat_messages cm
                 JOIN users u ON cm.user_id = u.id
                 WHERE cm.room_id = ? ORDER BY cm.sent_at DESC LIMIT 50''', (room_id,))
    messages = [dict(zip([col[0] for col in c.description], row)) for row in c.fetchall()]
    messages.reverse()  # لإرجاع الرسائل من الأقدم إلى الأحدث
    
    session.modified = True
    conn.close()
    
    return jsonify({'success': True, 'messages': messages})

@app.route('/api/create_assignment', methods=['POST'])
def api_create_assignment():
    if 'user_id' not in session or session['user_type'] != 'teacher':
        return jsonify({'success': False, 'error': 'غير مصرح'})
    
    title = request.form['title']
    description = request.form['description']
    subject = request.form['subject']
    grade = request.form['grade']
    section = request.form['section']
    due_date = request.form['due_date']
    total_marks = int(request.form['total_marks'])
    
    try:
        conn = sqlite3.connect('data/database.db')
        c = conn.cursor()
        
        c.execute('''INSERT INTO assignments 
                    (title, description, subject, grade, section, teacher_id, due_date, total_marks)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                  (title, description, subject, grade, section, session['user_id'], due_date, total_marks))
        conn.commit()
        session.modified = True
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/submit_assignment', methods=['POST'])
def api_submit_assignment():
    if 'user_id' not in session or session['user_type'] != 'student':
        return jsonify({'success': False, 'error': 'غير مصرح'})
    
    assignment_id = request.form['assignment_id']
    solution = request.form['solution']
    
    conn = sqlite3.connect('data/database.db')
    c = conn.cursor()
    
    # التحقق من التسليم المسبق
    c.execute('SELECT * FROM assignment_submissions WHERE assignment_id = ? AND student_id = ?',
              (assignment_id, session['user_id']))
    if c.fetchone():
        conn.close()
        return jsonify({'success': False, 'error': 'لقد قمت بتسليم هذا الواجب مسبقاً'})
    
    try:
        c.execute('''INSERT INTO assignment_submissions (assignment_id, student_id, solution)
                     VALUES (?, ?, ?)''', (assignment_id, session['user_id'], solution))
        conn.commit()
        session.modified = True
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/grade_submission', methods=['POST'])
def api_grade_submission():
    if 'user_id' not in session or session['user_type'] != 'teacher':
        return jsonify({'success': False, 'error': 'غير مصرح'})
    
    submission_id = request.form['submission_id']
    grade = int(request.form['grade'])
    feedback = request.form.get('feedback', '')
    
    try:
        conn = sqlite3.connect('data/database.db')
        c = conn.cursor()
        
        # التحقق من أن المعلم صاحب الواجب
        c.execute('''SELECT a.teacher_id FROM assignments a
                     JOIN assignment_submissions s ON a.id = s.assignment_id
                     WHERE s.id = ?''', (submission_id,))
        result = c.fetchone()
        
        if not result or result[0] != session['user_id']:
            conn.close()
            return jsonify({'success': False, 'error': 'غير مصرح لك بتصحيح هذا الحل'})
        
        c.execute('''UPDATE assignment_submissions 
                     SET grade = ?, feedback = ?, status = "graded", graded_at = CURRENT_TIMESTAMP
                     WHERE id = ?''', (grade, feedback, submission_id))
        conn.commit()
        session.modified = True
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/get_student_assignments')
def api_get_student_assignments():
    if 'user_id' not in session or session['user_type'] != 'student':
        return jsonify({'success': False, 'error': 'غير مصرح'})
    
    # إضافة timestamp لمنع التخزين المؤقت
    timestamp = request.args.get('t', '')
    
    conn = sqlite3.connect('data/database.db')
    c = conn.cursor()
    
    c.execute('''SELECT a.*, u.name as teacher_name FROM assignments a
                 JOIN users u ON a.teacher_id = u.id
                 WHERE a.grade = ? AND a.section = ?
                 ORDER BY a.due_date''', (session['grade'], session['section']))
    assignments = [dict(zip([col[0] for col in c.description], row)) for row in c.fetchall()]
    
    # إضافة حالة التسليم
    for assignment in assignments:
        c.execute('''SELECT status, grade, feedback FROM assignment_submissions 
                     WHERE assignment_id = ? AND student_id = ?''',
                  (assignment['id'], session['user_id']))
        submission = c.fetchone()
        if submission:
            assignment['submission_status'] = submission[0]
            assignment['submission_grade'] = submission[1]
            assignment['feedback'] = submission[2]
        else:
            assignment['submission_status'] = 'not_submitted'
            assignment['submission_grade'] = None
            assignment['feedback'] = None
    
    session.modified = True
    conn.close()
    
    return jsonify({'success': True, 'assignments': assignments})

@app.route('/api/get_students')
def api_get_students():
    if 'user_id' not in session or session['user_type'] != 'teacher':
        return jsonify({'success': False, 'error': 'غير مصرح'})
    
    # إضافة timestamp لمنع التخزين المؤقت
    timestamp = request.args.get('t', '')
    
    conn = sqlite3.connect('data/database.db')
    c = conn.cursor()
    
    c.execute('SELECT * FROM users WHERE user_type = "student" ORDER BY grade, section, name')
    students = [dict(zip([col[0] for col in c.description], row)) for row in c.fetchall()]
    
    session.modified = True
    conn.close()
    
    return jsonify({'success': True, 'students': students})

@app.route('/logout')
def logout():
    session.clear()
    flash('تم تسجيل الخروج بنجاح!', 'success')
    return redirect('/')

if __name__ == '__main__':
    init_db()
    print("=" * 60)
    print("🎓 النظام التعليمي الإلكتروني - مدرسة الراشد")
    print("=" * 60)
    print("🌐 الخادم يعمل على: http://localhost:5000")
    print("🔑 حساب المدير: admin / admin123")
    print("=" * 60)
    print("📝 صنع بواسطة: راشد رائد الجراونه مع عبد الرحمان اكرم دنديس")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=False)