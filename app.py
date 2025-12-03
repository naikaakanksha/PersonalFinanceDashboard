from flask import Flask, render_template, request, redirect, session, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from collections import defaultdict

app = Flask(__name__)
app.secret_key = "your_secret_key"

# ===================== DATABASE =====================
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///finance.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# ===================== MODELS =====================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type = db.Column(db.String(20), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    details = db.Column(db.JSON, nullable=False)

# ===================== ROUTES =====================
@app.route("/")
def index():
    return render_template("index.html")

# ---------- REGISTER ----------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        fullname = request.form.get("fullname")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if password != confirm_password:
            flash("Passwords do not match!", "danger")
            return redirect(url_for("register"))

        if User.query.filter_by(email=email).first():
            flash("Email already registered!", "danger")
            return redirect(url_for("register"))

        hashed_password = generate_password_hash(password)
        new_user = User(username=fullname, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful! Please login.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")

# ---------- LOGIN ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            session["username"] = user.username
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid credentials", "danger")
            return redirect(url_for("login"))

    return render_template("login.html")

# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

# ---------- ADD TRANSACTION ----------
@app.route("/add_transaction", methods=["GET", "POST"])
def add_transaction():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        t_type = request.form.get("type")
        categories = request.form.getlist("category")
        amounts = request.form.getlist("amount")

        details = {}
        for cat, amt in zip(categories, amounts):
            if cat.strip() and amt.strip():
                try:
                    details[cat] = float(amt)
                except ValueError:
                    flash("Invalid amount entered!", "danger")
                    return redirect(url_for("add_transaction"))

        if not details:
            flash("Please enter at least one category with amount.", "warning")
            return redirect(url_for("add_transaction"))

        new_transaction = Transaction(
            user_id=session["user_id"],
            type=t_type,
            details=details
        )
        db.session.add(new_transaction)
        db.session.commit()

        flash("Transaction added successfully!", "success")
        return redirect(url_for("dashboard"))

    return render_template("add_transaction.html")

# ---------- DASHBOARD ----------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    transactions = Transaction.query.filter_by(user_id=session["user_id"]).order_by(Transaction.date).all()

    total_income, total_expense = 0, 0
    category_income = defaultdict(float)
    category_expense = defaultdict(float)
    monthly_income = defaultdict(float)
    monthly_expense = defaultdict(float)

    dates_sorted = []
    balance_values = []
    cumulative_balance = 0

    for t in transactions:
        amount_sum = sum(t.details.values())
        month = t.date.strftime("%Y-%m")

        if t.type == "Income":
            total_income += amount_sum
            for cat, amt in t.details.items():
                category_income[cat] += amt
            monthly_income[month] += amount_sum
            cumulative_balance += amount_sum

        elif t.type == "Expense":
            total_expense += amount_sum
            for cat, amt in t.details.items():
                category_expense[cat] += amt
            monthly_expense[month] += amount_sum
            cumulative_balance -= amount_sum

        dates_sorted.append(t.date.strftime("%Y-%m-%d"))
        balance_values.append(cumulative_balance)

    months = sorted(set(list(monthly_income.keys()) + list(monthly_expense.keys())))
    monthly_income_list = [monthly_income.get(m, 0) for m in months]
    monthly_expense_list = [monthly_expense.get(m, 0) for m in months]

    remaining_balance = total_income - total_expense

    return render_template(
        "dashboard.html",
        total_income=total_income,
        total_expense=total_expense,
        remaining_balance=remaining_balance,
        transactions=transactions,
        category_income=dict(category_income),
        category_expense=dict(category_expense),
        months=months,
        monthly_income=monthly_income_list,
        monthly_expense=monthly_expense_list,
        dates_sorted=dates_sorted,
        balance_values=balance_values
    )

# ===================== MAIN =====================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
