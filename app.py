from flask import Flask, redirect, url_for, session, render_template, request, abort
from flask_sqlalchemy import SQLAlchemy, Model
from sqlalchemy.ext.declarative import declared_attr
import yahoo_fin.stock_info as si
import hashlib

def get_live_price(ticker):
    return si.get_live_price(ticker)

app = Flask(__name__)
app.secret_key = "jeanpaullovesmoscow"
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///./data.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20))
    password = db.Column(db.String(64))

    accounts = db.relationship("Account", backref="user")

class Account(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    balance = db.Column(db.Float)
    commission = db.Column(db.Float)
    initial_balance = db.Column(db.Integer)

    positions = db.relationship("Position", backref="account")

    def get_worth(self):
        return self.balance + sum([
        pos.get_value()*(1-self.commission) for pos in self.positions
        ])

    def get_profits(self):
        return self.get_worth() - self.initial_balance

class Position(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey("account.id"))
    ticker = db.Column(db.String(4))
    amount = db.Column(db.Integer)
    bought_for = db.Column(db.Float)

    def get_value(self):
        return self.amount*get_live_price(self.ticker)

@app.route("/")
@app.route("/index")
def index():
    if "user_id" not in session:
        return render_template("index.html")
    else:
        return render_template("cabinet.html", user=User.query.get(session['user_id']))

@app.route("/login", methods=["POST", "GET"])
def login():
    if "user_id" in session:
        return redirect(url_for("index"))
    if request.method == 'POST':
        pwdencoded = request.form["password"].encode("utf-8")
        hexpassword = hashlib.sha256(pwdencoded).hexdigest()
        for user in User.query.all():
            if user.username == request.form["name"] and user.password == hexpassword:
                session['user_id'] = user.id
                session['username'] = user.username
                return redirect(url_for('index'))
        return render_template("login.html", warning="Wrong username/password!")
    return render_template("login.html")

@app.route("/logout")
def logout():
    if "user_id" in session:
        session.pop("user_id")
    return redirect(url_for("login"))

@app.route("/register", methods=["POST", "GET"])
def register():
    if "user_id" in session:
        return redirect(url_for("index"))
    if request.method == 'POST':
        username, password = request.form["name"], request.form["password"]
        if username in [user.username for user in User.query.all()]:
            return render_template("register.html", warning="Such user exists!")
        if len(password) < 4:
            return render_template("register.html", warning="Password is too short")
        newborn = User(username=username, password=hashlib.sha256(password.encode("utf-8")).hexdigest())
        db.session.add(newborn)
        db.session.commit()
        session["user_id"] = newborn.id
        session["username"] = newborn.username
        return redirect(url_for("index"))
    return render_template("register.html")

@app.route("/addaccount", methods=["POST", "GET"])
def addaccount():
    if request.method == 'POST':
        balance, commission = request.form["balance"], request.form["commission"]
        try:
            balance = int(balance)
            if balance <=0:
                return render_template("addaccount.html", warning="Balance should be positive, you know...")
        except:
            return render_template("addaccount.html", warning="Balance must be an integer")
        try:
            commission = float(commission)
            if commission < 0 or commission > 1:
                return render_template("addaccount.html", warning="Commission should be between 0 and 1 ")
        except:
            return render_template("addaccount.html", warning="Commission should be a float between 0 and 1")
        new_account = Account(commission=commission, balance=balance, initial_balance=balance, user=User.query.get(session["user_id"]))
        db.session.add(new_account)
        db.session.commit()
        return redirect(url_for("index"))
    return render_template("addaccount.html")

@app.route("/deleteaccount", methods=["POST"])
def deleteaccount():
    deleted = Account.query.get(request.form["account_id"])
    db.session.delete(deleted)
    db.session.commit()
    return redirect(url_for("index"))

@app.route('/account/<id>')
def account(id, **kwargs):
    try:
        if Account.query.get(id).user_id != session["user_id"]:
            return abort(403)
    except:
        return abort(404)
    account = Account.query.get(id)
    if "warning" in kwargs:
        warning = kwargs['warning']
    else:
        warning = None
    return render_template("positions.html", account=account, warning = warning)

@app.route('/account/<id>/addposition', methods=["POST", "GET"])
def addposition(id):
    try:
        if Account.query.get(id).user_id != session["user_id"]:
            return abort(403)
    except:
        return abort(404)
    if request.method == 'POST':
        ticker, amount = request.form['ticker'], request.form['amount']
        try:
            amount = int(amount)
        except:
            return render_template('addposition.html',
            warning='Amount should be an integer')
        if si.get_quote_data(ticker)['marketState'] == 'CLOSED':
            return render_template('addposition.html',
            warning = "Market is CLOSED")
        try:
            live_price = get_live_price(ticker)
        except:
            return render_template('addposition.html',
            warning='Couldnt get live price')
        account = Account.query.get(id)
        total = amount*live_price*(1+account.commission)
        if total > account.balance:
            return render_template("addposition.html",
            warning='You can\'t afford that')
        account.balance -= total
        account.positions.append(Position(ticker=ticker, amount=amount, bought_for=total))
        db.session.add(account)
        db.session.commit()
        return redirect(url_for('account', id=id))
    return render_template('addposition.html')

@app.route('/closeposition', methods=["POST"])
def closeposition():
    closed = Position.query.get(request.form["position_id"])
    account = Account.query.get(closed.account_id)
    if si.get_quote_data(closed.ticker)['marketState'] == 'CLOSED':
        return render_template('positions.html', account=account, warning = "Market is CLOSED")
    account.balance += closed.get_value()*(1-account.commission)
    db.session.delete(closed)
    db.session.commit()
    return redirect(url_for("account", id=account.id))
