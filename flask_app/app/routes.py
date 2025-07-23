from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from . import db, login_manager
from .models import User, BlogPost, Like
from .forms import RegisterForm, LoginForm, BlogPostForm
from flask import current_app as app

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    posts = BlogPost.query.order_by(BlogPost.timestamp.desc()).all()
    return render_template('home.html', posts=posts, current_user=current_user)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        existing_username = User.query.filter_by(username=form.username.data).first()
        existing_email = User.query.filter_by(email=form.email.data).first()
        if existing_username:
            flash('Username already exists. Please choose another.')
            return render_template('register.html', form=form)
        if existing_email:
            flash('Email already exists. Please use another email.')
            return render_template('register.html', form=form)
        try:
            hashed_pw = generate_password_hash(form.password.data)
            user = User(username=form.username.data, email=form.email.data, password=hashed_pw)
            db.session.add(user)
            db.session.commit()
            flash('Account created! You can now log in.')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred during registration. Please try again.')
            return render_template('register.html', form=form)
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials.')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    form = BlogPostForm()
    if form.validate_on_submit():
        post = BlogPost(title=form.title.data, content=form.content.data, author_id=current_user.id)
        db.session.add(post)
        db.session.commit()
        flash('Blog post added!')
        return redirect(url_for('dashboard'))
    user_id = request.args.get('user_id', type=int)
    if user_id:
        posts = BlogPost.query.filter_by(author_id=user_id).order_by(BlogPost.timestamp.desc()).all()
    else:
        posts = BlogPost.query.order_by(BlogPost.timestamp.desc()).all()
    return render_template('dashboard.html', username=current_user.username, form=form, posts=posts, current_user=current_user, request=request)

@app.route('/like/<int:post_id>', methods=['POST'])
@login_required
def like_post(post_id):
    post = BlogPost.query.get_or_404(post_id)
    like = Like.query.filter_by(user_id=current_user.id, post_id=post_id).first()
    if not like:
        like = Like(user_id=current_user.id, post_id=post_id)
        db.session.add(like)
        db.session.commit()
        flash('You liked the post!')
    else:
        db.session.delete(like)
        db.session.commit()
        flash('You unliked the post!')
    return redirect(url_for('dashboard'))

@app.route('/like_json/<int:post_id>', methods=['POST'])
@login_required
def like_post_json(post_id):
    post = BlogPost.query.get_or_404(post_id)
    like = Like.query.filter_by(user_id=current_user.id, post_id=post_id).first()
    liked = False
    if not like:
        like = Like(user_id=current_user.id, post_id=post_id)
        db.session.add(like)
        db.session.commit()
        liked = True
    else:
        db.session.delete(like)
        db.session.commit()
        liked = False
    return jsonify({
        'liked': liked,
        'like_count': len(post.likes)
    })

@app.route('/profile')
@login_required
def profile():
    user_posts = BlogPost.query.filter_by(author_id=current_user.id).order_by(BlogPost.timestamp.desc()).all()
    user_likes = Like.query.filter_by(user_id=current_user.id).all()
    liked_post_ids = [like.post_id for like in user_likes]
    liked_posts = BlogPost.query.filter(BlogPost.id.in_(liked_post_ids)).all() if liked_post_ids else []
    return render_template(
        'profile.html',
        username=current_user.username,
        email=current_user.email,
        post_count=len(user_posts),
        like_count=len(user_likes),
        recent_posts=user_posts[:3],
        liked_posts=liked_posts[:3]
    )

@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        new_username = request.form.get('username')
        new_email = request.form.get('email')
        if new_username:
            current_user.username = new_username
        if new_email:
            current_user.email = new_email
        try:
            db.session.commit()
            flash('Profile updated!')
        except Exception:
            db.session.rollback()
            flash('Username or email already exists.')
        return redirect(url_for('profile'))
    return render_template('edit_profile.html', username=current_user.username, email=current_user.email)

@app.route('/delete_account', methods=['POST'])
@login_required
def delete_account():
    user = User.query.get(current_user.id)
    # Delete likes, posts, then user
    Like.query.filter_by(user_id=user.id).delete()
    BlogPost.query.filter_by(author_id=user.id).delete()
    db.session.delete(user)
    db.session.commit()
    logout_user()
    flash('Your account has been deleted.')
    return redirect(url_for('home'))

@app.route('/delete_post/<int:post_id>', methods=['POST'])
@login_required
def delete_post(post_id):
    post = BlogPost.query.get_or_404(post_id)
    if post.author_id != current_user.id:
        flash('You can only delete your own posts.')
        return redirect(url_for('dashboard'))
    Like.query.filter_by(post_id=post.id).delete()
    db.session.delete(post)
    db.session.commit()
    flash('Blog post deleted.')
    return redirect(url_for('dashboard'))
