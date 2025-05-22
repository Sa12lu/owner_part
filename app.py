import os
import io
import base64
from markupsafe import Markup  # ✅ CORRECT
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask import send_file
from flask import Response
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# MySQL Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/flask_app'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# File Upload Configuration
UPLOAD_FOLDER = 'static/uploads/'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

hashed = generate_password_hash('admin123', method='pbkdf2:sha256')
print(hashed)

# Database Models
class Owner(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class BuyStock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    price = db.Column(db.Float, nullable=False)
    image_data = db.Column(db.LargeBinary, nullable=True)  # Optional image storage
    image_mimetype = db.Column(db.String(50))
    quantity = db.Column(db.Integer, nullable=False)
    datetime = db.Column(db.DateTime, default=datetime.utcnow)

class RecordSk(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    price = db.Column(db.Float, nullable=False)
    image_data = db.Column(db.LargeBinary, nullable=True)
    image_mimetype = db.Column(db.String(50))
    quantity = db.Column(db.Integer, nullable=False)
    datetime = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(10), default='Pending')  # Accept / Reject / Pending

with app.app_context():
    db.create_all()

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        owner_user = Owner.query.filter_by(username=username).first()

        if owner_user and check_password_hash(owner_user.password, password):
            session['username'] = username
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials.', 'danger')

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'username' in session:
        return render_template('dashboard.html', username=session['username'])
    else:
        flash('You need to log in first.', 'warning')
        return redirect(url_for('login'))

@app.route('/buy-stock')
def buy_stock():
    stock_items = BuyStock.query.order_by(BuyStock.datetime.desc()).all()
    message = session.pop('message', None)  # Get and remove message
    return render_template('buy_stock.html', stock_items=stock_items,message=message)

@app.route('/buystock-image/<int:stock_id>')
def buystock_image(stock_id):
    stock_item = BuyStock.query.get_or_404(stock_id)
    if stock_item.image_data:
        return Response(stock_item.image_data, mimetype=stock_item.image_mimetype)
    return '', 404

@app.route('/accept-stock/<int:stock_id>', methods=['GET'])
def accept_stock(stock_id):
    stock_item = BuyStock.query.get_or_404(stock_id)
    new_record = RecordSk(
        product_name=stock_item.product_name,
        description=stock_item.description,
        price=stock_item.price,
        image_data=stock_item.image_data,
        image_mimetype=stock_item.image_mimetype,
        quantity=stock_item.quantity,
        datetime=stock_item.datetime,
        status='Accept'
    )
    db.session.add(new_record)
    db.session.commit()
    return redirect(url_for('buy_stock'))

@app.route('/reject-stock/<int:stock_id>', methods=['GET'])
def reject_stock(stock_id):
    stock_item = BuyStock.query.get_or_404(stock_id)
    new_record = RecordSk(
        product_name=stock_item.product_name,
        description=stock_item.description,
        price=stock_item.price,
        image_data=stock_item.image_data,
        image_mimetype=stock_item.image_mimetype,
        quantity=stock_item.quantity,
        datetime=stock_item.datetime,
        status='Reject'
    )
    db.session.add(new_record)
    db.session.commit()
    return redirect(url_for('buy_stock'))


@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

if __name__ == "__main__":
    print("Starting Flask app...")
    app.run(host="0.0.0.0", port=5002, debug=True)