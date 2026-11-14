# Online Canteen Pre-Ordering System

A complete Python Flask web application designed for college canteens to allow students to pre-order food, choose pickup times, and avoid long waiting queues, with an administrative dashboard for canteen staff to manage inventory and fulfill orders.

---

## 🛠️ Technologies
- **Python 3.10+**
- **Flask** (Micro web framework)
- **SQLite 3** (`database.db`)
- **HTML5 & Jinja2** templating
- **CSS3 & FontAwesome** (Responsive layout)
- **Werkzeug** (Secure password hashing with PBKDF2/scrypt)

---

## 📂 Project Structure
```text
├── app.py                   # Main Flask application & route controller
├── database.db              # SQLite database (auto-generated)
├── init_db.py               # Database initialization & seeding script
├── test_app.py              # Automated integration test suite
├── requirements.txt         # Python dependencies
├── README.md                # Project documentation
├── static/
│   ├── style.css            # Stylesheet for student & admin UI
│   └── images/              # Food item image uploads
└── templates/               # Jinja2 HTML templates
    ├── base.html            # Common layout & navigation bar
    ├── index.html           # Public landing page
    ├── register.html        # Student registration page
    ├── login.html           # Student login page
    ├── menu.html            # Menu browsing, search & category filter
    ├── cart.html            # Shopping cart & pickup time checkout
    ├── confirmation.html    # Order confirmation screen
    ├── my_orders.html       # Student order history & status tracking
    ├── admin_login.html     # Dedicated canteen administrator login
    ├── admin_dashboard.html # Admin dashboard with operational statistics
    ├── admin_foods.html     # Food items inventory management
    ├── food_form.html       # Add / Edit food item form
    └── admin_orders.html    # Admin order management & status updates
```

---

## 🗄️ Database Tables (`database.db`)

1. **`users`**
   - `user_id` (INTEGER, Primary Key, AUTOINCREMENT)
   - `name` (TEXT, NOT NULL)
   - `email` (TEXT, UNIQUE, NOT NULL)
   - `password_hash` (TEXT, NOT NULL)
   - `role` (TEXT, NOT NULL - `'student'` or `'admin'`)

2. **`food_items`**
   - `food_id` (INTEGER, Primary Key, AUTOINCREMENT)
   - `food_name` (TEXT, NOT NULL)
   - `description` (TEXT)
   - `price` (REAL, NOT NULL)
   - `category` (TEXT, NOT NULL - `'Snacks'`, `'Meals'`, `'Beverages'`, `'Fast Food'`)
   - `image` (TEXT, optional filename)
   - `availability` (TEXT, NOT NULL - `'Available'` or `'Out of Stock'`)

3. **`orders`**
   - `order_id` (INTEGER, Primary Key, AUTOINCREMENT)
   - `user_id` (INTEGER, Foreign Key referencing `users(user_id)`)
   - `total_amount` (REAL, NOT NULL)
   - `pickup_time` (TEXT, NOT NULL)
   - `order_status` (TEXT, NOT NULL - `'Pending'`, `'Accepted'`, `'Preparing'`, `'Ready'`, `'Collected'`, `'Rejected'`)
   - `created_at` (TIMESTAMP, DEFAULT CURRENT_TIMESTAMP)

4. **`order_items`**
   - `order_item_id` (INTEGER, Primary Key, AUTOINCREMENT)
   - `order_id` (INTEGER, Foreign Key referencing `orders(order_id)`)
   - `food_id` (INTEGER, Foreign Key referencing `food_items(food_id)`)
   - `quantity` (INTEGER, NOT NULL)
   - `price` (REAL, NOT NULL)

---

## 🔐 Default Demo Accounts

| Role | Email | Password |
|---|---|---|
| **Administrator** | `admin@canteen.com` | `admin123` |
| **Student** | `student@canteen.com` | `student123` |

---

## 🚀 How to Run in Visual Studio Code

### 1. Open Project in VS Code
- Open VS Code.
- Go to **File** > **Open Folder...** and select this directory.

### 2. Open the Integrated Terminal
- Press ``Ctrl + ` `` (Backtick) or go to **Terminal** > **New Terminal**.

### 3. Create and Activate a Virtual Environment
**On Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```
*(If you encounter execution policy restrictions, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first).*

**On Windows (Command Prompt):**
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

**On macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Initialize Database (Optional / Automatic)
The database auto-initializes upon launching `app.py`, but you can also seed it manually:
```bash
python init_db.py
```

### 6. Run the Application
```bash
python app.py
```

### 7. Access in Your Browser
- Student Portal: [http://127.0.0.1:5000](http://127.0.0.1:5000)
- Admin Login: [http://127.0.0.1:5000/admin/login](http://127.0.0.1:5000/admin/login)

---

## 🧪 Running Automated Tests
To run the automated 14-point test suite:
```bash
python test_app.py
```
