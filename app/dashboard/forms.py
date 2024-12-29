from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, FloatField, IntegerField
from wtforms.validators import DataRequired, Email, Length, NumberRange

# Formulario para Usuarios
class UsuarioForm(FlaskForm):
    nombre = StringField('Nombre', validators=[DataRequired(), Length(max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Contraseña', validators=[Length(min=6)])
    es_admin = BooleanField('Es administrador')
    submit = SubmitField('Guardar')

# Formulario para Productos
class ProductoForm(FlaskForm):
    nombre = StringField('Nombre del Producto', validators=[DataRequired(), Length(max=100)])
    total_piezas = IntegerField('Total de Piezas', validators=[DataRequired(), NumberRange(min=1)])
    precio = FloatField('Precio', validators=[DataRequired(), NumberRange(min=0)])
    submit = SubmitField('Guardar')
