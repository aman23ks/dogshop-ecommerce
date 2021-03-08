from flask import Flask, render_template, redirect, url_for, request, flash, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from forms import SigninForm, SignupForm, ContactFrom, CommentForm, AddDogForm
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from sqlalchemy.orm import relationship
from datetime import datetime
import smtplib
import stripe

app = Flask(__name__)
app.config["SECRET_KEY"] = "EVVBAVNVKNVKN"
app.config["STRIPE_PUBLIC_KEY"] = "pk_test_51IRWiNExRBiBD9IcW2kbeW5koqkTifz4PXi0rKY1IM0nQqxzJtnfyFzJ6KLn7voO4zAcZfaJyV1Mb7DUKJTRdedS00mcb4n2MS"
app.config["STRIPE_SECRET_KEY"] = "sk_test_51IRWiNExRBiBD9IcsCbJCCWoYDPK6QvKxDlBYNQcfwIUzITNh1xVD1ttFPY8w2klVt1JCHxGRaFMTaVLGmq7X4JI00ulDBn7d4"
stripe.api_key = app.config["STRIPE_SECRET_KEY"]

Bootstrap(app)
ckeditor = CKEditor(app)
now = datetime.now()
year = now.year

# Connect DB

app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///shop.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)

# Configure Table


class User(UserMixin, db.Model):
    _tablename_ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(100))
    dogs = relationship("Dog", back_populates="user")
    comments = relationship("Comment", back_populates="comment_user")


class Dog(db.Model):
    _tablename_ = "dogs"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = relationship("User", back_populates="dogs")
    name = db.Column(db.String(100))
    description = db.Column(db.String(100))
    img_url = db.Column(db.String(100))
    age = db.Column(db.String(100))
    breed = db.Column(db.String(100))
    price = db.Column(db.Integer)
    medication = db.Column(db.String(100))
    motivation = db.Column(db.String(100))
    comments = relationship("Comment", back_populates="parent_post")


class Comment(db.Model):
    _tablename_ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    dog_id = db.Column(db.Integer, db.ForeignKey("dog.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    parent_post = relationship("Dog", back_populates="comments")
    comment_user = relationship("User", back_populates="comments")
    text = db.Column(db.Text, nullable=False)


class Cart(db.Model):
    _tablename_ = "cart"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    dog_id = db.Column(db.Integer, db.ForeignKey("dog.id"))


db.create_all()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.id != 1:
            return abort(403)
        return f(*args, **kwargs)
    return decorated_function


def user_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.id == 1:
            return abort(403)
        return f(*args, **kwargs)
    return decorated_function


@app.route("/")
def home():
    return render_template("index.html", year=year)


@app.route('/signup', methods=["GET", "POST"])
def signup():
    form = SignupForm()
    if form.validate_on_submit():

        if User.query.filter_by(email=form.email.data).first():
            print(User.query.filter_by(email=form.email.data).first())
            # User already exists
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for('signin'))

        hash_and_salted_password = generate_password_hash(
            form.password.data,
            method='pbkdf2:sha256',
            salt_length=8
        )
        new_user = User(
            email=form.email.data,
            name=form.name.data,
            password=hash_and_salted_password,
        )
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for("home"))

    return render_template("signup.html", form=form, current_user=current_user, year=year)


@app.route('/signin', methods=["GET", "POST"])
def signin():
    form = SigninForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        user = User.query.filter_by(email=email).first()
        # Email doesn't exist or password incorrect.
        if not user:
            flash("That email does not exist, please try again.")
            return redirect(url_for('signin'))
        elif not check_password_hash(user.password, password):
            flash('Password incorrect, please try again.')
            return redirect(url_for('signin'))
        else:
            login_user(user)
            return redirect(url_for('home'))
    return render_template("signin.html", form=form, current_user=current_user, year=year)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('signin'))


@app.route("/contact", methods=["GET", "POST"])
def contact():
    form = ContactFrom()
    if form.validate_on_submit():
        name = request.form["name"]
        email = request.form["email"]
        comment = request.form["message"]
        message = f"Subject: You recieved a message from your Tindog Website!\n\n name: {name}\nemail: {email}\ncomment: {comment}"

        my_email = "aman23ks@yahoo.com"
        my_password = "dwowjkdytlfbhbvk"

        connection = smtplib.SMTP("smtp.mail.yahoo.com", port=587)
        connection.starttls()
        connection.login(user=my_email, password=my_password)
        connection.sendmail(from_addr=my_email,
                            to_addrs="aman23ks@gmail.com", msg=f"Subject:Message from your Tindog Website!\n\n{message}")
        connection.close()
        return redirect(url_for("home"))
    return render_template("contact.html", form=form, year=year)


@app.route("/about")
def about():
    return render_template("about.html", year=year)


@app.route("/explore")
def explore():
    dogs = Dog.query.all()
    return render_template("explore.html", year=year, dogs=dogs, current_user=current_user)


@app.route("/product/<int:id>", methods=["GET", "POST"])
def product(id):
    form = CommentForm()
    dog = Dog.query.get(id)
    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("You need to login or register to comment.")
            return redirect(url_for("signin"))
        new_comment = Comment(
            text=form.comment_text.data,
            comment_user=current_user,
            parent_post=dog
        )
        db.session.add(new_comment)
        db.session.commit()
    return render_template("product.html", form=form, year=year, dog=dog)


@app.route("/cart/<int:id>", methods=["GET", "POST"])
@user_only
def cart(id):
    if id == 0:
        list_of_dogs = []
        price = 0
        dog_items = Cart.query.filter_by(user_id=current_user.id).all()
        for dog in dog_items:
            dog_id_item = Dog.query.get(dog.dog_id)
            price += dog_id_item.price
            list_of_dogs.append(dog_id_item)
        return render_template("cart.html", year=year, list_of_dogs=list_of_dogs, price=price)
    else:
        dog = Dog.query.get(id)
        new_cart = Cart(
            user_id=current_user.id,
            dog_id=dog.id
        )
        db.session.add(new_cart)
        db.session.commit()

        list_of_dogs = []
        price = 0
        dog_items = Cart.query.filter_by(user_id=current_user.id).all()
        for dog in dog_items:
            dog_id_item = Dog.query.get(dog.dog_id)
            price += dog_id_item.price
            list_of_dogs.append(dog_id_item)
        return render_template("cart.html", year=year, list_of_dogs=list_of_dogs, price=price)
    return render_template("cart.html", year=year)


@app.route("/add", methods=["GET", "POST"])
@admin_only
def add():
    form = AddDogForm()
    if form.validate_on_submit():
        new_dog = Dog(
            name=form.name.data,
            description=form.description.data,
            img_url=form.img_url.data,
            age=form.age.data,
            breed=form.breed.data,
            price=form.price.data,
            medication=form.medication.data,
            motivation=form.motivation.data,
            user_id=1
        )
        db.session.add(new_dog)
        db.session.commit()
        return redirect(url_for('explore'))
    return render_template("add.html", year=year, form=form)


@app.route("/edit-dog/<int:id>", methods=["GET", "POST"])
@admin_only
def edit(id):
    dog = Dog.query.get(id)
    print(dog.id)
    edit_dog = AddDogForm(
        name=dog.name,
        description=dog.description,
        img_url=dog.img_url,
        age=dog.age,
        breed=dog.breed,
        price=dog.price,
        medication=dog.medication,
        motivation=dog.motivation,
    )
    if edit_dog.validate_on_submit():
        dog.name = edit_dog.name.data
        dog.description = edit_dog.description.data
        dog.img_url = edit_dog.img_url.data
        dog.age = edit_dog.age.data
        dog.breed = edit_dog.breed.data
        dog.price = edit_dog.price.data
        dog.medication = edit_dog.medication.data
        dog.motivation = edit_dog.motivation.data
        db.session.commit()
        return redirect(url_for('explore'))
    return render_template("add.html", form=edit_dog, year=year)


@app.route("/delete/<int:id>")
@admin_only
def delete(id):
    dog_to_delete = Dog.query.get(id)
    db.session.delete(dog_to_delete)
    db.session.commit()
    return redirect(url_for('explore'))


@app.route("/success")
def success():
    dogs_list = Cart.query.filter_by(user_id=current_user.id).all()
    for dogs in dogs_list:
        db.session.delete(dogs)
        db.session.commit()
    return render_template("success.html")


@app.route('/stripe_pay')
def stripe_pay():
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price': 'price_1IRXPUExRBiBD9Ich074UzOW',
            'quantity': 1,
        }],
        mode='payment',
        success_url=url_for('success', _external=True) +
        '?session_id={CHECKOUT_SESSION_ID}',
        cancel_url=url_for('home', _external=True),
    )
    return {
        'checkout_session_id': session['id'],
        'checkout_public_key': app.config['STRIPE_PUBLIC_KEY']
    }


@app.route('/stripe_webhook', methods=['GET', 'POST'])
def stripe_webhook():
    print('WEBHOOK CALLED')

    if request.content_length > 1024 * 1024:
        print('REQUEST TOO BIG')
        abort(400)
    payload = request.get_data()
    sig_header = request.environ.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = 'whsec_8l1LX3LVna2MNKIWgKwWhSb4grLLCard'
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        # Invalid payload
        print('INVALID PAYLOAD')
        return {}, 400
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        print('INVALID SIGNATURE')
        return {}, 400

    # Handle the checkout.session.completed event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        print(session)
        line_items = stripe.checkout.Session.list_line_items(
            session['id'], limit=1)
        print(line_items['data'][0]['description'])


if __name__ == "__main__":
    app.run(debug=True)
