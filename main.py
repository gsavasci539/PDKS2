from flask import Flask, request, jsonify
import pyodbc
import jwt
import datetime
import bcrypt
from functools import wraps
from flask_socketio import SocketIO
from datetime import datetime, timedelta
from flask import Flask
from flask_cors import CORS



app = Flask(__name__)
socketio = SocketIO(app)
CORS(app)
app.config['SECRET_KEY'] = 'your_secret_key'

DB_CONN = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=104.247.167.130,1433;DATABASE=yazil112_learning;UID=yazil112_test2;PWD=GURkan5391"


def db_connect():
    return pyodbc.connect(DB_CONN)

# JWT Yetkilendirme Decorator
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token eksik!'}), 403
        try:
            jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        except:
            return jsonify({'message': 'Geçersiz token!'}), 403
        return f(*args, **kwargs)
    return decorated

# Personel Bilgileri
@app.route('/employees', methods=['POST'])
def add_employee():
    data = request.json
    first_name = data.get('first_name')
    employee_id = data.get('employee_id')
    last_name = data.get('last_name')
    department = data.get('department')
    position = data.get('position')
    email = data.get('email')
    phone = data.get('phone')
    hire_date = data.get('hire_date')
    status = data.get('status')
    base_salary = data.get('base_salary')

    conn = db_connect()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO Employees (EmployeeId, FirstName, LastName, Department, Position, Email, Phone, HireDate, Status, BaseSalary) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (employee_id, first_name, last_name, department, position, email, phone, hire_date, status, base_salary))
            conn.commit()
            return jsonify({"message": "Employee added successfully"}), 201
        except pyodbc.Error as e:
            conn.rollback()
            return jsonify({"error": str(e)}), 500
        finally:
            cursor.close()
            conn.close()
    else:
        return jsonify({"error": "Database connection failed"}), 500

@app.route('/employees', methods=['GET'])
def get_employees():
    conn = db_connect()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM Employees")
            columns = [column[0] for column in cursor.description] #get column names
            employees = [dict(zip(columns, row)) for row in cursor.fetchall()]

            return jsonify(employees)
        except pyodbc.Error as e:
            return jsonify({"error": str(e)}), 500
        finally:
            cursor.close()
            conn.close()
    else:
        return jsonify({"error": "Database connection failed"}), 500

@app.route('/employees/<int:employee_id>', methods=['PUT'])
def update_employee(employee_id):
    data = request.json
    conn = db_connect()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE Employees
                SET EmployeeId = ?, FirstName = ?, LastName = ?, Department = ?, Position = ?, Email = ?, Phone = ?, HireDate = ?, Status = ?, BaseSalary = ?
                WHERE ID = ?
            """, (
                data.get('employee_id'), data.get('first_name'), data.get('last_name'), data.get('department'),
                data.get('position'), data.get('email'), data.get('phone'),
                data.get('hire_date'), data.get('status'), data.get('base_salary'), employee_id
            ))
            conn.commit()
            return jsonify({"message": "Employee updated successfully"})
        except pyodbc.Error as e:
            conn.rollback()
            return jsonify({"error": str(e)}), 500
        finally:
            cursor.close()
            conn.close()
    else:
        return jsonify({"error": "Database connection failed"}), 500

@app.route('/employees/<int:employee_id>', methods=['DELETE'])
def delete_employee(employee_id):
    conn = db_connect()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM Employees WHERE ID = ?", (employee_id,))
            conn.commit()
            return jsonify({"message": "Employee deleted successfully"})
        except pyodbc.Error as e:
            conn.rollback()
            return jsonify({"error": str(e)}), 500
        finally:
            cursor.close()
            conn.close()
    else:
        return jsonify({"error": "Database connection failed"}), 500



# İzin Talebi Yönetimi (Geliştirilmiş)
@app.route('/leave-requests', methods=['POST'])
def add_leave_request():
    data = request.get_json()
    print(f"Alınan veri: {data}")  # Eklenen yazdırma ifadesi
    employee_id = data.get('employee_id')
    leave_type = data.get('leave_type')
    start_date_str = data.get('start_date')
    end_date_str = data.get('end_date')
    status = data.get('status')

    if not all([employee_id, leave_type, start_date_str, end_date_str, status]):
        return jsonify({"error": "Gerekli alanlar eksik"}), 400

    try:
        # Tarih dizelerini datetime.datetime nesnelerine dönüştür
        start_date = datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%dT%H:%M')

        conn = db_connect()
        if conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO LeaveRequests (EmployeeID, LeaveType, StartDate, EndDate, Status)
                VALUES (?, ?, ?, ?, ?)
            """, (employee_id, leave_type, start_date, end_date, status))
            conn.commit()
            conn.close()
            return jsonify({"message": "İzin isteği başarıyla eklendi"}), 201
        else:
            return jsonify({"error": "Veritabanı bağlantısı başarısız"}), 500

    except ValueError:
        return jsonify({"error": "Geçersiz tarih formatı.YYYY-MM-DDTHH:MM kullanın"}), 400  # Hata mesajını güncelledim
    except pyodbc.Error as ex:
        sqlstate = ex.args[0]
        print(f"Veritabanı hatası: {ex}, SQLSTATE: {sqlstate}")
        if conn:
            conn.rollback()
            conn.close()
        return jsonify({"error": "Veritabanı hatası oluştu"}), 500

@app.route('/leave-requests', methods=['GET'])
def get_leave_requests():
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            lr.ID AS LeaveRequestID,
            e.EmployeeID,
            e.FirstName,
            e.LastName,
            lr.LeaveType,
            lr.StartDate,
            lr.EndDate,
            lr.Status AS LeaveRequestStatus
        FROM
            LeaveRequests lr
        JOIN
            Employees e ON CAST(lr.EmployeeID AS NVARCHAR(255)) = CAST(e.ID AS NVARCHAR(255));
    """)
    leave_requests = cursor.fetchall()
    conn.close()

    result = []
    columns = [column[0] for column in cursor.description]
    for row in leave_requests:
        result.append(dict(zip(columns, row)))

    return jsonify(result)
@app.route('/leave-requests/<int:request_id>', methods=['PUT'])
def update_leave_request(request_id):
    data = request.get_json()
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE LeaveRequests
        SET EmployeeID = ?, LeaveType = ?, StartDate = ?, EndDate = ?, Status = ?
        WHERE ID = ?
    """, (
        data.get('employee_id'),
        data.get('leave_type'),
        data.get('start_date'),
        data.get('end_date'),
        data.get('status'),
        request_id
    ))
    conn.commit()
    conn.close()
    return jsonify({"message": "Leave request updated successfully"})

@app.route('/leave-requests/<int:request_id>', methods=['DELETE'])
def delete_leave_request(request_id):
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM LeaveRequests WHERE ID = ?", (request_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Leave request deleted successfully"})

# Giriş İşlemleri (Login)
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password').encode('utf-8')
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT ID, PasswordHash FROM Employees WHERE Email=?", (email,))
    user = cursor.fetchone()
    conn.close()

    if user and bcrypt.checkpw(password, user[1].encode('utf-8')):
        token = jwt.encode({'user_id': user[0], 'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=12)}, app.config['SECRET_KEY'])
        return jsonify({'token': token})
    return jsonify({'message': 'Geçersiz giriş!'}), 401

@app.route('/attendance', methods=['GET'])
def get_all_attendance():
    conn = db_connect()
    cursor = conn.cursor()

    # Fetch all attendance records
    cursor.execute("SELECT * FROM Attendance")
    all_records = cursor.fetchall()

    # Convert each row to a dictionary
    columns = [column[0] for column in cursor.description]  # Get column names
    attendance_list = [dict(zip(columns, row)) for row in all_records]

    conn.close()

    return jsonify({'attendance': attendance_list}), 200


@app.route('/attendance/entry', methods=['POST'])
def add_entry():
    data = request.json
    employee_id = data.get('employee_id')
    entry_time = data.get('entry_time')

    conn = db_connect()
    cursor = conn.cursor()

    if entry_time:
        entry_date = entry_time.split('T')[0]
        print(f"Entry Date: {entry_date}")

        cursor.execute("""
            SELECT * FROM Attendance
            WHERE EmployeeID = ? AND CAST(EntryTime AS DATE) = ? AND ExitTime IS NULL
        """, (employee_id, entry_date))
        existing_record = cursor.fetchone()

        print(f"Existing Entry Record: {existing_record}")

        if existing_record:
            cursor.execute("""
                UPDATE Attendance
                SET EntryTime = ?
                WHERE EmployeeID = ? AND CAST(EntryTime AS DATE) = ? AND ExitTime IS NULL
            """, (entry_time, employee_id, entry_date))
            message = 'Giriş kaydı güncellendi!'
        else:
            cursor.execute("""
                INSERT INTO Attendance (EmployeeID, EntryTime, ExitTime)
                VALUES (?, ?, ?)
            """, (employee_id, entry_time, None))
            message = 'Giriş kaydedildi!'

        conn.commit()
        conn.close()

        return jsonify({'message': message}), 200  # Returning a valid JSON response
    else:
        return jsonify({'error': 'Invalid entry time'}), 400  # If entry_time is no


@app.route('/attendance/exit', methods=['POST'])
def add_exit():
    data = request.json
    employee_id = str(data.get('employee_id'))  # Ensure employee_id is a string
    exit_time = data.get('exit_time')

    # Eğer exit_time verilmemişse hata mesajı döndür
    if not exit_time:
        return jsonify({'error': 'Exit time is required'}), 400

    conn = db_connect()
    cursor = conn.cursor()

    exit_date = exit_time.split('T')[0]  # Assuming exit_time is in ISO format
    print(f"Exit Date: {exit_date}")  # Debugging step to print exit date

    # Check if there is an existing record for the same employee and date (ExitTime is NULL)
    cursor.execute("""

        SELECT * FROM Attendance
        WHERE EmployeeID = ? AND CAST(EntryTime AS DATE) = ? AND ExitTime IS NULL
    """, (employee_id, exit_date))  # Ensure employee_id is treated as a string
    existing_record = cursor.fetchone()

    print(f"Existing Exit Record: {existing_record}")  # Debugging step to print existing record

    if existing_record:
        # If record exists, update the exit time
        cursor.execute("""

            UPDATE Attendance
            SET ExitTime = ?
            WHERE EmployeeID = ? AND CAST(EntryTime AS DATE) = ? AND ExitTime IS NULL
        """, (exit_time, employee_id, exit_date))
        message = 'Çıkış kaydı güncellendi!'
    else:
        # If no existing record, add an exit record
        cursor.execute("""
            INSERT INTO Attendance (EmployeeID, EntryTime, ExitTime)
            VALUES (?, NULL, ?)
        """, (employee_id, exit_time))
        message = 'Çıkış kaydedildi!'

    conn.commit()
    conn.close()

    return jsonify({'message': message})

@app.route('/attendance/total_work_time/<string:employee_id>', methods=['GET'])
def get_total_work_time_by_employee(employee_id):
    conn = db_connect()
    cursor = conn.cursor()

    # Get today's date for daily, weekly and monthly calculations
    today = datetime.today()
    start_of_today = today.replace(hour=0, minute=0, second=0, microsecond=0)
    start_of_week = start_of_today - timedelta(days=today.weekday())  # Start of the week (Monday)
    start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Ensure `today` has no time part for the daily calculation
    end_of_today = today.replace(hour=23, minute=59, second=59, microsecond=999999)

    # SQL query to calculate total work time for a specific employee for today, this week, and this month
    query = """
    SELECT 
        EmployeeID,
        SUM(CASE 
            WHEN [EntryTime] >= ? AND [ExitTime] <= ? THEN DATEDIFF(SECOND, [EntryTime], [ExitTime])
            ELSE 0
        END) AS TotalToday,
        SUM(CASE 
            WHEN [EntryTime] >= ? AND [ExitTime] <= ? THEN DATEDIFF(SECOND, [EntryTime], [ExitTime])
            ELSE 0
        END) AS TotalThisWeek,
        SUM(CASE 
            WHEN [EntryTime] >= ? AND [ExitTime] <= ? THEN DATEDIFF(SECOND, [EntryTime], [ExitTime])
            ELSE 0
        END) AS TotalThisMonth
    FROM Attendance
    WHERE EmployeeID = ? AND EntryTime IS NOT NULL AND ExitTime IS NOT NULL
    GROUP BY EmployeeID
    """

    cursor.execute(query, (start_of_today, end_of_today, start_of_week, today, start_of_month, today, employee_id))
    result = cursor.fetchone()
    conn.close()

    def format_time(seconds):
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        return f"{hours} hours {minutes} minutes {seconds} seconds"

    if result:
        return jsonify({
            'EmployeeID': result[0],
            'TotalToday': format_time(result[1]),
            'TotalThisWeek': format_time(result[2]),
            'TotalThisMonth': format_time(result[3])
        }), 200
    else:
        return jsonify({'message': 'Çalışan için kayıt bulunamadı veya eksik zaman bilgisi var.'}), 404


@app.route('/calculate-salary', methods=['POST'])
def calculate_salary():
    """Çalışanın maaşını hesaplar ve veritabanına kaydeder."""
    data = request.json
    employee_id = str(data.get('employee_id'))
    base_salary = data.get('base_salary')
    overtime_rate = data.get('overtime_rate')
    overtime_hours = data.get('overtime_hours')

    if not all([employee_id, base_salary, overtime_rate, overtime_hours]):
        return jsonify({'message': 'Eksik veri'}), 400

    total_salary = base_salary + (overtime_hours * overtime_rate)
    total_salary = round(total_salary, 2) # Maaşı virgülden sonra 2 haneye yuvarla

    conn = db_connect()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT ID FROM yazil112_test2.Employees WHERE ID = ?", employee_id)
            existing_employee = cursor.fetchone()

            if existing_employee:
                cursor.execute("INSERT INTO Salaries (EmployeeID, BaseSalary, OvertimeRate, OvertimeHours, TotalSalary) VALUES (?, ?, ?, ?, ?)",
                               (employee_id, base_salary, overtime_rate, overtime_hours, total_salary))
                conn.commit()
                return jsonify({'message': 'Maaş başarıyla hesaplandı.', 'total_salary': total_salary}), 201
            else:
                return jsonify({'message': f'{employee_id} ID\'li çalışan bulunamadı.'}), 404

        except pyodbc.Error as ex:
            return jsonify({'message': 'Veritabanı hatası.'}), 500
        finally:
            conn.close()
    else:
        return jsonify({'message': 'Veritabanı bağlantısı başarısız.'}), 500

def get_overtime_hours(employee_id):
    conn = db_connect()
    if conn is None:
        return {"error": "Database connection failed"}, 500

    try:
        cursor = conn.cursor()

        sql_query = """
        SELECT
            e.EmployeeID,
            e.FirstName,
            e.LastName,
            FORMAT(a.EntryTime, 'yyyy-MM') AS Month,
            a.EntryTime,
            a.ExitTime
        FROM
            yazil112_learning.yazil112_test2.Employees e
        JOIN
            yazil112_learning.yazil112_test2.Attendance a ON e.EmployeeID = a.EmployeeID
        WHERE
            e.EmployeeID = ?
        ORDER BY
            FORMAT(a.EntryTime, 'yyyy-MM'), a.EntryTime;
        """

        cursor.execute(sql_query, employee_id)
        rows = cursor.fetchall()

        monthly_data = {}
        for row in rows:
            emp_id = row.EmployeeID
            first_name = row.FirstName
            last_name = row.LastName
            month = row.Month
            entry_time = row.EntryTime
            exit_time = row.ExitTime

            if month not in monthly_data:
                monthly_data[month] = {
                    'EmployeeID': emp_id,
                    'FirstName': first_name,
                    'LastName': last_name,
                    'Month': month,
                    'total_working_seconds': 0
                }

            time_difference = exit_time - entry_time
            monthly_data[month]['total_working_seconds'] += time_difference.total_seconds()

        overtime_data = []
        for month, data in monthly_data.items():
            total_working_hours = data['total_working_seconds'] / 3600.0
            # Calculate total allowed break time for the month (assuming 20 working days)
            # This is a simplification, you might need a more accurate way to determine working days
            total_break_hours = 20 * 1.5
            net_working_hours = total_working_hours - total_break_hours

            overtime_hours = max(0, net_working_hours - 160.0)

            if overtime_hours > 0:
                overtime_data.append({
                    'EmployeeID': data['EmployeeID'],
                    'FirstName': data['FirstName'],
                    'LastName': data['LastName'],
                    'Month': data['Month'],
                    'OvertimeHours': round(overtime_hours, 2)
                })

        return overtime_data

    except pyodbc.Error as ex:
        sqlstate = ex.args[0]
        print(sqlstate)
        return {"error": "Database error"}, 500
    finally:
        if 'cursor' in locals() and cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


@app.route('/attendance/<employee_id>', methods=['GET'])
def get_overtime(employee_id):
    overtime_data = get_overtime_hours(employee_id)
    if "error" in overtime_data:
        return jsonify(overtime_data), 500
    return jsonify(overtime_data), 200

@app.route('/employee/<string:employee_id>/base-salary', methods=['GET'])
def get_base_salary(employee_id):
    """Belirli bir çalışanın temel maaşını getirir."""
    conn = db_connect()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT BaseSalary FROM Employees WHERE ID = ?", employee_id)
            result = cursor.fetchone()

            if result:
                return jsonify({'base_salary': result[0]}), 200
            else:
                return jsonify({'message': f'{employee_id} ID\'li çalışan bulunamadı.'}), 404
        except pyodbc.Error as ex:

            return jsonify({'message': 'Veritabanı hatası.'}), 500
        finally:
            conn.close()
    else:
        return jsonify({'message': 'Veritabanı bağlantısı başarısız.'}), 500

@app.route('/employee', methods=['GET'])
def get_employee():
    """Tüm çalışanların listesini getirir."""
    conn = db_connect()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT ID, FirstName, LastName FROM yazil112_test2.Employees")
            employees = [{'employee_id': row.ID, 'employee_name': f'{row.FirstName} {row.LastName}'} for row in cursor.fetchall()]
            return jsonify(employees), 200
        except pyodbc.Error as ex:

            return jsonify({'message': 'Veritabanı hatası.'}), 500
        finally:
            conn.close()
    else:
        return jsonify({'message': 'Veritabanı bağlantısı başarısız.'}), 500

@app.route('/rfidcards', methods=['GET'])
def get_rfid_cards():
    """RFID kartlarının listesini getirir. EmployeeID ile eşleşen kartlar hariç tutulur."""
    conn = db_connect()
    if conn:
        cursor = conn.cursor()
        try:
            # Önce EmployeeID'leri al
            cursor.execute("SELECT EmployeeID FROM Employees")
            employee_ids = {row.EmployeeID for row in cursor.fetchall()}

            # Sonra RFID kartlarını EmployeeID'lerde olmayanları filtreleyerek al
            cursor.execute("SELECT cardId FROM RFIDCards WHERE cardId NOT IN (SELECT EmployeeID FROM Employees WHERE EmployeeID IS NOT NULL)")
            rfid_cards = [{'card_id': row.cardId} for row in cursor.fetchall()]

            return jsonify(rfid_cards), 200
        except pyodbc.Error as ex:
            print(f"Veritabanı sorgu hatası: {ex}")
            return jsonify({'message': 'Veritabanı hatası.'}), 500
        finally:
            conn.close()
    else:
        return jsonify({'message': 'Veritabanı bağlantısı başarısız.'}), 500

@app.route('/rfidcard', methods=['GET'])
def get_rfid_code():
    """RFID kartlarının listesini getirir. EmployeeID ile eşleşen kartlar hariç tutulur."""
    conn = db_connect()
    if conn:
        cursor = conn.cursor()
        try:
            # Önce EmployeeID'leri al


            # Sonra RFID kartlarını EmployeeID'lerde olmayanları filtreleyerek al
            cursor.execute("SELECT * FROM RFIDCards")
            rfid_card = [{'card_id': row.cardId} for row in cursor.fetchall()]

            return jsonify(rfid_card), 200
        except pyodbc.Error as ex:
            print(f"Veritabanı sorgu hatası: {ex}")
            return jsonify({'message': 'Veritabanı hatası.'}), 500
        finally:
            conn.close()
    else:
        return jsonify({'message': 'Veritabanı bağlantısı başarısız.'}), 500

@app.route('/rfidcards/<string:card_id>', methods=['GET'])
def get_rfid_card(card_id):
    """Belirli bir RFID kartının detaylarını ve eşleşen çalışanın bilgilerini getirir."""
    conn = db_connect()
    if conn:
        cursor = conn.cursor()
        try:
            # Önce RFID kartını kontrol et
            cursor.execute("SELECT cardId FROM RFIDCards WHERE cardId=?", card_id)
            rfid_row = cursor.fetchone()
            if rfid_row:
                # RFID kartı bulundu, şimdi eşleşen çalışanı ara
                cursor.execute("""
                   SELECT e.EmployeeID, e.FirstName, e.LastName, rc.cardId
                    FROM Employees e
                    JOIN RFIDCards rc ON e.EmployeeID = rc.cardId
                    WHERE rc.cardId= ?
                """, card_id)
                employee_row = cursor.fetchone()
                if employee_row:
                    employee_info = {
                        'employee_id': employee_row.EmployeeID,
                        'first_name': employee_row.FirstName,
                        'last_name': employee_row.LastName,
                        'rfid_card_id': employee_row.cardId
                    }
                    return jsonify(employee_info), 200
                else:
                    return jsonify({'message': f'Bu RFID kartına ({card_id}) bağlı çalışan bulunamadı.'}), 404
            else:
                return jsonify({'message': f'RFID kartı ({card_id}) bulunamadı.'}), 404
        except pyodbc.Error as ex:
            print(f"Veritabanı sorgu hatası: {ex}")
            return jsonify({'message': 'Veritabanı hatası.'}), 500
        finally:
            conn.close()
    else:
        return jsonify({'message': 'Veritabanı bağlantısı başarısız.'}), 500


@app.route('/rfidcards', methods=['POST'])
def add_rfid_card():
    """Yeni bir RFID kartı ekler."""
    data = request.get_json()
    card_id = data.get('card_id')
    if not card_id:
        return jsonify({'message': 'card_id zorunlu.'}), 400

    conn = db_connect()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO RFIDCards (cardId) VALUES (?)", card_id)
            conn.commit()
            return jsonify({'message': 'RFID kartı başarıyla eklendi.', 'card_id': card_id}), 201
        except pyodbc.Error as ex:
            print(f"Veritabanı ekleme hatası: {ex}")
            return jsonify({'message': 'Veritabanı hatası: RFID kartı eklenirken bir sorun oluştu.'}), 500
        finally:
            conn.close()
    else:
        return jsonify({'message': 'Veritabanı bağlantısı başarısız.'}), 500

@app.route('/rfidcards/<string:card_id>', methods=['PUT'])
def update_rfid_card(card_id):
    """Belirli bir RFID kartının bilgilerini günceller."""
    data = request.get_json()
    new_card_id = data.get('card_id')
    if not new_card_id:
        return jsonify({'message': 'Yeni card_id zorunlu.'}), 400

    conn = db_connect()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE RFIDCards SET cardId=? WHERE cardId=?", new_card_id, card_id)
            conn.commit()
            if cursor.rowcount > 0:
                return jsonify({'message': 'RFID kartı başarıyla güncellendi.', 'card_id': new_card_id}), 200
            else:
                return jsonify({'message': 'Güncellenecek RFID kartı bulunamadı.'}), 404
        except pyodbc.Error as ex:
            print(f"Veritabanı güncelleme hatası: {ex}")
            return jsonify({'message': 'Veritabanı hatası: RFID kartı güncellenirken bir sorun oluştu.'}), 500
        finally:
            conn.close()
    else:
        return jsonify({'message': 'Veritabanı bağlantısı başarısız.'}), 500

@app.route('/rfidcards/<string:card_id>', methods=['DELETE'])
def delete_rfid_card(card_id):
    """Belirli bir RFID kartını siler."""
    conn = db_connect()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM RFIDCards WHERE cardId=?", card_id)
            conn.commit()
            if cursor.rowcount > 0:
                return jsonify({'message': 'RFID kartı başarıyla silindi.', 'card_id': card_id}), 200
            else:
                return jsonify({'message': 'Silinecek RFID kartı bulunamadı.'}), 404
        except pyodbc.Error as ex:
            print(f"Veritabanı silme hatası: {ex}")
            return jsonify({'message': 'Veritabanı hatası: RFID kartı silinirken bir sorun oluştu.'}), 500
        finally:
            conn.close()
    else:
        return jsonify({'message': 'Veritabanı bağlantısı başarısız.'}), 500
# Yüz Tanıma Giriş
@app.route('/face-login', methods=['POST'])
def face_login():
    return jsonify({'message': 'Yüz tanıma henüz entegre edilmedi. Demo endpoint.'})

# QR Kod Giriş
@app.route('/qr-login', methods=['POST'])
def qr_login():
    return jsonify({'message': 'QR kod okuma demo endpoint. Gerçek uygulama cihazla entegre edilir.'})

# Eğitim Sertifika Yönetimi

@app.route('/certificates', methods=['POST'])
def add_certificate():
    data = request.json
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Certificates (EmployeeID, Title, DateEarned, ExpiryDate)
        VALUES (?, ?, ?, ?)
    """, (data['employee_id'], data['title'], data['date_earned'], data['expiry_date']))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Sertifika eklendi'}), 201

@app.route('/certificates', methods=['GET'])
def get_certificates():
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT ID, EmployeeID, Title, DateEarned, ExpiryDate FROM Certificates")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([
        {
            'ID': row[0],
            'EmployeeID': row[1],
            'Title': row[2],
            'DateEarned': row[3],
            'ExpiryDate': row[4]
        } for row in rows
    ])

@app.route('/certificates/<int:certificate_id>', methods=['PUT'])
def update_certificate(certificate_id):
    data = request.json
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE Certificates 
        SET EmployeeID = ?, Title = ?, DateEarned = ?, ExpiryDate = ?
        WHERE ID = ?
    """, (
        data['employee_id'],
        data['title'],
        data['date_earned'],
        data['expiry_date'],
        certificate_id
    ))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Sertifika güncellendi'})

@app.route('/certificates/<int:certificate_id>', methods=['DELETE'])
def delete_certificate(certificate_id):
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Certificates WHERE ID = ?", (certificate_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Sertifika silindi'})

# Sistem Ayarları API'si
@app.route('/system-settings', methods=['GET'])
def get_system_settings():
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM SystemSettings")
    settings = cursor.fetchall()
    conn.close()

    settings_dict = {setting[1]: setting[2] for setting in settings}
    return jsonify(settings_dict)

@app.route('/system-settings', methods=['POST'])
def update_system_settings():
    data = request.json
    setting_name = data.get('setting_name')
    setting_value = data.get('setting_value')

    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("IF EXISTS (SELECT 1 FROM SystemSettings WHERE SettingName=?) "
                   "UPDATE SystemSettings SET SettingValue=? WHERE SettingName=? "
                   "ELSE INSERT INTO SystemSettings (SettingName, SettingValue) VALUES (?, ?)",
                   (setting_name, setting_value, setting_name, setting_name, setting_value))
    conn.commit()
    conn.close()

    return jsonify({"message": "System setting updated successfully"}), 200

@app.route('/log', methods=['POST'])
def receive_log():
    try:
        # JSON verisini al
        data = request.get_json()

        # 'log' ve 'log_type' anahtarlarının var olup olmadığını kontrol et
        if 'log' not in data or 'log_type' not in data:
            return jsonify({'error': 'Log data or log_type is missing'}), 400

        # Geçerli log_type değerini kontrol et (INFO, ALERT, ERROR)
        log_type = data['log_type'].upper()
        if log_type not in ['INFO', 'ALERT', 'ERROR']:
            return jsonify({'error': 'Invalid log_type. Must be INFO, ALERT, or ERROR'}), 400

        # Veritabanına bağlan
        conn = pyodbc.connect(DB_CONN)
        cursor = conn.cursor()

        # Veriyi SQL sorgusu ile ekle
        query = "INSERT INTO logs (log_message, log_type) VALUES (?, ?)"
        cursor.execute(query, (str(data['log']), log_type))

        # Değişiklikleri kaydet
        conn.commit()

        # Bağlantıyı kapat
        cursor.close()
        conn.close()

        # Başarılı yanıt
        return jsonify({'message': 'Log received and saved to database successfully'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/log', methods=['GET'])
def get_logs():
    try:
        # Veritabanına bağlan
        conn = pyodbc.connect(DB_CONN)
        cursor = conn.cursor()

        # Veritabanından logları al
        query = "SELECT * FROM logs"
        cursor.execute(query)

        # Sonuçları al
        logs = cursor.fetchall()

        # Logları JSON formatında döndür
        log_list = []
        for log in logs:
            log_list.append({
                'log_message': log[1],
                'log_type': log[3],
                'created_at': log[2]# log_message ikinci kolonda
                     # log_type üçüncü kolonda
            })

        # Bağlantıyı kapat
        cursor.close()
        conn.close()

        # Başarılı yanıt
        return jsonify({'logs': log_list}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Vardiya Yönetimi
@app.route('/shifts', methods=['POST'])
def add_shift():
    data = request.json
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Shifts (ShiftName, StartTime, EndTime)
        VALUES (?, ?, ?)
    """, (data['shift_name'], data['start_time'], data['end_time']))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Vardiya eklendi'}), 201

@app.route('/shifts', methods=['GET'])
def get_shifts():
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT ID, ShiftName, StartTime, EndTime FROM Shifts")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{
        'ID': row[0],
        'ShiftName': row[1],
        'StartTime': row[2],
        'EndTime': row[3]
    } for row in rows])

# Proje Yönetimi
@app.route('/projects', methods=['POST'])
def add_project():
    data = request.json
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Projects (ProjectName, Description, StartDate, EndDate)
        VALUES (?, ?, ?, ?)
    """, (data['project_name'], data['description'], data['start_date'], data['end_date']))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Proje eklendi'}), 201

@app.route('/projects', methods=['GET'])
def get_projects():
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT ID, ProjectName, Description, StartDate, EndDate FROM Projects")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{
        'ID': row[0],
        'ProjectName': row[1],
        'Description': row[2],
        'StartDate': row[3],
        'EndDate': row[4]
    } for row in rows])

# Personel Proje Atama
@app.route('/project-assignments', methods=['POST'])
def assign_project():
    data = request.json
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO ProjectAssignments (EmployeeID, ProjectID)
        VALUES (?, ?)
    """, (data['employee_id'], data['project_id']))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Personel projeye atandı'}), 201

# Çalışma Süresi Takibi
@app.route('/work-logs', methods=['POST'])
def add_work_log():
    data = request.json
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO WorkLogs (EmployeeID, ProjectID, WorkDate, WorkHours)
        VALUES (?, ?, ?, ?)
    """, (data['employee_id'], data['project_id'], data['work_date'], data['work_hours']))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Çalışma süresi kaydedildi'}), 201

# Eğitim Yönetimi
@app.route('/trainings', methods=['POST'])
def add_training():
    data = request.json
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Trainings (TrainingName, Description, TrainingDate, TrainingLocation)
        VALUES (?, ?, ?, ?)
    """, (data['training_name'], data['description'], data['training_date'], data['training_location']))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Eğitim eklendi'}), 201

@app.route('/trainings', methods=['GET'])
def get_trainings():
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT ID, TrainingName, Description, TrainingDate, TrainingLocation FROM Trainings")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{
        'ID': row[0],
        'TrainingName': row[1],
        'Description': row[2],
        'TrainingDate': row[3],
        'TrainingLocation': row[4]
    } for row in rows])

# Personel Eğitim Atama
@app.route('/training-assignments', methods=['POST'])
def assign_training():
    data = request.json
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO TrainingAssignments (EmployeeID, TrainingID)
        VALUES (?, ?)
    """, (data['employee_id'], data['training_id']))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Personel eğitime atandı'}), 201
# Belge Yönetimi
@app.route('/documents', methods=['POST'])
def upload_document():
    data = request.json
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Documents (EmployeeID, DocumentName, DocumentType, FilePath)
        VALUES (?, ?, ?, ?)
    """, (data['employee_id'], data['document_name'], data['document_type'], data['file_path']))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Belge yüklendi'}), 201

@app.route('/documents', methods=['GET'])
def get_documents():
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT ID, EmployeeID, DocumentName, DocumentType, FilePath FROM Documents")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{
        'ID': row[0],
        'EmployeeID': row[1],
        'DocumentName': row[2],
        'DocumentType': row[3],
        'FilePath': row[4]
    } for row in rows])
# Ziyaretçi Yönetimi
@app.route('/visitors', methods=['POST'])
def add_visitor():
    data = request.json
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Visitors (VisitorName, Company, VisitReason, EntryTime, ExitTime)
        VALUES (?, ?, ?, ?, ?)
    """, (data['visitor_name'], data['company'], data['visit_reason'], data['entry_time'], data['exit_time']))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Ziyaretçi kaydı eklendi'}), 201

@app.route('/visitors', methods=['GET'])
def get_visitors():
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT ID, VisitorName, Company, VisitReason, EntryTime, ExitTime FROM Visitors")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{
        'ID': row[0],
        'VisitorName': row[1],
        'Company': row[2],
        'VisitReason': row[3],
        'EntryTime': row[4],
        'ExitTime': row[5]
    } for row in rows])

# Toplantı Odası Yönetimi
@app.route('/meeting-rooms', methods=['POST'])
def add_meeting_room():
    data = request.json
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO MeetingRooms (RoomName, Capacity, Equipment)
        VALUES (?, ?, ?)
    """, (data['room_name'], data['capacity'], data['equipment']))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Toplantı odası eklendi'}), 201

@app.route('/meeting-rooms', methods=['GET'])
def get_meeting_rooms():
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT ID, RoomName, Capacity, Equipment FROM MeetingRooms")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{
        'ID': row[0],
        'RoomName': row[1],
        'Capacity': row[2],
        'Equipment': row[3]
    } for row in rows])

@app.route('/meeting-room-reservations', methods=['POST'])
def add_meeting_room_reservation():
    data = request.json
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO MeetingRoomReservations (EmployeeID, RoomID, ReservationDate, ReservationTime)
        VALUES (?, ?, ?, ?)
    """, (data['employee_id'], data['room_id'], data['reservation_date'], data['reservation_time']))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Toplantı odası rezervasyonu yapıldı'}), 201

@app.route('/meeting-room-reservations', methods=['GET'])
def get_meeting_room_reservations():
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT ID, EmployeeID, RoomID, ReservationDate, ReservationTime FROM MeetingRoomReservations")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{
        'ID': row[0],
        'EmployeeID': row[1],
        'RoomID': row[2],
        'ReservationDate': row[3],
        'ReservationTime': row[4]
    } for row in rows])
# Yemekhane Yönetimi
@app.route('/cafeteria-menus', methods=['POST'])
def add_cafeteria_menu():
    data = request.json
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO CafeteriaMenus (MenuDate, MenuItems)
        VALUES (?, ?)
    """, (data['menu_date'], data['menu_items']))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Yemekhane menüsü eklendi'}), 201

@app.route('/cafeteria-menus', methods=['GET'])
def get_cafeteria_menus():
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT ID, MenuDate, MenuItems FROM CafeteriaMenus")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{
        'ID': row[0],
        'MenuDate': row[1],
        'MenuItems': row[2]
    } for row in rows])

@app.route('/cafeteria-reservations', methods=['POST'])
def add_cafeteria_reservation():
    data = request.json
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO CafeteriaReservations (EmployeeID, ReservationDate, ReservationTime)
        VALUES (?, ?, ?)
    """, (data['employee_id'], data['reservation_date'], data['reservation_time']))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Yemekhane rezervasyonu yapıldı'}), 201

@app.route('/cafeteria-reservations', methods=['GET'])
def get_cafeteria_reservations():
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT ID, EmployeeID, ReservationDate, ReservationTime FROM CafeteriaReservations")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{
        'ID': row[0],
        'EmployeeID': row[1],
        'ReservationDate': row[2],
        'ReservationTime': row[3]
    } for row in rows])
# Otopark Yönetimi
@app.route('/parking-lots', methods=['POST'])
def add_parking_lot():
    data = request.json
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO ParkingLots (LotName, Capacity, Location)
        VALUES (?, ?, ?)
    """, (data['lot_name'], data['capacity'], data['location']))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Otopark alanı eklendi'}), 201

@app.route('/parking-lots', methods=['GET'])
def get_parking_lots():
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT ID, LotName, Capacity, Location FROM ParkingLots")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{
        'ID': row[0],
        'LotName': row[1],
        'Capacity': row[2],
        'Location': row[3]
    } for row in rows])

@app.route('/parking-reservations', methods=['POST'])
def add_parking_reservation():
    data = request.json
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO ParkingReservations (EmployeeID, LotID, ReservationDate, ReservationTime)
        VALUES (?, ?, ?, ?)
    """, (data['employee_id'], data['lot_id'], data['reservation_date'], data['reservation_time']))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Otopark rezervasyonu yapıldı'}), 201

@app.route('/parking-reservations', methods=['GET'])
def get_parking_reservations():
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT ID, EmployeeID, LotID, ReservationDate, ReservationTime FROM ParkingReservations")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{
        'ID': row[0],
        'EmployeeID': row[1],
        'LotID': row[2],
        'ReservationDate': row[3],
        'ReservationTime': row[4]
    } for row in rows])
# Servis Yönetimi
@app.route('/shuttles', methods=['POST'])
def add_shuttle():
    data = request.json
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Shuttles (Plate, Route, DepartureTime)
        VALUES (?, ?, ?)
    """, (data['plate'], data['route'], data['departure_time']))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Servis aracı eklendi'}), 201

@app.route('/shuttles', methods=['GET'])
def get_shuttles():
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT ID, Plate, Route, DepartureTime FROM Shuttles")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{
        'ID': row[0],
        'Plate': row[1],
        'Route': row[2],
        'DepartureTime': row[3]
    } for row in rows])

@app.route('/shuttle-reservations', methods=['POST'])
def add_shuttle_reservation():
    data = request.json
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO ShuttleReservations (EmployeeID, ShuttleID, ReservationDate, ReservationTime)
        VALUES (?, ?, ?, ?)
    """, (data['employee_id'], data['shuttle_id'], data['reservation_date'], data['reservation_time']))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Servis rezervasyonu yapıldı'}), 201

@app.route('/shuttle-reservations', methods=['GET'])
def get_shuttle_reservations():
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT ID, EmployeeID, ShuttleID, ReservationDate, ReservationTime FROM ShuttleReservations")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{
        'ID': row[0],
        'EmployeeID': row[1],
        'ShuttleID': row[2],
        'ReservationDate': row[3],
        'ReservationTime': row[4]
    } for row in rows])
# Anket Yönetimi
@app.route('/surveys', methods=['POST'])
def add_survey():
    data = request.json
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Surveys (SurveyName, Description)
        VALUES (?, ?)
    """, (data['survey_name'], data['description']))
    survey_id = cursor.execute("SELECT @@IDENTITY").fetchone()[0]
    for question in data['questions']:
        cursor.execute("""
            INSERT INTO SurveyQuestions (SurveyID, QuestionText)
            VALUES (?, ?)
        """, (survey_id, question['question_text']))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Anket eklendi'}), 201

@app.route('/surveys', methods=['GET'])
def get_surveys():
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.ID, s.SurveyName, s.Description, sq.ID, sq.QuestionText
        FROM Surveys s
        LEFT JOIN SurveyQuestions sq ON s.ID = sq.SurveyID
    """)
    rows = cursor.fetchall()
    surveys = {}
    for row in rows:
        if row[0] not in surveys:
            surveys[row[0]] = {'ID': row[0], 'SurveyName': row[1], 'Description': row[2], 'Questions': []}
        if row[3]:
            surveys[row[0]]['Questions'].append({'ID': row[3], 'QuestionText': row[4]})
    conn.close()
    return jsonify(list(surveys.values()))

@app.route('/survey-assignments', methods=['POST'])
def assign_survey():
    data = request.json
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO SurveyAssignments (EmployeeID, SurveyID)
        VALUES (?, ?)
    """, (data['employee_id'], data['survey_id']))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Anket personellere atandı'}), 201

@app.route('/survey-responses', methods=['POST'])
def add_survey_response():
    data = request.json
    conn = db_connect()
    cursor = conn.cursor()
    for response in data['responses']:
        cursor.execute("""
            INSERT INTO SurveyResponses (EmployeeID, QuestionID, ResponseText)
            VALUES (?, ?, ?)
        """, (data['employee_id'], response['question_id'], response['response_text']))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Anket cevapları kaydedildi'}), 201

@app.route('/survey-responses', methods=['GET'])
def get_survey_responses():
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT sr.ID, sr.EmployeeID, sq.SurveyID, sq.QuestionText, sr.ResponseText
        FROM SurveyResponses sr
        JOIN SurveyQuestions sq ON sr.QuestionID = sq.ID
    """)
    rows = cursor.fetchall()
    responses = []
    for row in rows:
        responses.append({'ID': row[0], 'EmployeeID': row[1], 'SurveyID': row[2], 'QuestionText': row[3], 'ResponseText': row[4]})
    conn.close()
    return jsonify(responses)
# İş Sağlığı ve Güvenliği Yönetimi
@app.route('/work-accidents', methods=['POST'])
def add_work_accident():
    data = request.json
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO WorkAccidents (EmployeeID, AccidentDate, Description, Location)
        VALUES (?, ?, ?, ?)
    """, (data['employee_id'], data['accident_date'], data['description'], data['location']))
    conn.commit()
    conn.close()
    return jsonify({'message': 'İş kazası kaydedildi'}), 201

@app.route('/work-accidents', methods=['GET'])
def get_work_accidents():
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT ID, EmployeeID, AccidentDate, Description, Location FROM WorkAccidents")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{
        'ID': row[0],
        'EmployeeID': row[1],
        'AccidentDate': row[2],
        'Description': row[3],
        'Location': row[4]
    } for row in rows])

@app.route('/safety-trainings', methods=['POST'])
def add_safety_training():
    data = request.json
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO SafetyTrainings (TrainingName, Description, TrainingDate, TrainingLocation)
        VALUES (?, ?, ?, ?)
    """, (data['training_name'], data['description'], data['training_date'], data['training_location']))
    conn.commit()
    conn.close()
    return jsonify({'message': 'İş sağlığı ve güvenliği eğitimi eklendi'}), 201

@app.route('/safety-trainings', methods=['GET'])
def get_safety_trainings():
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT ID, TrainingName, Description, TrainingDate, TrainingLocation FROM SafetyTrainings")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{
        'ID': row[0],
        'TrainingName': row[1],
        'Description': row[2],
        'TrainingDate': row[3],
        'TrainingLocation': row[4]
    } for row in rows])

@app.route('/safety-training-assignments', methods=['POST'])
def assign_safety_training():
    data = request.json
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO SafetyTrainingAssignments (EmployeeID, TrainingID)
        VALUES (?, ?)
    """, (data['employee_id'], data['training_id']))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Personel iş sağlığı ve güvenliği eğitimine atandı'}), 201

@app.route('/risk-assessments', methods=['POST'])
def add_risk_assessment():
    data = request.json
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO RiskAssessments (AssessmentDate, Description, Result)
        VALUES (?, ?, ?)
    """, (data['assessment_date'], data['description'], data['result']))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Risk değerlendirme kaydedildi'}), 201

@app.route('/risk-assessments', methods=['GET'])
def get_risk_assessments():
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT ID, AssessmentDate, Description, Result FROM RiskAssessments")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{
        'ID': row[0],
        'AssessmentDate': row[1],
        'Description': row[2],
        'Result': row[3]
    } for row in rows])
# Performans Değerlendirme (Geliştirilmiş)
@app.route('/performance-criteria', methods=['POST'])
def add_performance_criteria():
    data = request.json
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO PerformanceCriteria (CriteriaName, Description)
        VALUES (?, ?)
    """, (data['criteria_name'], data['description']))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Performans kriteri eklendi'}), 201

@app.route('/performance-criteria', methods=['GET'])
def get_performance_criteria():
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT ID, CriteriaName, Description FROM PerformanceCriteria")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{
        'ID': row[0],
        'CriteriaName': row[1],
        'Description': row[2]
    } for row in rows])

@app.route('/performance-evaluations', methods=['POST'])
def add_performance_evaluation():
    data = request.json
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO PerformanceEvaluations (EmployeeID, EvaluationDate, CriteriaID, Score)
        VALUES (?, ?, ?, ?)
    """, (data['employee_id'], data['evaluation_date'], data['criteria_id'], data['score']))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Performans değerlendirme kaydedildi'}), 201

@app.route('/performance-evaluations', methods=['GET'])
def get_performance_evaluations():
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT pe.ID, pe.EmployeeID, pe.EvaluationDate, pc.CriteriaName, pe.Score FROM PerformanceEvaluations pe JOIN PerformanceCriteria pc ON pe.CriteriaID = pc.ID")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{
        'ID': row[0],
        'EmployeeID': row[1],
        'EvaluationDate': row[2],
        'CriteriaName': row[3],
        'Score': row[4]
    } for row in rows])
# Zaman Çizelgesi (Geliştirilmiş)
@app.route('/asset-assignments', methods=['POST'])
def assign_asset():
    data = request.json
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO AssetAssignments (EmployeeID, AssetName, AssignmentDate, ReturnDate)
        VALUES (?, ?, ?, ?)
    """, (data['employee_id'], data['asset_name'], data['assignment_date'], data['return_date']))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Zimmet ataması yapıldı'}), 201

@app.route('/asset-assignments', methods=['GET'])
def get_asset_assignments():
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT ID, EmployeeID, AssetName, AssignmentDate, ReturnDate FROM AssetAssignments")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{
        'ID': row[0],
        'EmployeeID': row[1],
        'AssetName': row[2],
        'AssignmentDate': row[3],
        'ReturnDate': row[4]
    } for row in rows])

@app.route('/equipment-maintenance', methods=['POST'])
def add_equipment_maintenance():
    data = request.json
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO EquipmentMaintenance (EquipmentName, MaintenanceDate, Description)
        VALUES (?, ?, ?)
    """, (data['equipment_name'], data['maintenance_date'], data['description']))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Ekipman bakımı kaydedildi'}), 201

@app.route('/equipment-maintenance', methods=['GET'])
def get_equipment_maintenance():
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT ID, EquipmentName, MaintenanceDate, Description FROM EquipmentMaintenance")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{
        'ID': row[0],
        'EquipmentName': row[1],
        'MaintenanceDate': row[2],
        'Description': row[3]
    } for row in rows])

# Proje Bütçe Yönetimi
@app.route('/project-budgets', methods=['POST'])
def add_project_budget():
    data = request.json
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO ProjectBudgets (ProjectID, BudgetAmount, Currency)
        VALUES (?, ?, ?)
    """, (data['project_id'], data['budget_amount'], data['currency']))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Proje bütçesi eklendi'}), 201

@app.route('/project-budgets', methods=['GET'])
def get_project_budgets():
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT ID, ProjectID, BudgetAmount, Currency FROM ProjectBudgets")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{
        'ID': row[0],
        'ProjectID': row[1],
        'BudgetAmount': row[2],
        'Currency': row[3]
    } for row in rows])

@app.route('/project-expenses', methods=['POST'])
def add_project_expense():
    data = request.json
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO ProjectExpenses (ProjectID, ExpenseDate, ExpenseAmount, ExpenseCategory)
        VALUES (?, ?, ?, ?)
    """, (data['project_id'], data['expense_date'], data['expense_amount'], data['expense_category']))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Proje harcaması kaydedildi'}), 201

@app.route('/project-expenses', methods=['GET'])
def get_project_expenses():
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT ID, ProjectID, ExpenseDate, ExpenseAmount, ExpenseCategory FROM ProjectExpenses")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{
        'ID': row[0],
        'ProjectID': row[1],
        'ExpenseDate': row[2],
        'ExpenseAmount': row[3],
        'ExpenseCategory': row[4]
    } for row in rows])
if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5001, debug=True, allow_unsafe_werkzeug=True)
