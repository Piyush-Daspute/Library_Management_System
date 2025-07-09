from flask import Flask, render_template, request, redirect, url_for,flash
import mysql.connector
from flask import session
from datetime import date
import os
from PIL import Image
from werkzeug.utils import secure_filename
from flask_apscheduler import APScheduler
from flask_mail import Mail, Message


app = Flask(__name__)

# Mail Config
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'piyush.daspute23@pccoepune.org'
app.config['MAIL_PASSWORD'] = 'FY23H003'
app.config['MAIL_DEFAULT_SENDER'] = 'piyush.daspute23@pccoepune.org'

mail = Mail(app)

scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

@scheduler.task('interval', id='daily_reminder', hours=24)
def daily_email_reminder():
    with app.app_context():
        send_reminders()

app = Flask(__name__)
app.secret_key = 'Piyush_Secret_Key'

print("Trying to connect...")

try:
    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Lumberjack#01",
        database="book_lending_system"
    )
    print("✅ Connected successfully!")
    print(db)
except mysql.connector.Error as err:
    print("❌ Connection failed:", err)

cursor = db.cursor()

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        phone = request.form['phone']
        password = request.form['password']
        
        query = "SELECT * FROM users WHERE phone = %s AND password = %s"
        cursor.execute(query, (phone, password))
        result = cursor.fetchone()

        print("Phone:", phone)
        print("Password:", password)
        print("Query result:", result)  # This is the most important
        session['user_id'] = result[0]
        session['role'] = result[4]
        print("Session user is = ", session['user_id'])
        if result:
            return redirect('/home')
        else:
            error = "Invalid credentials. Please try again."
            print("Error passed to template:", error)
            return render_template('index.html', error=error)

    # For GET request
    return render_template('index.html', error=None)




@app.route('/home')
def home():
    user_id = session.get('user_id')
    search_query = request.args.get('search', '')

    if search_query:
        query = "SELECT * FROM books WHERE title LIKE %s OR author LIKE %s"
        search_term = f"%{search_query}%"
        cursor.execute(query, (search_term, search_term))
    else:
        query = "SELECT * FROM books"
        cursor.execute(query)

    books = cursor.fetchall()
    
    # Create a dictionary to track rental status for each book
    book_rental_status = {}
    
    for book in books:
        book_id = book[0]  # Assuming book_id is the first column
        
        # Check rental status for each book
        cursor.execute("""
            SELECT user_id 
            FROM transactions 
            WHERE book_id = %s AND return_date IS NULL 
            ORDER BY borrow_date DESC 
            LIMIT 1
        """, (book_id,))
        
        result = cursor.fetchone()
        
        if result:
            rented_user_id = result[0]
            book_rental_status[book_id] = {
                'currently_rented': True,
                'true_renter': (user_id == rented_user_id)
            }
        else:
            book_rental_status[book_id] = {
                'currently_rented': False,
                'true_renter': False
            }
    role = session['role']
    if role == 'admin':
        return render_template('home.html', 
                            books=books, 
                            book_rental_status=book_rental_status)
    else:
        return render_template('user_home.html', 
                            books=books, 
                            book_rental_status=book_rental_status)
    
    
@app.route('/logout')
def logout():
    session.clear()  # Optional: clear session if used
    return redirect('/')  # Redirect to login page

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        phone = request.form["phone"]
        password = request.form["password"]
        role = request.form["role"]

        # Optional: Check if user already exists
        cursor.execute("SELECT * FROM users WHERE phone = %s", (phone,))
        if cursor.fetchone():
            error = "User already exists with this phone number."
            return render_template("register.html", error=error)

        # Insert new user
        query = "INSERT INTO users (name, email, phone, password, role) VALUES (%s, %s, %s, %s, %s)"
        values = (name, email, phone, password, role)
        cursor.execute(query, values)
        db.commit()

        return redirect("/")  # Redirect to login or home after registration

    return render_template("register.html")


from datetime import date

@app.route('/rent/<string:book_id>', methods=['POST'])
def rent_book(book_id):
    user_id = session.get('user_id')  # Ensure user is logged in

    if not user_id:
        return redirect(url_for('index'))

    # Check if book is available
    cursor.execute("SELECT available FROM books WHERE book_id = %s", (book_id,))
    available = cursor.fetchone()[0]

    if not available:
        return "Book is already rented!", 400

    # Mark book as not available
    cursor.execute("UPDATE books SET available = FALSE WHERE book_id = %s", (book_id,))
    
    # Create transaction
    cursor.execute(
        "INSERT INTO transactions (user_id, book_id, borrow_date, status) VALUES (%s, %s, %s, %s)",
        (user_id, book_id, date.today(), "rented")
    )
    db.commit()
    return redirect(url_for('home'))


@app.route('/return/<string:book_id>', methods=['POST'])
def return_book(book_id):
    user_id = session.get('user_id')

    if not user_id:
        return redirect(url_for('index'))

    cursor.execute("SELECT user_id FROM transactions WHERE book_id = %s  ORDER BY transaction_id DESC LIMIT 1 ", (book_id,))
    rented_user_id = cursor.fetchone()[0]
    print("Fetched row:", cursor.fetchone())
    if user_id == rented_user_id:
        # Update book availability
        cursor.execute("UPDATE books SET available = TRUE WHERE book_id = %s", (book_id,))

        # Update transaction
        print("Updating return")
        cursor.execute("""
            UPDATE transactions 
            SET return_date = %s, status = %s 
            WHERE user_id = %s AND book_id = %s AND status = 'rented'
            ORDER BY borrow_date DESC LIMIT 1
        """, (date.today(), "returned", user_id, book_id))
        
        db.commit()
        return redirect(url_for('home'))
    
    else:
         flash('You cannot return this book')
         return redirect(url_for('home'))
    
@app.route('/book/<int:book_id>/renting-info')
def book_renting_info(book_id):
    # Current renting status
    cursor.execute("""
        SELECT t.transaction_id, t.user_id, t.book_id, t.borrow_date, 
               t.return_date, t.status, t.fine, u.name as username 
        FROM transactions t 
        JOIN users u ON t.user_id = u.user_id 
        WHERE t.book_id = %s AND t.status = 'rented'
        LIMIT 1
    """, (book_id,))
    current_rent = cursor.fetchone()

    # Rental history
    cursor.execute("""
        SELECT t.transaction_id, t.user_id, t.book_id, t.borrow_date, 
               t.return_date, t.status, t.fine, u.name as username 
        FROM transactions t 
        JOIN users u ON t.user_id = u.user_id 
        WHERE t.book_id = %s 
        ORDER BY t.transaction_id DESC
    """, (book_id,))
    history = cursor.fetchall()

    return render_template('renting_info.html', 
                           book_id=book_id, 
                           current_rent=current_rent, 
                           history=history)



@app.route('/transaction-history')
def transaction_history():
    cur = db.cursor()

    cur.execute("""
        SELECT t.transaction_id, u.name, b.title, t.borrow_date, t.return_date, t.status, t.fine
        FROM transactions t
        JOIN users u ON t.user_id = u.user_id
        JOIN books b ON t.book_id = b.book_id
        ORDER BY t.transaction_id DESC
    """)
    transactions = cur.fetchall()
    return render_template('transaction_history.html', transactions=transactions)


#Image save path 
UPLOAD_FOLDER = 'static/images'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

#Image upload restrictions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/update-library')
def update_library():
    cur = db.cursor()
    cur.execute("SELECT * FROM books")
    books = cur.fetchall()
    return render_template('update_library.html', books=books)

from PIL import Image
import os
from werkzeug.utils import secure_filename

@app.route('/add-book', methods=['POST'])
def add_book():
    title = request.form['title']
    author = request.form['author']
    available = True

    file = request.files['img_path']
    filename = secure_filename(file.filename)
    img_path = os.path.join('images', filename)

    if file and allowed_file(filename):
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(save_path)
    else:
        return "Invalid file format"

    # Check if archived book exists
    cur = db.cursor()
    cur.execute("SELECT * FROM books WHERE title = %s AND author = %s AND archived = TRUE", (title, author))
    archived_book = cur.fetchone()

    if archived_book:
        # Restore archived book instead of inserting a new one
        cur.execute("""
            UPDATE books 
            SET archived = FALSE, available = TRUE, book_img = %s 
            WHERE book_id = %s
        """, (img_path, archived_book[0]))
        db.commit()
        flash("✅ Archived book restored and updated.", "success")
    else:
        # Add new book
        cur.execute("""
            INSERT INTO books (title, author, available, book_img, archived) 
            VALUES (%s, %s, %s, %s, %s)
        """, (title, author, available, img_path, False))
        db.commit()
        flash("✅ New book added successfully.", "success")

    return redirect(url_for('update_library'))


@app.route('/delete_book/<int:book_id>', methods=['POST'])
def delete_book(book_id):
    print("Execution Delete Start")
    try:
        cursor.execute("UPDATE books SET archived = TRUE, available = FALSE WHERE book_id = %s", (book_id,))
        db.commit()

        print("Execution Delete Done")
        flash("✅ Book archived successfully.", "success")
    except Exception as e:
        print(f"❌ Exception occurred: {e}")  # This helps debug the error
        flash(f"❌ Error: {str(e)}", "error")

    return redirect(url_for('update_library'))


@app.route('/about')
def about():
    return render_template('about.html')


#Mail Reminder sending 
@app.route('/send_reminders')
def send_reminders():
    # Step 1: Get all users with active rented books
    query = """
        SELECT DISTINCT u.email, u.name, b.title, t.borrow_date
        FROM users u
        JOIN transactions t ON u.user_id = t.user_id
        JOIN books b ON t.book_id = b.book_id
        WHERE t.status = 'rented'
    """
    cursor.execute(query)
    results = cursor.fetchall()

    # Step 2: Send reminder email to each user
    for email, name, title, borrow_date in results:
        msg = Message(
            subject="📚 Library Book Return Reminder",
            recipients=[email]
        )
        msg.body = f"""Hi {name},

This is a friendly reminder that you have borrowed the book titled: '{title}' on {borrow_date}.

Please ensure it is returned on time to avoid any fines.

Regards,  
Library Management System"""
        mail.send(msg)

    return "Reminders sent to all users with active rentals!"

@app.route('/profile')
def profile():
    user_id = session.get('user_id')


    cursor.execute("Select * from transactions where user_id = %s", (user_id,))
    transactions = cursor.fetchall()
    print(transactions[0])
    cursor.execute("Select * from users where user_id = %s", (user_id,))
    user = cursor.fetchone()
    print(user[0])
    return render_template('profile.html', user=user, transactions=transactions)

@app.route('/user_about')
def user_about():
    return render_template('user_about.html')



if __name__ == '__main__':
    app.run(debug=True)
