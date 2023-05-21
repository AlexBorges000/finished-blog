import os
from functools import wraps
from flask import Flask, render_template, redirect, url_for, flash, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from sqlalchemy import ForeignKey
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RequisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ["SECRET_KEY"]
ckeditor = CKEditor(app)
Bootstrap(app)


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
gravatar = Gravatar(app)


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    author_id = db.Column(db.Integer, ForeignKey("user.id"))
    author = relationship("User", back_populates="posts")


class User(UserMixin, db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))
    posts = relationship("BlogPost", back_populates="author")
    user_comment = relationship("Comment", back_populates="author")


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    comment = db.Column(db.String(250), nullable=False)
    user_id = db.Column(db.Integer, ForeignKey("user.id"))
    author = relationship("User", back_populates="user_comment")


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def admin_only(f):
    @wraps(f)
    def wrapped_func(*args, **kwargs):
        if current_user.id == 1:
            return f(*args, **kwargs)
        else:
            abort(403)

    return wrapped_func


@app.route('/')
def get_all_posts():
    db.create_all()
    print(current_user)
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts)


@app.route('/register', methods=["GET", "POST"])
def register():
    reg_form = RequisterForm()
    duplicated = User.query.filter_by(email=reg_form.email.data).first()
    if duplicated:
        flash("Email already registered")
        return redirect(url_for("login"))
    if reg_form.validate_on_submit():
        new_user = User(
            email=reg_form.email.data,
            password=generate_password_hash(
                password=reg_form.password.data,
                method="pbkdf2:sha256",
                salt_length=8),
            name=reg_form.name.data
        )
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for("get_all_posts"))
    return render_template("register.html", form=reg_form)


@app.route('/login', methods=["GET", "POST"])
def login():
    enter_form = LoginForm()
    user = User.query.filter_by(email=enter_form.email.data).first()
    password = enter_form.password.data
    if user == []:
        flash("Email incorrect!")
        return redirect(url_for("login"))
    if enter_form.validate_on_submit():
        if check_password_hash(pwhash=user.password, password=password):
            login_user(user)
            return redirect(url_for("get_all_posts"))
        else:
            flash("Wrong password")
    return render_template("login.html", form=enter_form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=["POST", "GET"])
def show_post(post_id):
    requested_post = BlogPost.query.get(post_id)
    comments = Comment.query.all()
    form = CommentForm()
    if form.validate_on_submit():

        if current_user.is_authenticated:
            new_comment = Comment(
                user_id=current_user.id,
                comment=form.comment.data
            )
            db.session.add(new_comment)
            db.session.commit()
        else:
            flash("You need to  login ")
            return redirect(url_for("login"))

    return render_template("post.html", post=requested_post, form=form, comments=comments)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/new-post", methods=["POST", "GET"])
@login_required
@admin_only
def add_new_post():
    form = CreatePostForm()
    user = db.session.query(User).filter_by(id=current_user.id).first()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


@app.route("/edit-post/<int:post_id>")
@admin_only
@login_required
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form)


@app.route("/delete/<int:post_id>")
@admin_only
@login_required
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
