from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required
from app.auth.forms import LoginForm
from app.models import Usuario
from app import db
from app.auth import auth

@auth.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = Usuario.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash('Inicio de sesión exitoso. ¡Bienvenido!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard.index'))
        flash('Correo o contraseña incorrectos. Inténtalo de nuevo.', 'error')
    return render_template('auth/login.html', form=form)

@auth.route('/logout')
@login_required
def logout():
    """Ruta para cerrar sesión."""
    logout_user()
    flash('Sesión cerrada con éxito', 'info')
    return redirect(url_for('auth.login'))
