import os
import re
import sqlite3
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "images")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

STATUSES = ["Pending", "Accepted", "Preparing", "Ready", "Collected"]
ALL_STATUSES = ["Pending", "Accepted", "Preparing", "Ready", "Collected", "Rejected"]
CATEGORIES = ["Snacks", "Meals", "Beverages", "Fast Food"]

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "canteen_preordering_secure_secret_key_2026")


# ==============================================================================
# DATABASE MANAGEMENT
# ==============================================================================
def get_db():
    """Returns the current request's database connection, creating it if needed."""
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON;")
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    """Closes the database connection at the end of the request."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Initializes SQLite database tables, default admin, student demo, and sample food items."""
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA foreign_keys = ON;")
    
    con.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'student'
    );

    CREATE TABLE IF NOT EXISTS food_items (
        food_id INTEGER PRIMARY KEY AUTOINCREMENT,
        food_name TEXT NOT NULL,
        description TEXT,
        price REAL NOT NULL,
        category TEXT NOT NULL,
        image TEXT,
        availability TEXT NOT NULL DEFAULT 'Available'
    );

    CREATE TABLE IF NOT EXISTS orders (
        order_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        total_amount REAL NOT NULL,
        pickup_time TEXT NOT NULL,
        order_status TEXT NOT NULL DEFAULT 'Pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    );

    CREATE TABLE IF NOT EXISTS order_items (
        order_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        food_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        price REAL NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders(order_id),
        FOREIGN KEY (food_id) REFERENCES food_items(food_id)
    );
    """)

    # Create initial admin account if not present
    admin_exists = con.execute("SELECT 1 FROM users WHERE role = 'admin'").fetchone()
    if not admin_exists:
        con.execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, 'admin')",
            ("Canteen Admin", "admin@canteen.com", generate_password_hash("admin123"))
        )

    # Create demo student account if not present
    student_exists = con.execute("SELECT 1 FROM users WHERE role = 'student'").fetchone()
    if not student_exists:
        con.execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, 'student')",
            ("Student Demo", "student@canteen.com", generate_password_hash("student123"))
        )

    # Insert sample food items if none exist
    food_exists = con.execute("SELECT 1 FROM food_items").fetchone()
    if not food_exists:
        sample_foods = [
            ("Samosa", "Crispy potato and peas samosa (2 pcs) with mint chutney", 20.00, "Snacks", None, "Available"),
            ("Veg Puff", "Flaky bakery pastry with savory spiced vegetable filling", 25.00, "Snacks", None, "Available"),
            ("Paneer Tikka Roll", "Grilled marinated paneer cubes rolled in fresh flatbread", 60.00, "Snacks", None, "Available"),
            ("Special Veg Meals", "Basmati rice, 2 chapatis, dal tadka, paneer sabzi, and pickle", 70.00, "Meals", None, "Available"),
            ("Masala Dosa", "Crispy fermented crepe served with hot sambar and coconut chutney", 50.00, "Meals", None, "Available"),
            ("Veg Fried Rice", "Wok-tossed rice with crisp garden vegetables and soy seasoning", 65.00, "Meals", None, "Available"),
            ("Cold Coffee", "Rich chilled blended coffee topped with chocolate syrup", 40.00, "Beverages", None, "Available"),
            ("Masala Tea", "Aromatic hot spiced milk tea with ginger and cardamom", 15.00, "Beverages", None, "Available"),
            ("Fresh Lime Soda", "Refreshing sweet and salted chilled carbonated lime soda", 30.00, "Beverages", None, "Available"),
            ("Veg Burger", "Crispy vegetable patty with fresh lettuce, tomato, and mayo", 60.00, "Fast Food", None, "Available"),
            ("Veg Hakka Noodles", "Stir-fried noodles with crunchy cabbage, capsicum, and carrots", 55.00, "Fast Food", None, "Available"),
            ("Grilled Cheese Sandwich", "Golden grilled bread layered with melted cheese and herbs", 45.00, "Fast Food", None, "Available"),
        ]
        con.executemany(
            "INSERT INTO food_items (food_name, description, price, category, image, availability) VALUES (?, ?, ?, ?, ?, ?)",
            sample_foods
        )

    con.commit()
    con.close()


# ==============================================================================
# ACCESS CONTROL DECORATORS & HELPERS
# ==============================================================================
def login_required(f):
    """Restricts route access to logged-in students."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("role") != "student":
            flash("Please log in as a student to access this page.")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Restricts route access to logged-in administrators."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("role") != "admin":
            flash("Administrator login required.")
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated_function


def allowed_file(filename):
    """Validates uploaded image file extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.context_processor
def inject_context():
    """Injects cart count and status flow list into all templates."""
    cart = session.get("cart", {})
    cart_count = 0
    if isinstance(cart, dict):
        cart_count = sum(qty for qty in cart.values() if isinstance(qty, int) and qty > 0)
    return dict(cart_count=cart_count, statuses=STATUSES)


def cart_items():
    """
    Computes verified cart items and total directly from database records.
    Guarantees client-side prices are never trusted.
    """
    items, total = [], 0.0
    cart = session.get("cart", {})
    if not isinstance(cart, dict):
        return items, total

    db = get_db()
    for fid_str, qty in list(cart.items()):
        try:
            food_id = int(fid_str)
            quantity = int(qty)
        except (ValueError, TypeError):
            continue

        if quantity <= 0:
            continue

        food = db.execute("SELECT * FROM food_items WHERE food_id = ?", (food_id,)).fetchone()
        if food:
            subtotal = round(float(food["price"]) * quantity, 2)
            total += subtotal
            items.append({
                "food": food,
                "qty": quantity,
                "sub": subtotal
            })

    return items, round(total, 2)


def orders_with_items(where_clause="", args=()):
    """Fetches orders joined with user details and populated order items."""
    db = get_db()
    query = f"""
        SELECT o.*, u.name, u.email
        FROM orders o
        JOIN users u ON u.user_id = o.user_id
        {where_clause}
        ORDER BY o.order_id DESC
    """
    order_rows = db.execute(query, args).fetchall()
    results = []
    for order in order_rows:
        item_rows = db.execute("""
            SELECT f.food_name, oi.quantity, oi.price
            FROM order_items oi
            JOIN food_items f ON f.food_id = oi.food_id
            WHERE oi.order_id = ?
        """, (order["order_id"],)).fetchall()
        results.append((order, item_rows))
    return results


# ==============================================================================
# PUBLIC & AUTHENTICATION ROUTES
# ==============================================================================
@app.route("/")
def index():
    """Landing homepage."""
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Student registration route with input validation and password hashing."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        email_pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"

        if not name:
            flash("Please enter your full name.")
        elif not email or not re.match(email_pattern, email):
            flash("Please enter a valid email address.")
        elif len(password) < 6:
            flash("Password must be at least 6 characters long.")
        else:
            db = get_db()
            existing_user = db.execute(
                "SELECT 1 FROM users WHERE LOWER(email) = ?", (email,)
            ).fetchone()
            if existing_user:
                flash("This email is already registered. Please log in.")
            else:
                pw_hash = generate_password_hash(password)
                db.execute(
                    "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, 'student')",
                    (name, email, pw_hash)
                )
                db.commit()
                flash("Registration successful! You can now log in.")
                return redirect(url_for("login"))

    return render_template("register.html")


def authenticate_user(required_role, template_name, destination_endpoint):
    """Helper to authenticate credentials and assign session role."""
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE LOWER(email) = ? AND role = ?",
            (email, required_role)
        ).fetchone()

        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["user_id"]
            session["name"] = user["name"]
            session["email"] = user["email"]
            session["role"] = required_role
            flash(f"Welcome back, {user['name']}!")
            return redirect(url_for(destination_endpoint))

        flash("Invalid email or password.")

    return render_template(template_name)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Student login endpoint."""
    if session.get("role") == "student":
        return redirect(url_for("menu"))
    return authenticate_user("student", "login.html", "menu")


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    """Dedicated Administrator login endpoint."""
    if session.get("role") == "admin":
        return redirect(url_for("admin_dashboard"))
    return authenticate_user("admin", "admin_login.html", "admin_dashboard")


@app.route("/logout")
def logout():
    """Clears user session and logs out."""
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for("index"))


# ==============================================================================
# STUDENT FUNCTIONALITY ROUTES
# ==============================================================================
@app.route("/menu")
@login_required
def menu():
    """Food menu with search, category filtering, and availability display."""
    search_query = request.args.get("q", "").strip()
    selected_category = request.args.get("category", "").strip()

    sql = "SELECT * FROM food_items WHERE 1=1"
    params = []

    if search_query:
        sql += " AND (food_name LIKE ? OR description LIKE ?)"
        term = f"%{search_query}%"
        params.extend([term, term])

    if selected_category and selected_category in CATEGORIES:
        sql += " AND category = ?"
        params.append(selected_category)

    sql += " ORDER BY category ASC, food_name ASC"

    db = get_db()
    foods = db.execute(sql, params).fetchall()

    return render_template(
        "menu.html",
        foods=foods,
        q=search_query,
        cat=selected_category,
        categories=CATEGORIES
    )


@app.route("/cart")
@login_required
def cart():
    """Displays cart items, subtotal, total, and pickup time order form."""
    items, total = cart_items()
    return render_template("cart.html", items=items, total=total)


@app.route("/cart/add/<int:food_id>", methods=["POST"])
@login_required
def add_to_cart(food_id):
    """Adds available food item to session cart."""
    db = get_db()
    food = db.execute("SELECT * FROM food_items WHERE food_id = ?", (food_id,)).fetchone()

    if food and food["availability"] == "Available":
        cart = session.get("cart", {})
        if not isinstance(cart, dict):
            cart = {}
        fid_str = str(food_id)
        cart[fid_str] = cart.get(fid_str, 0) + 1
        session["cart"] = cart
        flash(f"'{food['food_name']}' added to your cart.")
    else:
        flash("Sorry, this item is currently out of stock.")

    return redirect(request.referrer or url_for("menu"))


@app.route("/cart/update/<int:food_id>/<action>", methods=["POST"])
@login_required
def update_cart(food_id, action):
    """Updates cart quantities: increment, decrement, or remove."""
    cart = session.get("cart", {})
    if not isinstance(cart, dict):
        cart = {}
    fid_str = str(food_id)

    if action == "inc":
        cart[fid_str] = cart.get(fid_str, 0) + 1
    elif action == "dec":
        cart[fid_str] = cart.get(fid_str, 0) - 1
    elif action == "remove":
        cart.pop(fid_str, None)

    if fid_str in cart and cart[fid_str] <= 0:
        cart.pop(fid_str, None)

    session["cart"] = cart
    return redirect(url_for("cart"))


@app.route("/checkout", methods=["POST"])
@login_required
def checkout():
    """
    Places an order:
    1. Verifies food availability and calculates verified total on server.
    2. Uses SQLite database transactions to store order and order_items atomically.
    """
    items, total = cart_items()
    pickup_time = request.form.get("pickup_time", "").strip()

    if not items:
        flash("Your cart is empty. Add food items before placing an order.")
        return redirect(url_for("cart"))

    if not pickup_time:
        flash("Please select a preferred pickup time.")
        return redirect(url_for("cart"))

    # Server-side verification of item availability
    unavailable_items = [i["food"]["food_name"] for i in items if i["food"]["availability"] != "Available"]
    if unavailable_items:
        flash(f"The following items are out of stock. Please remove them: {', '.join(unavailable_items)}")
        return redirect(url_for("cart"))

    # Database Transaction
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(
            """
            INSERT INTO orders (user_id, total_amount, pickup_time, order_status)
            VALUES (?, ?, ?, 'Pending')
            """,
            (session["user_id"], total, pickup_time)
        )
        order_id = cur.lastrowid

        for item in items:
            cur.execute(
                """
                INSERT INTO order_items (order_id, food_id, quantity, price)
                VALUES (?, ?, ?, ?)
                """,
                (order_id, item["food"]["food_id"], item["qty"], item["food"]["price"])
            )

        db.commit()
    except Exception as e:
        db.rollback()
        flash("A database error occurred while placing your order. Please try again.")
        return redirect(url_for("cart"))

    # Clear cart upon successful transaction
    session.pop("cart", None)
    flash("Order placed successfully!")
    return redirect(url_for("confirmation", order_id=order_id))


@app.route("/confirmation/<int:order_id>")
@login_required
def confirmation(order_id):
    """Displays order confirmation details for the current student."""
    orders = orders_with_items("WHERE o.order_id = ? AND o.user_id = ?", (order_id, session["user_id"]))
    if not orders:
        flash("Order not found.")
        return redirect(url_for("my_orders"))

    order, items = orders[0]
    return render_template("confirmation.html", order=order, items=items)


@app.route("/my-orders")
@login_required
def my_orders():
    """Lists order history and status tracking for the current student."""
    orders = orders_with_items("WHERE o.user_id = ?", (session["user_id"],))
    return render_template("my_orders.html", orders=orders)


# ==============================================================================
# ADMINISTRATOR ROUTES
# ==============================================================================
@app.route("/admin")
@admin_required
def admin_dashboard():
    """Admin dashboard overview with order and menu metrics."""
    db = get_db()
    count_fn = lambda sql, params=(): db.execute(sql, params).fetchone()[0]

    stats = {
        "total": count_fn("SELECT COUNT(*) FROM orders"),
        "pending": count_fn("SELECT COUNT(*) FROM orders WHERE order_status = 'Pending'"),
        "foods": count_fn("SELECT COUNT(*) FROM food_items WHERE availability = 'Available'")
    }
    return render_template("admin_dashboard.html", stats=stats)


@app.route("/admin/foods")
@admin_required
def admin_foods():
    """Manages canteen food items."""
    db = get_db()
    foods = db.execute("SELECT * FROM food_items ORDER BY food_id DESC").fetchall()
    return render_template("admin_foods.html", foods=foods)


@app.route("/admin/foods/add", methods=["GET", "POST"])
@app.route("/admin/foods/edit/<int:food_id>", methods=["GET", "POST"])
@admin_required
def food_form(food_id=None):
    """Creates a new food item or edits an existing item."""
    db = get_db()
    food = None
    if food_id:
        food = db.execute("SELECT * FROM food_items WHERE food_id = ?", (food_id,)).fetchone()
        if not food:
            flash("Food item not found.")
            return redirect(url_for("admin_foods"))

    if request.method == "POST":
        food_name = request.form.get("food_name", "").strip()
        description = request.form.get("description", "").strip()
        price_raw = request.form.get("price", "").strip()
        category = request.form.get("category", "").strip()
        availability = request.form.get("availability", "Available").strip()

        if not food_name:
            flash("Food name is required.")
            return render_template("food_form.html", food=food, categories=CATEGORIES)

        try:
            price = float(price_raw)
            if price < 0:
                raise ValueError()
        except ValueError:
            flash("Please enter a valid non-negative price.")
            return render_template("food_form.html", food=food, categories=CATEGORIES)

        if category not in CATEGORIES:
            category = CATEGORIES[0]

        if availability not in ["Available", "Out of Stock"]:
            availability = "Available"

        # Handle image upload
        uploaded_image = request.files.get("image")
        filename = None
        if uploaded_image and uploaded_image.filename:
            if allowed_file(uploaded_image.filename):
                filename = secure_filename(uploaded_image.filename)
                save_path = os.path.join(UPLOAD_FOLDER, filename)
                uploaded_image.save(save_path)
            else:
                flash("Invalid image format. Allowed: PNG, JPG, JPEG, GIF, WEBP.")
                return render_template("food_form.html", food=food, categories=CATEGORIES)

        if food:
            if filename:
                db.execute(
                    """
                    UPDATE food_items
                    SET food_name = ?, description = ?, price = ?, category = ?, availability = ?, image = ?
                    WHERE food_id = ?
                    """,
                    (food_name, description, price, category, availability, filename, food_id)
                )
            else:
                db.execute(
                    """
                    UPDATE food_items
                    SET food_name = ?, description = ?, price = ?, category = ?, availability = ?
                    WHERE food_id = ?
                    """,
                    (food_name, description, price, category, availability, food_id)
                )
            flash(f"'{food_name}' updated successfully.")
        else:
            db.execute(
                """
                INSERT INTO food_items (food_name, description, price, category, availability, image)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (food_name, description, price, category, availability, filename)
            )
            flash(f"'{food_name}' added successfully.")

        db.commit()
        return redirect(url_for("admin_foods"))

    return render_template("food_form.html", food=food, categories=CATEGORIES)


@app.route("/admin/foods/delete/<int:food_id>", methods=["POST"])
@admin_required
def delete_food(food_id):
    """
    Deletes food item if not ordered yet.
    If present in past orders, safely updates availability to 'Out of Stock' to protect historical records.
    """
    db = get_db()
    referenced_in_orders = db.execute(
        "SELECT 1 FROM order_items WHERE food_id = ?", (food_id,)
    ).fetchone()

    if referenced_in_orders:
        db.execute(
            "UPDATE food_items SET availability = 'Out of Stock' WHERE food_id = ?", (food_id,)
        )
        flash("Item is linked to past orders. To protect history, it has been marked 'Out of Stock'.")
    else:
        db.execute("DELETE FROM food_items WHERE food_id = ?", (food_id,))
        flash("Food item deleted successfully.")

    db.commit()
    return redirect(url_for("admin_foods"))


@app.route("/admin/foods/toggle/<int:food_id>", methods=["POST"])
@admin_required
def toggle_food(food_id):
    """Toggles food item availability between 'Available' and 'Out of Stock'."""
    db = get_db()
    db.execute("""
        UPDATE food_items
        SET availability = CASE availability
            WHEN 'Available' THEN 'Out of Stock'
            ELSE 'Available'
        END
        WHERE food_id = ?
    """, (food_id,))
    db.commit()
    flash("Food availability updated.")
    return redirect(url_for("admin_foods"))


@app.route("/admin/orders")
@admin_required
def admin_orders():
    """Lists all student orders for canteen management."""
    orders = orders_with_items()
    return render_template("admin_orders.html", orders=orders)


@app.route("/admin/orders/<int:order_id>/status", methods=["POST"])
@admin_required
def update_status(order_id):
    """Updates order status: Pending, Accepted, Preparing, Ready, Collected, Rejected."""
    status = request.form.get("status", "").strip()
    if status in ALL_STATUSES:
        db = get_db()
        db.execute("UPDATE orders SET order_status = ? WHERE order_id = ?", (status, order_id))
        db.commit()
        flash(f"Order #{order_id} status updated to '{status}'.")
    else:
        flash("Invalid status specified.")

    return redirect(url_for("admin_orders"))


# ==============================================================================
# MAIN ENTRYPOINT
# ==============================================================================
if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
    print("Running Online Canteen Pre-Ordering System on http://127.0.0.1:5000")
    app.run(debug=True, host="127.0.0.1", port=5000)
