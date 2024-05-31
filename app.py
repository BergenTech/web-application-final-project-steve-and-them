from flask import Flask, render_template, request, flash, url_for, redirect
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, current_user, logout_user, login_required
import random, base64
from datetime import datetime
from sqlalchemy import desc, asc
import os

app = Flask(__name__)
app.secret_key = os.urandom(12)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///library.db"
# login_manager = LoginManager(app)
# login_manager.login_view = 'login'
# login_manager.login_message = "Unauthorized Access! Please Login!"
# login_manager.login_message_category = "danger"

db = SQLAlchemy(app)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(255), unique=True, nullable=False)
    last_name = db.Column(db.String(255), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Item(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(50), unique=True)
    # image = db.Column(db.Image)
    date = db.Column(db.Date)
    description = db.Column(db.String(255), unique=True)

    def __repr__(self):
        return f"Book: {self.name}"

with app.app_context():
    db.create_all()



@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
        # Extract form data
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get("confirm_password")
        phone_number = request.form.get('phone_number')
        role = request.form.get("role")

        if not (
            first_name
            and last_name
            and password
            and confirm_password
            and phone_number
            and email
            and role
        ):
            flash("Please fill in all fields.", "danger")
            return render_template('register.html')
        user = User.query.filter_by(email=email).first()
        if user is not None and email == user.email:
            flash("An account already exists under this email. Try a different email or login", "danger")
            return render_template('register.html')
        if password != confirm_password:
            flash("Passwords do not match, please try again", "danger")
            return render_template('register.html')
        else:
            flash("Login Successful!", "success")
            return render_template('register.html')

@app.route('/login', methods=['POST', 'GET'])
def login():
    return render_template("login.html")

@app.route('/account')
def account():
    return render_template("account.html")

@app.route("/report", methods=["POST", "GET"])
def reportItem():
    if request.method == "GET":
        return render_template("report.html")
    elif request.method == "POST":
        try:
            new_item = Item(
                name = request.form["item_name"],
                # image = request.form["item_image"],
                date = datetime.strptime(request.form["item_date"], "%Y-%m-%d").date(),
                description = request.form["item_description"]
            )
            db.session.add(new_item)
            db.session.commit()
            flash("Item has been added successfully!", "success")
            return render_template("report.html")
        except IntegrityError:
            db.session.rollback()
            flash("The book is already in the inventory!", "warning")
            return render_template("report.html")

def get_page_range(current_page, total_pages, max_page_buttons=5):
    if total_pages <= max_page_buttons:
        return range(1, total_pages+1)
    
    half_buttons = max_page_buttons // 2
    if current_page <= half_buttons:
        return range(1, max_page_buttons + 1)
    
    if current_page >= total_pages - half_buttons:
        return range(total_pages - max_page_buttons + 1, total_pages + 1)

    return range(current_page - half_buttons, current_page + half_buttons + 1)

@app.route("/inventory")
def inventory():
    page = request.args.get("page", 1, type=int)
    items_per_page = request.args.get("items_per_page", 20, type=int)
    items = Item.query.order_by(asc(Item.id)).paginate(page = page, per_page = items_per_page, error_out = False)
    return render_template("inventory.html", items = items, get_page_range = get_page_range, items_per_page = items_per_page)

if __name__ == '__main__':
    app.run(debug=True)
    app.secret_key = "secret_key"
