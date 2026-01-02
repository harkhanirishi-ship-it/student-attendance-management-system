print("APP.PY FILE RUNNING")
from datetime import date, timedelta
from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import date

app = Flask(__name__)
app.secret_key = "attendance_secret"


def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = sqlite3.connect('database.db')

    conn.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        roll TEXT,
        class TEXT
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        date TEXT,
        status TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()


# ---------- LOGIN ----------
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] == 'admin' and request.form['password'] == 'admin123':
            session['user'] = 'admin'
            return redirect('/dashboard')
        else:
            return "Invalid Login"
    return render_template('login.html')


# ---------- DASHBOARD ----------
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/')
    return render_template('dashboard.html')


# ---------- ADD STUDENT ----------
@app.route('/add_student', methods=['GET', 'POST'])
def add_student():
    erro = None
    if request.method == 'POST':
        conn = get_db_connection()

        name = request.form['name']
        roll = request.form['roll']
        student_class = request.form['class']
        existing = conn.execute(
            "SELECT * FROM students WHERE roll = ?",
            (roll,)
        ).fetchone()

        if existing:
           error_msg = f"Roll number '{roll}' already exists!"
           conn.close()
           return render_template('add_student.html', existing=error_msg)
        else:
          conn.execute(       
            "INSERT INTO students (name, roll, class) VALUES (?, ?, ?)",
            (request.form['name'], request.form['class'],request.form['roll'])
        )
        conn.commit()
        conn.close()
       
        return redirect('/dashboard')   
    return render_template('add_student.html',)


@app.route('/mark_attendance', methods=['GET', 'POST'])
def mark_attendance():
    today = str(date.today())
    conn = get_db_connection()
    students = conn.execute("SELECT * FROM students").fetchall()

    # POST request → fill attendance
    if request.method == 'POST':
        for student in students:
            status = request.form.get(str(student['id']))

            # check if this student's attendance already exists today
            existing = conn.execute(
                "SELECT * FROM attendance WHERE student_id = ? AND date = ?",
                (student['id'], today)
            ).fetchone()

            if not existing:
                conn.execute(
                    "INSERT INTO attendance (student_id, date, status) VALUES (?, ?, ?)",
                    (student['id'], today, status)
                )

        conn.commit()
        conn.close()
        return redirect('/dashboard')

    # GET request → display form
    # pass a flag per student if already marked (optional)
    attendance_today = conn.execute(
        "SELECT student_id FROM attendance WHERE date = ?", (today,)
    ).fetchall()
    marked_ids = [r['student_id'] for r in attendance_today]

    conn.close()
    return render_template(
        'mark_attendance.html',
        students=students,
        today=today,
        marked_ids=marked_ids  # use in template to disable already marked students
    )



# ---------- VIEW ATTENDANCE ----------
@app.route('/view_attendance', methods=['GET', 'POST'])
def view_attendance():
    conn = get_db_connection()
    records = []

    if request.method == 'POST':
        selected_date = request.form['date']
        records = conn.execute("""
            SELECT students.name, students.roll, students.class,
                   attendance.date, attendance.status
            FROM attendance
            JOIN students ON students.id = attendance.student_id
            WHERE attendance.date = ?
        """, (selected_date,)).fetchall()

    conn.close()
    return render_template('view_attendance.html', records=records)


# ---------- LOGOUT ----------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/student_summary', methods=['GET', 'POST'])
def student_summary():
    conn = get_db_connection()

    # saare students dropdown ke liye
    students = conn.execute("SELECT * FROM students").fetchall()

    summary = None
    selected_student = None

    if request.method == 'POST':
        student_id = request.form['student_id']
        selected_student = student_id

        one_year_ago = str(date.today() - timedelta(days=365))

        records = conn.execute("""
            SELECT status, COUNT(*) as count
            FROM attendance
            WHERE student_id = ?
            AND date >= ?
            GROUP BY status
        """, (student_id, one_year_ago)).fetchall()

        present = 0
        absent = 0

        for r in records:
            if r['status'] == 'Present':
                present = r['count']
            elif r['status'] == 'Absent':
                absent = r['count']

        summary = {
            'present': present,
            'absent': absent,
            'total': present + absent
        }

    conn.close()

    return render_template(
        'student_summary.html',
        students=students,
        summary=summary,
        selected_student=selected_student
    )

@app.route('/attendance_result', methods=['GET', 'POST'])
def attendance_result():
    conn = get_db_connection()

    
    students = conn.execute("SELECT * FROM students").fetchall()

    result_data = None

    if request.method == 'POST':
        student_id = request.form['student_id']

        # 🔹 selected student ke attendance records
        records = conn.execute("""
            SELECT status FROM attendance
            WHERE student_id = ?
        """, (student_id,)).fetchall()

        present = 0
        absent = 0

        # 🔹 present / absent count
        for r in records:
            if r['status'] == 'Present':
                present += 1
            elif r['status'] == 'Absent':
                absent += 1

        total_days = present + absent

        if total_days > 0:
            percentage = (present / total_days) * 100
        else:
            percentage = 0

        
        if percentage >= 75:
            final_result = 'PASS'
        else:
            final_result = 'FAIL'

        result_data = {
            'present': present,
            'absent': absent,
            'total': total_days,
            'percentage': round(percentage, 2),
            'result': final_result
        }

    conn.close()

    return render_template(
        'attendance_result.html',
        students=students,
        result_data=result_data
    )




if __name__ == '__main__':
    app.run(debug=True)

from datetime import date, timedelta

