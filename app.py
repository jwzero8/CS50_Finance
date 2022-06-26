import os
import datetime
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Note: If status code 400, one solution is to run on different chrome user
@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    # My thought: It would be the best to mention trade type in the database, AKA buy or sell
    # My thought: Just update the database, knows the importance of a well-designed database
    # My thought: First get user_id, then db.execute from the database of trade to show what the user did
    # My thought: The database should be based on BUY less any SELL.

    # Note: Fun fact: if we only get this line of code, website will be down to 502 bad request
    user_id = session["user_id"]
    # b = "BUY"
    # s = "SELL"
    # Note: SQL >> SELECT xxx AS yyy
    stocks = db.execute("SELECT symbol, SUM(share) AS shares, price FROM trade WHERE user_id = ? GROUP BY symbol, transaction_type", user_id)
    # b_stocks = db.execute("SELECT symbol, SUM(share) AS shares, price FROM trade WHERE user_id = ?, transaction_type = ? GROUP BY symbol, transaction_type", user_id, b)
    # s_stocks = db.execute("SELECT symbol, SUM(share) AS shares, price FROM trade WHERE user_id = ?, transaction_type = ? GROUP BY symbol, transaction_type", user_id, s)


    cash_db = db.execute("SELECT cash FROM users WHERE id = ?", user_id)
    cash = cash_db[0]["cash"]
    asset = cash

    for stock in stocks:
        asset = cash + stock["price"] * stock["shares"]

    # Note: My personal touch >> One key sell ALL
    # Note: My reflection: Sadly, there is a flaw in this program that I only shows the cost but not the current price
    # Note: *** stock = stocks, stock is the name passed into HTML while stocks is the variable declared here
    return render_template("index.html", cash = cash, stocks = stocks, asset = asset)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "GET":
        return render_template("buy.html")
    else:
        request.method == "POST"
        symbol = request.form.get("symbol")
        shares = int(request.form.get("shares"))
        if not symbol or not shares:
            return apology("Symbol and no. of share are needed!")

        stock = lookup(symbol.upper())

        if stock == None:
            return apology("Stock does not appear in our database!")

        if shares < 0:
            return apology ("No. of share has to be positive to buy a stock.")

        turnover = shares * stock["price"]

        user_id = session["user_id"]

        # Note:  "?" can refer to things in SQL
        user_cash = db.execute("SELECT cash FROM users WHERE id = ?", user_id)
        cash = user_cash[0]["cash"]

        if turnover > cash:
            return apology("Sorry man, you do not have enough cash.")

        updated_cash = cash - turnover

        # Note: to use datetime function, you need to import the library datetime
        date = datetime.datetime.now()
        # Note: Update cash after transaction
        db.execute("UPDATE users SET cash = ? WHERE id = ?", updated_cash, user_id)
        db.execute("INSERT INTO trade (user_id, date, symbol, share, price, turnover, transaction_type) VALUES (?, ?, ?, ?, ?, ?, ?)", user_id, date, stock["symbol"], shares, stock["price"], turnover, "BUY")
        # print("Hello to the {} {}".format(var2,var1))
        flash("Bought {} share(s) of {} on {}!!".format(shares, symbol, date))
        # {shares} share(s) of {symbol} on {date}!
        return redirect("/")

@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    user_id = session["user_id"]

    # Note: SQL >> SELECT xxx AS yyy

    # Note: **Solve the floating point issue coz 55 will be 55.00001 in HTML
    trade_db = db.execute("SELECT symbol, share, price, date, ROUND(turnover, 2) AS turnover, transaction_type FROM trade WHERE user_id = ? GROUP BY symbol, transaction_type ORDER BY date DESC", user_id)
    cash_db = db.execute("SELECT cash FROM users WHERE id = ?", user_id)
    cash = cash_db[0]["cash"]

    # Note: My personal touch >> One key sell ALL
    # Note: My reflection: Sadly, there is a flaw in this program that I only shows the cost but not the current price

    return render_template("history.html", cash = cash, trade_db = trade_db)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        symbol = request.form.get("symbol")

        if not symbol:
            return apology("Please enter your symbol!")

        stock = lookup(symbol.upper())

        if stock == None:
            return apology("Stock does not appear in our database!")

        else:
            return render_template("quoted.html", name = stock["name"], price = stock["price"], symbol = stock["symbol"])

    else:
        request.method == "GET"
        return render_template("quote.html")



@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "GET":
        return render_template("register.html")
    else:
        request.method == "POST"
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        # Note: For CSS stuff: # >> id, . >> class
        # Note: if something does not exist we can just use if not xxx
        if not username or not password or not confirmation:
            return apology("Username, password and confirmation are ALL needed to create an account!")

        if password != confirmation:
            return apology("Passwords do not match!")

        hash_pw = generate_password_hash(password)

        # Note: INSERT INTO follows by TABLE name not database name
        # Note: Try / Except use in Python
        try:
            new_username = db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", username, hash_pw)

        except:
            return apology("Username already used!")

        # Note: *** This is very important. You need this to let the computer remember the one logging in.
        session["user_id"] = new_username
        return redirect("/")



@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "GET":
        return render_template("sell.html")
    else:
        request.method == "POST"
        symbol = request.form.get("symbol")
        shares = int(request.form.get("shares"))
        if not symbol or not shares:
            return apology("Symbol and no. of share are needed!")

        stock = lookup(symbol.upper())

        if stock == None:
            return apology("Stock does not appear in our database!")

        # if shares < 0:
        #    return apology ("No. of share has to be positive to sell a stock. No short selling!")

        user_id = session["user_id"]

        # Failed:share_b for number of stocks bought, _s for sold which is for calculation of stocks users have
        # b = "BUY"

        # s = "SELL"
        # share_b = db.execute("SELECT SUM(share) AS share FROM trade WHERE user_id = ? AND transaction_type = ? GROUP BY symbol = ?", user_id, b, symbol)

        # share_s = db.execute("SELECT SUM(share) AS share FROM trade WHERE user_id = ? AND transaction_type = ? GROUP BY symbol = ?", user_id, s, symbol)



        # Failed! attempt! if share_b - share_s < shares:
        #    return apology ("No. of share you want to sell is more than what you have!")



        # ME: todo>> if user do not has that many shares >> return apology
        # ME: todo>> update cash + transaction_type = SELL
        # ME: todo>> fix the issue of cost price and current price

        turnover = shares * stock["price"]

        # Note:  "?" can refer to things in SQL
        user_cash = db.execute("SELECT cash FROM users WHERE id = ?", user_id)
        cash = user_cash[0]["cash"]

        user_share = db.execute("SELECT SUM(share) AS share FROM trade WHERE user_id = ? AND symbol = ? GROUP BY symbol", user_id, symbol)

        user_share_db = user_share[0]["share"]

        if shares > user_share_db:
            return apology("Number of shares you have is not enough!")

        updated_cash = cash + turnover

        # Note: to use datetime function, you need to import the library datetime
        date = datetime.datetime.now()
        # Note: Update cash after transaction
        db.execute("UPDATE users SET cash = ? WHERE id = ?", updated_cash, user_id)
        db.execute("INSERT INTO trade (user_id, date, symbol, share, price, turnover, transaction_type) VALUES (?, ?, ?, ?, ?, ?, ?)", user_id, date, stock["symbol"], shares, stock["price"], turnover, "SELL")
        # print("Hello to the {} {}".format(var2,var1))
        flash("Sold {} share(s) of {} on {}!!".format(shares, symbol, date))
        # {shares} share(s) of {symbol} on {date}!
        return redirect("/")


@app.route("/allsell", methods=["GET", "POST"])
@login_required
def allsell():
    """Sell ALL shares of stock"""
    if request.method == "GET":
        return render_template("sell.html")
    else:
        request.method == "POST"


        user_id = session["user_id"]

        reset = 10000

        user_cash = db.execute("UPDATE users SET cash = ? WHERE id = ?", reset, user_id)

        # Note: to use datetime function, you need to import the library datetime
        date = datetime.datetime.now()

        db.execute("DELETE FROM trade WHERE user_id = ?", user_id)


        flash("Sold ALL stock(s) on {}!! ALL transaction history GONE!! You principal is reset to USD 10000 :D ".format(date))

        return render_template("GG.html")
