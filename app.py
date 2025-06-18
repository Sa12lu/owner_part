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
from matplotlib.figure import Figure
from fpdf import FPDF
from PIL import Image
from sqlalchemy import func
from collections import defaultdict
from io import BytesIO
import re
import tempfile



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
    note = db.Column(db.Text, nullable=True)  # add notes
    buy_stock_id = db.Column(db.Integer, db.ForeignKey('buy_stock.id'), unique=True)
    # New column to track whether the gift is newly added
    is_new = db.Column(db.Boolean, default=True)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=True)
    description = db.Column(db.String(500), nullable=True)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    priority = db.Column(db.String(10), nullable=False, default='Low')
    image_filename = db.Column(db.String(100), nullable=True)
    quantity_updated_at = db.Column(db.DateTime, nullable=True)  # New column

class SaleProduct(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500), nullable=True)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    image_data = db.Column(db.LargeBinary, nullable=True)  
    image_mimetype = db.Column(db.String(50), nullable=True)  

class PurchasedProduct(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(50), nullable=False, default="Pending")
    username = db.Column(db.String(150), nullable=False)  # Add this line
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)  # add NEW time date
    sale_product_id = db.Column(db.Integer, db.ForeignKey('sale_product.id'), nullable=False)  # ✅ NEW

class GiftBooking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    gift_name = db.Column(db.String(100), nullable=False)  # Added gift name 
    image_data = db.Column(db.LargeBinary, nullable=True)
    image_mimetype = db.Column(db.String(50))
    description = db.Column(db.String(255), nullable=False)
    price = db.Column(db.Float, nullable=False)
    amount = db.Column(db.Integer, nullable=False)

class Booked(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    gift_id = db.Column(db.Integer, db.ForeignKey('gift_booking.id'), nullable=False)  # ← new line
    gift_name = db.Column(db.String(100), nullable=False)  # ← Add this line
    description = db.Column(db.String(255), nullable=False)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    datetime = db.Column(db.DateTime, default=datetime.utcnow)
    customer_name = db.Column(db.String(150), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('cust_user.id'))  
    status = db.Column(db.String(50), default='Pending')
    notified = db.Column(db.Boolean, default=False)

class Stock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    price = db.Column(db.Float, nullable=False)
    image_data = db.Column(db.LargeBinary, nullable=True)  # Optional image storage
    image_mimetype = db.Column(db.String(50))
    #quantity = db.Column(db.Integer, default=0)

class ListStock(db.Model):
    __tablename__ = 'list_stock'
    id = db.Column(db.Integer, primary_key=True)
    stock_id = db.Column(db.Integer, db.ForeignKey('stock.id'), nullable=False)
    product_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    recorded_datetime = db.Column(db.DateTime, nullable=False)  # renamed from 'datetime'
    checklist_datetime = db.Column(db.DateTime, default=datetime.utcnow)

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
            return render_template('login.html', message="Login successful!", category="success", redirect_url=url_for('dashboard'))
        else:
            return render_template('login.html', message="Invalid credentials.", category="error")

    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login', message='You need to log in first.'))

    message = request.args.get('message')

    # ✅ Stock chart data from ListStock
    from sqlalchemy import func
    stock_data = db.session.query(
        ListStock.product_name,
        func.sum(ListStock.quantity)
    ).group_by(ListStock.product_name).all()

    stock_labels = [row[0] for row in stock_data]
    stock_quantities = [row[1] for row in stock_data]

    # ✅ Gift chart data from Booked
    gift_data = db.session.query(
        Booked.gift_name,
        func.sum(Booked.quantity)
    ).group_by(Booked.gift_name).all()

    gift_labels = [row[0] for row in gift_data]
    gift_quantities = [row[1] for row in gift_data]

    return render_template(
        'dashboard.html',
        username=session['username'],
        message=message,
        stock_labels=stock_labels,
        stock_quantities=stock_quantities,
        gift_labels=gift_labels,
        gift_quantities=gift_quantities
    )




@app.route('/buy-stock')
def buy_stock():
    stock_items = BuyStock.query.order_by(BuyStock.datetime.desc()).all()
    records = RecordSk.query.all()  # Existing records
    history_records = RecordSk.query.filter(RecordSk.status != 'Pending').all()  # History
    list_stock_items = ListStock.query.order_by(ListStock.checklist_datetime.desc()).all()  # Add ListStock items
    message = session.pop('message', None)
    return render_template(
        'buy_stock.html', 
        stock_items=stock_items, 
        message=message, 
        records=records, 
        history_records=history_records,
        list_stock_items=list_stock_items  # Pass to template
    )



@app.route('/buystock-image/<int:stock_id>')
def buystock_image(stock_id):
    stock_item = BuyStock.query.get_or_404(stock_id)
    if stock_item.image_data:
        return Response(stock_item.image_data, mimetype=stock_item.image_mimetype)
    return '', 404

def create_record(stock_id, status):
    stock_item = BuyStock.query.get_or_404(stock_id)
    existing_record = RecordSk.query.filter_by(buy_stock_id=stock_id).first()

    if existing_record:
        if existing_record.status == 'Pending':
            existing_record.status = status
            db.session.commit()
            return redirect(url_for('buy_stock'))
        else:
            flash("Action already taken on this stock item.", "stock")
            return redirect(url_for('buy_stock'))

    new_record = RecordSk(
        product_name=stock_item.product_name,
        description=stock_item.description,
        price=stock_item.price,
        image_data=stock_item.image_data,
        image_mimetype=stock_item.image_mimetype,
        quantity=stock_item.quantity,
        datetime=stock_item.datetime,
        status=status,
        buy_stock_id=stock_id
    )
    db.session.add(new_record)
    db.session.commit()
    return redirect(url_for('buy_stock'))


@app.route('/accept-stock/<int:stock_id>')
def accept_stock(stock_id):
    return create_record(stock_id, 'Accept')

@app.route('/reject-stock/<int:stock_id>')
def reject_stock(stock_id):
    return create_record(stock_id, 'Reject')


@app.route('/add_note/<int:stock_id>', methods=['POST'])
def add_note(stock_id):
    note_content = request.form.get('note', '')
    stock_record = RecordSk.query.filter_by(buy_stock_id=stock_id).first()

    if stock_record:
        # Update existing record
        stock_record.note = note_content
    else:
        # Create new record with Pending status
        stock_item = BuyStock.query.get_or_404(stock_id)
        new_record = RecordSk(
            product_name=stock_item.product_name,
            description=stock_item.description,
            price=stock_item.price,
            image_data=stock_item.image_data,
            image_mimetype=stock_item.image_mimetype,
            quantity=stock_item.quantity,
            datetime=stock_item.datetime,
            status='Pending',
            note=note_content,
            buy_stock_id=stock_id
        )
        db.session.add(new_record)

    db.session.commit()
    return redirect(url_for('buy_stock'))

@app.route('/report')
def report():
    list_stock_items = ListStock.query.order_by(ListStock.checklist_datetime.desc()).all()
    return render_template('report.html', list_stock_items=list_stock_items)

@app.route('/inventory/pdf', methods=['POST'])
def download_inventory_pdf():
    products = Product.query.all()
    data = request.get_json()
    chart_data_url = data.get("chart")

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Inventory Report", ln=True, align='C')
    pdf.ln(10)

     # New line: Add timestamp under title
    now_str = datetime.now().strftime("Generated on: %Y-%m-%d %H:%M:%S")
    pdf.set_font("Arial", size=10)
    pdf.cell(200, 10, txt=now_str, ln=True, align='C')  # center aligned
    pdf.ln(10)

    # Add chart image
    if chart_data_url:
        try:
            print("Received base64 image string:", chart_data_url[:50])  # Just preview first 50 chars

            chart_data = base64.b64decode(chart_data_url.split(',')[1])
            image = Image.open(io.BytesIO(chart_data))
            image_path = 'temp_chart.png'
            image.save(image_path)

            if os.path.exists(image_path):
                pdf.image(image_path, x=10, y=None, w=pdf.w - 20)
                print("✅ Chart image added to PDF.")
            else:
                print("❌ temp_chart.png not found.")
                pdf.cell(200, 10, txt="Chart image not saved correctly.", ln=True)

        except Exception as e:
            print("❌ Error processing image:", e)
            pdf.cell(200, 10, txt=f"Error adding chart: {e}", ln=True)
    else:
        print("❌ No chart_data_url received.")


    # Stats
    total = sum(p.quantity for p in products)
    avg = total / len(products) if products else 0
    max_product = max(products, key=lambda x: x.quantity, default=None)
    min_product = min(products, key=lambda x: x.quantity, default=None)

    pdf.set_font("Arial", size=11)
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"Total Products: {len(products)}", ln=True)
    pdf.cell(200, 10, txt=f"Total Quantity in Stock: {total}", ln=True)
    pdf.cell(200, 10, txt=f"Average Stock per Product: {round(avg, 2)}", ln=True)

    if max_product:
        pdf.cell(200, 10, txt=f"Most Stocked Product: {max_product.name} ({max_product.quantity})", ln=True)
    if min_product:
        pdf.cell(200, 10, txt=f"Least Stocked Product: {min_product.name} ({min_product.quantity})", ln=True)

    pdf.ln(10)
    pdf.set_font("Arial", 'B', size=12)
    pdf.cell(200, 10, txt="Detailed Inventory", ln=True)
    pdf.set_font("Arial", size=11)

    for i, p in enumerate(products, start=1):
        pdf.cell(200, 10, txt=f"{i}. {p.name} - Quantity: {p.quantity}", ln=True)

    # Output as bytes
    pdf_output = pdf.output(dest='S').encode('latin1')
    pdf_buffer = io.BytesIO(pdf_output)

    filename = f"inventory_report_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    return send_file(pdf_buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')

@app.route('/inventory')
def inventory():
    products = Product.query.all()
    return render_template('inventory.html', products=products)


@app.route('/product')
def product():
    results = db.session.query(
        PurchasedProduct.sale_product_id,
        func.sum(PurchasedProduct.quantity)
    ).group_by(PurchasedProduct.sale_product_id).all()

    product_names = {p.id: p.name for p in SaleProduct.query.all()}
    labels = [product_names.get(sale_product_id, f"Product {sale_product_id}") for sale_product_id, _ in results]
    quantities = [qty for _, qty in results]

    # Zip product name and quantity for easy display
    product_data = list(zip(labels, quantities))

    if quantities:
        max_qty = max(quantities)
        max_index = quantities.index(max_qty)
        max_product_label = labels[max_index]

        min_qty = min(quantities)
        min_index = quantities.index(min_qty)
        min_product_label = labels[min_index]
    else:
        max_qty = min_qty = 0
        max_product_label = min_product_label = "N/A"

    return render_template(
        'product.html',
        labels=labels,
        quantities=quantities,
        max_product_label=max_product_label,
        max_qty=max_qty,
        min_product_label=min_product_label,
        min_qty=min_qty,
        product_data=product_data  # ✅ Pass zipped data
    )

@app.route('/product/pdf', methods=['POST'])
def generate_product_pdf():
    try:
        data = request.get_json()
        image_data = data.get('chart', '')

        if not image_data:
            return {'error': 'No chart data provided'}, 400

        # Remove the base64 header
        image_data = re.sub('^data:image/.+;base64,', '', image_data)

        # Decode and convert image
        image_bytes = base64.b64decode(image_data)
        image = Image.open(BytesIO(image_bytes))
        if image.mode == "RGBA":
            image = image.convert("RGB")

        # Save image to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
            image.save(tmp_file, format='JPEG')
            tmp_file_path = tmp_file.name

        # Build PDF
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, "Product Stock Report", ln=True, align='C')
        pdf.set_font("Arial", '', 12)
        pdf.cell(0, 10, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align='C')
        pdf.ln(10)
        pdf.image(tmp_file_path, x=15, w=180)
        pdf.ln(10)

        # Remove the temporary image file
        os.remove(tmp_file_path)

        # Output to buffer
        pdf_output = pdf.output(dest='S').encode('latin1')
        pdf_buffer = BytesIO(pdf_output)

        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            download_name='product_report.pdf',
            as_attachment=True
        )

    except Exception as e:
        print(f"[PDF Error] {str(e)}")
        return {'error': str(e)}, 500
    
@app.route('/daily-sale')
def daily_sale():
    product = request.args.get('product')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    query = db.session.query(
        func.date(PurchasedProduct.timestamp).label('date'),
        func.sum(PurchasedProduct.quantity).label('total_quantity')
    ).filter(PurchasedProduct.name == product)

    # Apply date range filtering if both dates are provided
    if start_date and end_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            query = query.filter(func.date(PurchasedProduct.timestamp) >= start_dt.date(),
                                 func.date(PurchasedProduct.timestamp) <= end_dt.date())
        except ValueError:
            pass

    query = query.group_by(func.date(PurchasedProduct.timestamp))\
                 .order_by(func.date(PurchasedProduct.timestamp))\
                 .all()

    dates = [str(row.date) for row in query]
    quantities = [row.total_quantity for row in query]

    return render_template('daily_sale.html', product=product, dates=dates, quantities=quantities,
                           start_date=start_date, end_date=end_date)

@app.route('/gift')
def gift():
    # Step 1: Aggregate quantities per gift_id from Booked table
    results = db.session.query(
        Booked.gift_id,
        func.sum(Booked.quantity)
    ).group_by(Booked.gift_id).all()

    # Step 2: Get gift names from GiftBooking table
    gift_names = {g.id: g.gift_name for g in GiftBooking.query.all()}

    # Step 3: Prepare labels and quantities
    labels = [gift_names.get(gift_id, f"Gift {gift_id}") for gift_id, _ in results]
    quantities = [qty for _, qty in results]
    zipped_data = list(zip(labels, quantities))

    # Step 4: Compute stats
    if quantities:
        max_quantity = max(quantities)
        max_index = quantities.index(max_quantity)
        max_gift = labels[max_index]

        min_quantity = min(quantities)
        min_index = quantities.index(min_quantity)
        min_gift = labels[min_index]

        total_quantity = sum(quantities)
        avg_quantity = round(total_quantity / len(quantities), 2)
    else:
        max_quantity = min_quantity = total_quantity = avg_quantity = 0
        max_gift = min_gift = "N/A"

    # Step 5: Pass everything to the template
    return render_template(
        'gift.html',
        labels=labels,
        quantities=quantities,
        zipped_data=zipped_data,
        total_quantity=total_quantity,
        avg_quantity=avg_quantity,
        max_quantity=max_quantity,
        min_quantity=min_quantity,
        max_gift=max_gift,
        min_gift=min_gift
    )

@app.route('/download_gift_pdf', methods=['POST'])
def download_gift_pdf():
    data = request.get_json()
    chart_data_url = data.get('chart')

    if chart_data_url.startswith('data:image/png;base64,'):
        chart_data_url = chart_data_url.replace('data:image/png;base64,', '')

    # Decode and load image
    image_bytes = base64.b64decode(chart_data_url)
    image = Image.open(io.BytesIO(image_bytes))

    # Convert image for compatibility
    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")

    # Save as JPEG temporarily
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_file:
        image.save(tmp_file, format='JPEG')
        temp_image_path = tmp_file.name

    # Create PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    # Title
    pdf.cell(200, 10, txt="Gift Booking Report", ln=True, align='C')

    # Timestamp
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pdf.set_font("Arial", size=10)
    pdf.cell(200, 10, txt=f"Generated on: {now}", ln=True, align='C')

    # Image
    pdf.image(temp_image_path, x=10, y=40, w=180)  # Y offset adjusted for the extra line

    # Finalize PDF
    pdf_output = io.BytesIO()
    pdf_bytes = pdf.output(dest='S').encode('latin1')
    pdf_output.write(pdf_bytes)
    pdf_output.seek(0)

    os.remove(temp_image_path)

    return send_file(pdf_output, mimetype='application/pdf', as_attachment=True, download_name='gift_report.pdf')

@app.route('/daily-booking')
def daily_booking():
    from datetime import datetime
    gift = request.args.get('gift')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    # Base query for gift
    query = db.session.query(
        func.date(Booked.datetime).label('date'),
        func.sum(Booked.quantity).label('total_quantity')
    ).filter(Booked.gift_name == gift)

    # Optional date filtering
    if start_date and end_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            query = query.filter(
                func.date(Booked.datetime) >= start.date(),
                func.date(Booked.datetime) <= end.date()
            )
        except ValueError:
            pass

    # Group by date and get results
    query = query.group_by(func.date(Booked.datetime)).order_by(func.date(Booked.datetime)).all()

    dates = [str(row.date) for row in query]
    quantities = [row.total_quantity for row in query]

    return render_template(
        'daily_booking.html',
        gift=gift,
        dates=dates,
        quantities=quantities,
        start_date=start_date,
        end_date=end_date
    )

@app.route('/stock')
def stock():
    from sqlalchemy import func

    results = db.session.query(
        ListStock.product_name,
        func.sum(ListStock.quantity)
    ).group_by(ListStock.product_name).all()

    labels = [row[0] for row in results]
    quantities = [row[1] for row in results]
    product_data = list(zip(labels, quantities))

    total_quantity = sum(quantities)
    avg_quantity = round(total_quantity / len(quantities), 2) if quantities else 0
    max_qty = max(quantities) if quantities else 0
    min_qty = min(quantities) if quantities else 0
    max_product_label = labels[quantities.index(max_qty)] if quantities else "N/A"
    min_product_label = labels[quantities.index(min_qty)] if quantities else "N/A"

    return render_template(
        'stock.html',   # <-- Now using the renamed template
        labels=labels,
        quantities=quantities,
        product_data=product_data,
        total_quantity=total_quantity,
        avg_quantity=avg_quantity,
        max_qty=max_qty,
        min_qty=min_qty,
        max_product_label=max_product_label,
        min_product_label=min_product_label
    )

@app.route('/stock/pdf', methods=['POST'])
def download_stock_pdf():
    data = request.get_json()
    chart_data_url = data.get('chart')

    if not chart_data_url:
        return {"error": "No chart data received"}, 400

    try:
        # Remove base64 header
        chart_data_url = chart_data_url.replace('data:image/png;base64,', '')
        image_bytes = base64.b64decode(chart_data_url)

        # Load image
        image = Image.open(io.BytesIO(image_bytes))
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")

        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_file:
            image.save(tmp_file, format="JPEG")
            image_path = tmp_file.name

        # Create PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "Stock Report", ln=True, align="C")
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 10, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align="C")
        pdf.ln(10)
        pdf.image(image_path, x=10, w=180)

        # Clean up
        os.remove(image_path)

        # Return PDF as downloadable file
        pdf_output = io.BytesIO()
        pdf_bytes = pdf.output(dest="S").encode("latin1")
        pdf_output.write(pdf_bytes)
        pdf_output.seek(0)

        return send_file(
            pdf_output,
            mimetype='application/pdf',
            as_attachment=True,
            download_name='stock_report.pdf'
        )

    except Exception as e:
        return {"error": str(e)}, 500
    
@app.route('/stock-daily')
def stock_daily():
    product = request.args.get('product')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    query = db.session.query(
        func.date(ListStock.checklist_datetime).label('date'),
        func.sum(ListStock.quantity).label('total_quantity')
    ).filter(ListStock.product_name == product)

    if start_date and end_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            query = query.filter(
                func.date(ListStock.checklist_datetime) >= start.date(),
                func.date(ListStock.checklist_datetime) <= end.date()
            )
        except ValueError:
            pass

    query = query.group_by(func.date(ListStock.checklist_datetime))\
                 .order_by(func.date(ListStock.checklist_datetime)).all()

    dates = [str(row.date) for row in query]
    quantities = [row.total_quantity for row in query]

    return render_template('stock_daily.html',
                           product=product,
                           dates=dates,
                           quantities=quantities,
                           start_date=start_date,
                           end_date=end_date)


@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

if __name__ == "__main__":
    print("Starting Flask app...")
    app.run(host="0.0.0.0", port=5002, debug=True)