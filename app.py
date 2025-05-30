from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import paypalrestsdk
import uuid
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import paypalrestsdk
import uuid
import random
import os


app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///freelance_platform.db'
db = SQLAlchemy(app)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'enyongesa462gmail@gmail.com'  # Replace
app.config['MAIL_PASSWORD'] = 'simiyu@30'  # Replace with Gmail App Password
app.config['MAIL_DEFAULT_SENDER'] = 'agritrue13@gmail.com'
mail = Mail(app)

paypalrestsdk.configure({
    "mode": "sandbox",
    "client_id": "AXNJ7bXz8J_bCu64q_jDOYrih613QY63uPwjs43ziQrIi2sMaondnfhrJQtFCFH_y521zlgvXYhxmkj4",
    "client_secret": "EGSKKlrIvnxknjLGhjB7XUncwx7ALUd9W1MoVk2tW5Hw8SZ8NuB_RGteEONDHx_sciOrZPOmDGwO7byB"
})
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    budget = db.Column(db.Integer, nullable=False)
    deadline = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    employer_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'))
    freelancer_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    cover_letter = db.Column(db.Text, nullable=True)
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)

class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=False)
    freelancer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    if user.role == 'employer':
        jobs = Job.query.filter_by(employer_id=user.id).all()
        return render_template('employer_dashboard.html', user=user, jobs=jobs)
    else:
        jobs = Job.query.all()
        
        return render_template('freelancer_dashboard.html', user=user, jobs=jobs)

@app.route('/post_job', methods=['GET', 'POST'])
def post_job():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        session['job_data'] = {
            'title': request.form['title'],
            'description': request.form['description'],
            'budget': int(request.form['budget']),
            'deadline': request.form['deadline'],
        }
        return redirect(url_for('pay_job_fee'))
    return render_template('post_job.html')

@app.route('/pay_job_fee', methods=['GET'])
def pay_job_fee():
    job_data = session.get('job_data')
    if not job_data:
        return redirect(url_for('dashboard'))  # fallback if no data

    fee = round(job_data['budget'] * 0.4, 2)
    return render_template('pay_job_fee.html', 
        title=job_data['title'], 
        description=job_data['description'],
        budget=job_data['budget'],
        amount=fee
    )
@app.route('/payment-success')
def payment_success():
    return '''
    <html>
    <head>
      <title>Payment Successful</title>
      <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body class="bg-light text-center py-5">
      <h2 class="mb-4">✅ Payment Successful!</h2>
      <p>Thank you for your payment. You may now proceed to submit your work.</p>

      <div class="text-center mt-4">
        <button onclick="document.getElementById('code-entry').style.display='block'" class="btn btn-primary">
          Submit Work
        </button>
      </div>

      <div id="code-entry" style="display:none;" class="mt-3 text-center">
        <input type="text" id="codeInput" class="form-control w-25 mx-auto mb-2" placeholder="Enter your code">
        <button onclick="verifyCode()" class="btn btn-success">Continue</button>
        <p id="errorMsg" class="text-danger mt-2" style="display:none;">Invalid code. Please try again.</p>
      </div>

      <script>
        function verifyCode() {
          const code = document.getElementById('codeInput').value;
          if (code === '4510') {
            window.location.href = '/submit-work';
          } else {
            document.getElementById('errorMsg').style.display = 'block';
          }
        }
      </script>
    </body>
    </html>
    '''


@app.route('/complete-payment', methods=['POST'])
def complete_payment():
    title = request.form.get('title')
    description = request.form.get('description')
    budget = request.form.get('budget')
    amount = request.form.get('amount')

    if not all([title, description, budget, amount]):
        return "Missing job data", 400

    # Create PayPal payment
    payment = paypalrestsdk.Payment({
        "intent": "sale",
        "payer": {
            "payment_method": "paypal"
        },
        "redirect_urls": {
            "return_url": url_for('payment_success', _external=True),
            "cancel_url": url_for('dashboard', _external=True)
        },
        "transactions": [{
            "amount": {
                "total": f"{float(amount):.2f}",
                "currency": "USD"
            },
            "description": f"Job Posting: {title}"
        }]
    })

    if payment.create():
        session['payment_id'] = payment.id
        # Payment created successfully
        for link in payment.links:
            if link.rel == "approval_url":
                return redirect(str(link.href))
        return "No approval URL found", 500
    else:
        print(payment.error)
        return "Payment setup failed", 500

@app.route('/execute_application_payment')
def execute_application_payment():
    payment_id = session.get('payment_id')
    payer_id = request.args.get('PayerID')
    if not payment_id or not payer_id:
        return "Missing payment information", 400

    payment = paypalrestsdk.Payment.find(payment_id)

    if payment.execute({"payer_id": payer_id}):
        data = session.pop('application_data', None)
        session.pop('payment_id', None)
        if not data:
            return "Session expired", 400

        application = Application(
            job_id=data['job_id'],
            freelancer_id=data['freelancer_id'],
            cover_letter=data['cover_letter']
        )
        db.session.add(application)
        db.session.commit()
        return "<h3>Payment successful! Application submitted.</h3><a href='/dashboard'>Back to Dashboard</a>"
    else:
        return "Payment failed", 400


# Application Flow
@app.route('/apply/<int:job_id>', methods=['GET', 'POST'])
def apply(job_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    job = Job.query.get_or_404(job_id)
    if request.method == 'POST':
        session['application_data'] = {
            'job_id': job.id,
            'freelancer_id': session['user_id'],
            'cover_letter': request.form['cover_letter'],
        }
    return redirect(url_for('pay_application_fee'))
    return render_template('apply.html', job=job)


@app.route('/pay_application_fee')
def pay_application_fee():
    application_data = session.get('application_data')
    if not application_data:
        return redirect(url_for('dashboard'))

    amount = 10.00  # Application fee
    payment = paypalrestsdk.Payment({
        "intent": "sale",
        "payer": {
            "payment_method": "paypal"
        },
        "redirect_urls": {
            "return_url": url_for('execute_application_payment', _external=True),  # ✅ FIXED
            "cancel_url": url_for('dashboard', _external=True)
        },
        "transactions": [{
            "amount": {
                "total": f"{amount:.2f}",
                "currency": "USD"
            },
            "description": "Application Fee"
        }]
    })

    if payment.create():
        session['payment_id'] = payment.id  # ✅ Make sure payment_id is stored
        for link in payment.links:
            if link.rel == "approval_url":
                return redirect(str(link.href))
        return "No approval URL found", 500
    else:
        print(payment.error)
        return "An error occurred during payment setup", 500
from flask import flash

@app.route('/submit-work', methods=['POST'])
def submit_work():
    if 'user_id' not in session or session.get('role') != 'freelancer':
        return redirect(url_for('login'))

    file = request.files['file']
    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Save submission in DB (optional)
        submission = Submission(
            job_id=request.form.get('job_id', 0),
            freelancer_id=session['user_id'],
            file_path=filename,
            notes=request.form.get('notes', '')
        )
        db.session.add(submission)
        db.session.commit()

        flash("✅ Work submitted successfully! 🎉 Thanks for your submission. We'll review it shortly.")
        return redirect(url_for('freelancer_dashboard'))

    flash("⚠️ File upload failed. Please try again.")
    return redirect(url_for('freelancer_dashboard'))

@app.route('/job/<int:job_id>/applicants')
def view_applicants(job_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    job = Job.query.get_or_404(job_id)
    if job.employer_id != session['user_id']:
        return "Unauthorized", 403
    applications = Application.query.filter_by(job_id=job.id).all()
    freelancers = [
        {'application': app, 'freelancer': User.query.get(app.freelancer_id)}
        for app in applications
    ]
    return render_template('view_applicants.html', job=job, freelancers=freelancers)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        role = request.form['role']
        if password != confirm_password:
            return "Passwords do not match!", 400
        if User.query.filter_by(email=email).first():
            return "Email already registered!", 409
        hashed = generate_password_hash(password)
        db.session.add(User(email=email, password=hashed, role=role))
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email']).first()
        if user and check_password_hash(user.password, request.form['password']):
            session['user_id'] = user.id
            return redirect(url_for('dashboard'))
        else:
            return "Invalid credentials", 401
    return render_template('login.html')


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
