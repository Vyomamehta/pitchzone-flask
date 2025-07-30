import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
import yfinance as yf
import pandas as pd
import mplfinance as mpf

# Initialize Flask app
app = Flask(__name__)
app.secret_key = "supersecretkey"

# Configure SQLite database with a new database name
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///new_data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

class Pitch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    investment_needed = db.Column(db.String(50), nullable=False)

class Investment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    investor_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    pitch_id = db.Column(db.Integer, db.ForeignKey('pitch.id'), nullable=False)
    amount = db.Column(db.String(50), nullable=False)

# Middleware to restrict access to certain routes
def login_required(func):
    def wrapper(*args, **kwargs):
        if "user" not in session:
            flash("You need to log in first.")
            return redirect(url_for("login"))
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper

# Fetch stock data from Yahoo Finance
def fetch_stock_data(stock_ticker, start_date, end_date):
    try:
        data = yf.download(stock_ticker, start=start_date, end=end_date)
        return data
    except Exception as e:
        return pd.DataFrame()

# Clean the stock data
def clean_data(data):
    try:
        data.columns = data.columns.get_level_values(0)
        required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        data = data.dropna(subset=required_columns)
        return data
    except Exception as e:
        return pd.DataFrame()

# Plot the candlestick chart and save as image
def plot_candlestick(data, stock_ticker):
    try:
        filename = f"static/charts/{stock_ticker}_candlestick_chart.png"
        mpf.plot(data, type='candle', volume=True, title=f"{stock_ticker} Candlestick Chart", savefig=filename)
        return filename
    except Exception as e:
        return None

# Home route
@app.route("/")
def home():
    if "user" in session:
        return render_template("home.html", username=session["user"])
    return redirect(url_for("login"))

# Login route
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session["user"] = username
            flash("Login successful!")
            return redirect(url_for("home"))
        else:
            flash("Invalid username or password.")
    return render_template("login.html")

# Register route
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]
        if password != confirm_password:
            flash("Passwords do not match.")
        elif User.query.filter_by(username=username).first():
            flash("Username already exists.")
        else:
            new_user = User(username=username, password=password)
            db.session.add(new_user)
            db.session.commit()
            flash("Registration successful! Please log in.")
            return redirect(url_for("login"))
    return render_template("register.html")

# Pitch Zone Route
@app.route("/pitch_zone", methods=["GET", "POST"])
@login_required
def pitch_zone():
    if request.method == "POST":
        pitch_title = request.form["pitch_title"]
        pitch_description = request.form["pitch_description"]
        investment_money = request.form["investment_money"]

        new_pitch = Pitch(title=pitch_title, description=pitch_description, investment_needed=investment_money)
        db.session.add(new_pitch)
        db.session.commit()
        flash("Your pitch idea has been submitted successfully!")
        return redirect(url_for("pitch_zone"))

    pitches = Pitch.query.all()
    return render_template("pitch_zone.html", pitch_ideas=pitches)

# Investor Zone Route
@app.route("/investor_zone", methods=["GET", "POST"])
@login_required
def investor_zone():
    if request.method == "POST":
        investor_name = request.form["investor_name"]
        email = request.form["email"]
        investment_amount = request.form["investment_amount"]

        # Here, no pitch_id is required, we just show a success message
        new_investment = Investment(
            investor_name=investor_name,
            email=email,
            pitch_id=1,  # Placeholder pitch ID; adjust based on actual use case
            amount=investment_amount
        )
        db.session.add(new_investment)
        db.session.commit()
        flash("Your investment has been recorded successfully!")
        return redirect(url_for("investor_zone"))

    pitches = Pitch.query.all()
    investments = Investment.query.all()
    return render_template("investor_zone.html", pitch_ideas=pitches, investments=investments)

# Stock Market Route
@app.route("/stock_market", methods=["GET", "POST"])
@login_required
def stock_market():
    if request.method == "POST":
        stock_ticker = request.form["stock_ticker"].upper()
        start_date = "2023-01-01"
        end_date = "2024-12-01"

        data = fetch_stock_data(stock_ticker, start_date, end_date)
        if data.empty:
            return render_template("stock_market.html", error="No data found for the ticker provided.")
        
        data = clean_data(data)
        if data.empty:
            return render_template("stock_market.html", error="No valid data available after cleaning.")
        
        img_filename = plot_candlestick(data, stock_ticker)
        if img_filename:
            return render_template("stock_market.html", stock_image=img_filename)
        else:
            return render_template("stock_market.html", error="Error generating chart.")
    
    return render_template("stock_market.html")

# Logout route
@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("You have been logged out.")
    return redirect(url_for("login"))

if __name__ == "__main__":
    if not os.path.exists("new_data.db"):
        with app.app_context():
            db.create_all()
            print("Database initialized.")
    app.run(debug=True)








