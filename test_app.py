"""
Comprehensive test suite for Online Canteen Pre-Ordering System.
Tests authentication, student operations, cart & transactions, admin actions, and RBAC.
"""
from app import app, get_db, init_db

def test_full_system():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    
    import os
    if os.path.exists("database.db"):
        os.remove("database.db")
    
    with app.test_client() as client:
        # Re-initialize DB
        with app.app_context():
            init_db()

        # 1. Landing Page
        res = client.get("/")
        assert res.status_code == 200
        assert b"College Canteen Pre-Ordering" in res.data
        print("[PASS] 1. Landing page loaded")

        # 2. Student Registration
        res = client.post("/register", data={
            "name": "Alice Wonderland",
            "email": "alice@student.com",
            "password": "secretpassword"
        }, follow_redirects=True)
        assert res.status_code == 200
        assert b"Registration successful" in res.data
        print("[PASS] 2. Student registration successful")

        # Duplicate Registration
        res = client.post("/register", data={
            "name": "Alice Duplicate",
            "email": "alice@student.com",
            "password": "secretpassword"
        }, follow_redirects=True)
        assert b"already registered" in res.data
        print("[PASS] 2b. Duplicate registration properly blocked")

        # 3. Student Login
        res = client.post("/login", data={
            "email": "alice@student.com",
            "password": "secretpassword"
        }, follow_redirects=True)
        assert res.status_code == 200
        assert b"Welcome, Alice Wonderland!" in res.data
        print("[PASS] 3. Student login successful")

        # 4. View Menu, Search, Category Filter
        res = client.get("/menu")
        assert res.status_code == 200
        assert b"Samosa" in res.data
        assert b"Masala Dosa" in res.data

        # Search
        res = client.get("/menu?q=Samosa")
        assert b"Samosa" in res.data
        assert b"Masala Dosa" not in res.data
        print("[PASS] 4. Menu view and search working")

        # Filter
        res = client.get("/menu?category=Beverages")
        assert b"Cold Coffee" in res.data
        assert b"Samosa" not in res.data
        print("[PASS] 4b. Category filter working")

        # 5. Add to Cart & Update Quantities
        # Add Samosa (food_id=1)
        res = client.post("/cart/add/1", follow_redirects=True)
        assert res.status_code == 200
        assert b"added to your cart" in res.data

        # Add Veg Puff (food_id=2)
        client.post("/cart/add/2", follow_redirects=True)

        # View Cart
        res = client.get("/cart")
        assert b"Samosa" in res.data
        assert b"Veg Puff" in res.data
        print("[PASS] 5. Add to cart working")

        # Increment Samosa
        client.post("/cart/update/1/inc", follow_redirects=True)
        # Decrement Veg Puff
        client.post("/cart/update/2/dec", follow_redirects=True)
        # Veg Puff qty is now 0, should be removed
        res = client.get("/cart")
        assert b"Samosa" in res.data
        assert b"Veg Puff" not in res.data
        print("[PASS] 5b. Update quantities and removal working")

        # 6. Checkout & Place Order (Server Price Calculation & Transaction)
        res = client.post("/checkout", data={
            "pickup_time": "12:30"
        }, follow_redirects=True)
        assert res.status_code == 200
        assert b"Order Placed!" in res.data
        assert b"12:30" in res.data
        print("[PASS] 6. Order placement and database transaction working")

        # 7. Check Confirmation & My Orders
        res = client.get("/my-orders")
        assert res.status_code == 200
        assert b"Order #" in res.data
        assert b"Pending" in res.data
        print("[PASS] 7. My orders tracking working")

        # 8. Student Logout
        res = client.get("/logout", follow_redirects=True)
        assert b"logged out" in res.data
        print("[PASS] 8. Logout working")

        # 9. RBAC: Student accessing admin route without admin privileges
        res = client.get("/admin", follow_redirects=True)
        assert b"Administrator login required" in res.data
        print("[PASS] 9. Admin route properly protected against unauthorized access")

        # 10. Admin Login
        res = client.post("/admin/login", data={
            "email": "admin@canteen.com",
            "password": "admin123"
        }, follow_redirects=True)
        assert res.status_code == 200
        assert b"Admin Dashboard" in res.data
        print("[PASS] 10. Admin login successful")

        # 11. Admin Dashboard Statistics
        res = client.get("/admin")
        assert b"Total Orders" in res.data
        assert b"Pending Orders" in res.data
        assert b"Available Food Items" in res.data
        print("[PASS] 11. Admin dashboard metrics working")

        # 12. Admin View Orders & Status Update
        res = client.get("/admin/orders")
        assert res.status_code == 200
        assert b"Alice Wonderland" in res.data
        assert b"12:30" in res.data

        # Update order status to 'Accepted'
        res = client.post("/admin/orders/1/status", data={
            "status": "Accepted"
        }, follow_redirects=True)
        assert b"status updated" in res.data and b"Accepted" in res.data

        # Update order status to 'Preparing'
        res = client.post("/admin/orders/1/status", data={
            "status": "Preparing"
        }, follow_redirects=True)
        assert b"status updated" in res.data and b"Preparing" in res.data
        print("[PASS] 12. Admin order management and status update working")

        # 13. Admin Food Management
        # Add new food item
        res = client.post("/admin/foods/add", data={
            "food_name": "Special Brownie",
            "description": "Rich chocolate walnut brownie",
            "price": "50.00",
            "category": "Snacks",
            "availability": "Available"
        }, follow_redirects=True)
        assert b"Special Brownie" in res.data
        assert b"added successfully" in res.data

        # Toggle availability
        with app.app_context():
            db = get_db()
            brownie = db.execute("SELECT food_id FROM food_items WHERE food_name = 'Special Brownie'").fetchone()
            brownie_id = brownie["food_id"]

        res = client.post(f"/admin/foods/toggle/{brownie_id}", follow_redirects=True)
        assert b"Food availability updated" in res.data

        # Edit food item
        res = client.post(f"/admin/foods/edit/{brownie_id}", data={
            "food_name": "Choco Fudge Brownie",
            "description": "Warm chocolate fudge brownie",
            "price": "60.00",
            "category": "Snacks",
            "availability": "Available"
        }, follow_redirects=True)
        assert b"Choco Fudge Brownie" in res.data
        assert b"updated successfully" in res.data

        # Delete food item
        res = client.post(f"/admin/foods/delete/{brownie_id}", follow_redirects=True)
        assert b"deleted successfully" in res.data
        print("[PASS] 13. Admin food CRUD and toggle availability working")

        # 14. RBAC: Admin accessing student route
        res = client.get("/menu", follow_redirects=True)
        assert b"Please log in as a student" in res.data
        print("[PASS] 14. Student route properly protected from admin role")

    print("\nALL 14 INTEGRATION TESTS PASSED WITH 100% SUCCESS!")

if __name__ == "__main__":
    test_full_system()
