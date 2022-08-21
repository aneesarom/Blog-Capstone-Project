from flask import Flask, render_template, redirect, url_for, flash, abort, jsonify, send_from_directory
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, URL
from flask_ckeditor import CKEditor, CKEditorField
from datetime import date
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from sqlalchemy.orm import relationship
from flask_gravatar import Gravatar
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY")
ckeditor = CKEditor(app)
bootstrap = Bootstrap(app)
gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL", "sqlite:///user.db")
app.config['SQLALCHEMY_BINDS'] = {
    'blog_key': os.environ.get("DATABASE_URL", "sqlite:///blog.db"),
    'comment_key': os.environ.get("DATABASE_URL", "sqlite:///comment.db")

}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def get_user(ident):
    # get id from session, then retrieve user object from database
    return User.query.get(int(ident))


##CONFIGURE TABLES

class BlogPost(db.Model):
    __bind_key__ = 'blog_key'
    __tablename__ = 'blog_table'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    # to use foreign column (parent database column) in child database. Refer below code
    author_id = db.Column(db.Integer, db.ForeignKey("user_table.id"))
    blog_comment = db.relationship("Comment", backref="user_comment",  lazy="dynamic")
    # primaryjoin = "Comment.blog_id == BlogPost.id"


class User(db.Model, UserMixin):
    __tablename__ = 'user_table'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)
    name = db.Column(db.String(250), nullable=False)
    # let other database to use this database column (parent database column) need to create relationship. Refer
    # below code
    post = db.relationship("BlogPost", backref="author")
    user_comment = db.relationship("Comment", backref="commenter")
    # backref name is used to get parent database column values


class Comment(db.Model, UserMixin):
    __bind_key__ = 'comment_key'
    __tablename__ = 'comment_table'
    id = db.Column(db.Integer, primary_key=True)
    comment = db.Column(db.String(250), nullable=False)
    blog_id = db.Column(db.Integer, db.ForeignKey("blog_table.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("user_table.id"))


# db.create_all()
db.session.commit()


def admin_only(function):
    def wrapper_function(*args, **kwargs):
        if current_user.get_id() == "1" or current_user.get_id() == "2":
            return function(*args, **kwargs)
        # else:
        #     abort(403, description="Resource not found")

    return wrapper_function


@app.errorhandler(403)
def resource_not_found(e):
    return jsonify(error=str(e)), 403


@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts)


@app.route('/register', methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if not user:
            new_user = User(
                email=form.email.data,
                password=generate_password_hash(form.password.data, method='pbkdf2:sha256', salt_length=8),
                name=form.name.data
            )
            db.session.add(new_user)
            db.session.commit()
            user = User.query.filter_by(email=form.email.data).first()
            login_user(user)
            return redirect("/")
        else:
            flash("Email is already taken. Please log-in here")
            return redirect("login")
    else:
        return render_template("register.html", form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        user = User.query.filter_by(email=email).first()
        if user:
            if check_password_hash(user.password, password):
                # store user id in session
                login_user(user)
                return redirect("/")
            else:
                flash("Password entered is wrong")
                return redirect("login")
        else:
            flash("Email entered is wrong")
            return redirect("login")
    else:
        return render_template("login.html", form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def show_post(post_id):
    form = CommentForm(
        comment=""
    )
    requested_post = BlogPost.query.get(post_id)
    if form.validate_on_submit():
        comment_data = Comment(
            comment=form.comment.data,
            blog_id=post_id,
            user_id=current_user.id
        )
        db.session.add(comment_data)
        db.session.commit()
        return redirect(url_for("show_post", post_id=requested_post.id) )
    all_comments = Comment.query.filter_by(blog_id=post_id)
    return render_template("post.html", post=requested_post, form=form, comments=all_comments)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/new-post", endpoint="add_new_post", methods=["GET", "POST"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author_id=current_user.id,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


@app.route("/edit-post/<int:post_id>", endpoint="edit_post", methods=["GET", "POST"])
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author_id=current_user.id,
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


@app.route("/delete/<int:post_id>", endpoint="delete_post")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(debug=True)
