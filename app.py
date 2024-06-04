from flask import Flask, render_template, request, flash, url_for, redirect, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, current_user, logout_user, login_required
from flask_mail import Mail, Message as MailMessage
from itsdangerous import URLSafeTimedSerializer
import base64
from datetime import datetime
from sqlalchemy import asc, desc, func
import os
from sqlalchemy.orm import aliased

app = Flask(__name__)
app.secret_key = os.urandom(12)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///library.db"
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'stevechoi268@gmail.com'
app.config['MAIL_PASSWORD'] = 'dykd bnpa kshc lfpw'
app.config['MAIL_DEFAULT_SENDER'] = 'stevechoi268@gmail.com'

mail = Mail(app)
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Unauthorized Access! Please Login!"
login_manager.login_message_category = "danger"

s = URLSafeTimedSerializer(app.secret_key)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    profile_picture = db.Column(db.LargeBinary)
    role = db.Column(db.String(10), nullable=False)  # "student" or "teacher"
    password_hash = db.Column(db.String(128), nullable=False)
    confirmed = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class UserMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    sent_date = db.Column(db.String(50), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    image = db.Column(db.LargeBinary)
    date = db.Column(db.Date)
    discovered_location = db.Column(db.String(50))
    current_location = db.Column(db.String(50))
    description = db.Column(db.String(255))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    transactions = db.relationship('Transaction', backref='item', lazy=True)
    claimed = db.Column(db.Boolean, default = False)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class ClaimedItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    image = db.Column(db.LargeBinary)
    date = db.Column(db.Date)
    discovered_location = db.Column(db.String(50))
    current_location = db.Column(db.String(50))
    description = db.Column(db.String(255))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    claimed_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

with app.app_context():
    db.create_all()

def get_users_by_last_name(last_name, current_user_id):
    return User.query.filter(User.last_name.ilike(f'%{last_name}%'), User.id != current_user_id).all()

@app.route('/')
def home():
    return render_template('index.html')

def send_email(to, subject, template):
    msg = MailMessage(
        subject=subject,
        recipients=[to]
    )
    msg.html = template
    mail.send(msg)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # Get form data
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        profile_picture = request.files.get("profile_picture")
        role = request.form.get("role")

        # Validate form data
        if not (first_name and last_name and email and password and confirm_password and profile_picture and role):
            flash("Please fill in all fields.", "danger")
            return render_template("register.html")
        
        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("register.html")

        # Check if user already exists
        user = User.query.filter_by(email=email).first()
        if user is not None:
            flash("User already exists! Try a different email.", "danger")
            return render_template("register.html")

        # Get profile picture data
        profile_picture_data = profile_picture.read()

        # Create a new user instance
        new_user = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            profile_picture=profile_picture_data,
            role=role
        )
        new_user.set_password(password)

        # Save the new user to the database
        db.session.add(new_user)
        db.session.commit()

        # Send verification email
        token = s.dumps(email, salt='email-confirm')
        confirm_url = url_for('confirm_email', token=token, _external=True)
        html = render_template('email_confirmation.html', confirm_url=confirm_url)
        subject = "Please confirm your email"
        send_email(email, subject, html)

        flash("A confirmation email has been sent to your email address.", "success")
        session['registered'] = True
        return redirect(url_for('login'))

    return render_template("register.html")

@app.route('/confirm/<token>')
def confirm_email(token):
    try:
        email = s.loads(token, salt='email-confirm', max_age=3600)
    except:
        flash('The confirmation link is invalid or has expired.', 'danger')
        return redirect(url_for('login'))
    
    user = User.query.filter_by(email=email).first_or_404()
    if user.confirmed:
        flash('Account already confirmed. Please login.', 'success')
    else:
        user.confirmed = True
        db.session.add(user)
        db.session.commit()
        flash('You have confirmed your account. Thanks!', 'success')
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get("email")
        password = request.form.get("password")
        # Check if user exists and passwords match
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            # Successful login
            flash('Login successful!', 'success')
            login_user(user)
            session['registered'] = True
            # Redirect to a dashboard or profile page
            return redirect(url_for('account'))  # Replace 'dashboard' with your route for dashboard or profile
        else:
            # Failed login
            flash('Invalid email or password. Please try again.', 'danger')

    # Render the login template
    return render_template('login.html')

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully", "success")
    return render_template("index.html")

@app.route('/account')
@login_required
def account():
    if current_user.is_authenticated and current_user.profile_picture:
        image_data_b64 = base64.b64encode(current_user.profile_picture).decode('utf-8')
    else:
        image_data_b64 = None

    transactions = Transaction.query.filter_by(user_id=current_user.id).all()
    claimed_items = ClaimedItem.query.filter_by(user_id=current_user.id).all()

    return render_template("account.html", user=current_user, profile_picture=image_data_b64, transactions=transactions, recent_claimed_items=claimed_items)

@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    user = current_user
    user.first_name = request.form['first_name']
    user.last_name = request.form['last_name']
    user.email = request.form['email']
    # Save the user object to the database
    db.session.commit()
    flash('Profile updated successfully', 'success')
    return redirect(url_for('account'))

@app.route('/change_password', methods=['POST'])
@login_required
def change_password():
    user = current_user
    old_password = request.form['old_password']
    new_password = request.form['new_password']
    confirm_new_password = request.form['confirm_new_password']
    
    if not user.check_password(old_password):
        flash('Old password is incorrect', 'danger')
        return redirect(url_for('account'))
    
    if new_password != confirm_new_password:
        flash('New passwords do not match', 'danger')
        return redirect(url_for('account'))
    
    user.set_password(new_password)
    # Save the user object to the database
    db.session.commit()
    flash('Password changed successfully', 'success')
    return redirect(url_for('account'))

@app.route("/report", methods=["POST", "GET"])
@login_required
def reportItem():
    if request.method == "GET":
        return render_template("report.html")
    elif request.method == "POST":
        try:
            name = request.form["item_name"]
            image = request.files.get("image")
            date = datetime.strptime(request.form["item_date"], "%Y-%m-%d").date()
            discovered_location = request.form["discovered_location"]
            current_location = request.form["current_location"]
            description = request.form["item_description"]

            image_data = image.read()
            if not isinstance(image_data, (bytes, bytearray)):
                flash("Image data is not in binary format", "danger")
                return render_template("report.html")

            new_item = Item(
                name=name,
                image=image_data,
                date=date,
                discovered_location=discovered_location,
                current_location=current_location,
                description=description,
                user_id=current_user.id  # Set the user_id to the current user's ID
            )
            db.session.add(new_item)
            db.session.commit()

            # Log the transaction
            new_transaction = Transaction(
                item_id=new_item.id,
                user_id=current_user.id,
                timestamp=datetime.utcnow()
            )
            db.session.add(new_transaction)
            db.session.commit()

            flash("Item has been added successfully!", "success")
            return render_template("report.html")
        except IntegrityError:
            db.session.rollback()
            flash("The item is already in the inventory!", "warning")
            return render_template("report.html")

@app.route("/claim_item/<int:item_id>")
@login_required
def claim_item(item_id):
    item = Item.query.get(item_id)
    item.claimed = True
    db.session.commit()

    return redirect(url_for('inventory'))

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
    items_per_page = request.args.get("items_per_page", 10, type=int)
    sort_by_name = request.args.get("sort_by_name", "asc")

    if sort_by_name == "asc":
        items = Item.query.order_by(asc(func.lower(Item.name))).paginate(page=page, per_page=items_per_page, error_out=False)
    else:
        items = Item.query.order_by(desc(func.lower(Item.name))).paginate(page=page, per_page=items_per_page, error_out=False)

    for item in items.items:
        if item.image:
            item.image_base64 = base64.b64encode(item.image).decode('utf-8')

    return render_template("inventory.html", items=items, sort_by_name=sort_by_name, items_per_page=items_per_page)

@app.route("/contact/<int:user_id>")
@login_required
def contact(user_id):
    return render_template("contact.html", user_id=user_id)

@app.route("/search_users/<int:user_id>", methods=["GET"])
@login_required
def search_users(user_id):
    last_name = request.args.get("last_name", "")
    users = get_users_by_last_name(last_name, user_id)
    users_list = [{'id': user.id, 'first_name': user.first_name, 'last_name': user.last_name} for user in users]
    return jsonify(users_list)

@app.route("/send_message/<int:receiver_id>", methods=["POST"])
@login_required
def send_message(receiver_id):
    sender_id = request.form['sender_id']
    subject = request.form['subject']
    message = request.form['message']
    sent_date = request.form['sent_date']
    
    new_message = UserMessage(sender_id=sender_id, receiver_id=receiver_id, subject=subject, message=message, sent_date=sent_date)
    db.session.add(new_message)
    db.session.commit()
    
    flash('Message sent successfully!', 'success')
    return redirect(url_for('contact', user_id=sender_id))

@app.route("/messages/<int:user_id>")
@login_required
def received_messages(user_id):
    user = User.query.get(user_id)
    sender = aliased(User)
    messages = db.session.query(UserMessage, sender).filter(UserMessage.receiver_id == user_id, UserMessage.sender_id == sender.id).all()
    return render_template("messages.html", user=user, messages=messages)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
