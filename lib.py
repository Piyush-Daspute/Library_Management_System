import mysql.connector

print("Trying to connect...")

try:
    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Lumberjack#01",
        database="hospital"
    )
    print("✅ Connected successfully!")
    print(db)
except mysql.connector.Error as err:
    print("❌ Connection failed:", err)

cursor = db.cursor()
# Insert a new user
def add_user(name, email, password, role, phone):
    query = "INSERT INTO users (name, email, password, role, phone) VALUES (%s, %s, %s, %s, %s)"
    values = (name, email, password, role, phone)
    cursor.execute(query, values)
    db.commit()
    print("User added successfully!")

def add_book(book_id,title,author,available):
    query = "INSERT INTO books (book_id,title,author,available) VALUES (%s, %s, %s, %s)"
    values = (book_id,title,author,available)
    cursor.execute(query, values)
    db.commit()
    print("Book added successfully!")

def transaction(transaction_id,user_id,book_id,borrow_date,return_date,status,fine):
    query = "INSERT INTO transactions (transaction_id,user_id,book_id,borrow_date,return_date,status,fine) VALUES (%s, %s, %s, %s,%s, %s, %s)"
    values = (transaction_id,user_id,book_id,borrow_date,return_date,status,fine)
    cursor.execute(query, values)
    db.commit()
    print("Transaction added successfully!")

print("Done")