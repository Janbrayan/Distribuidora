from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import pytz  # Asegúrate de instalar pytz

# Configuración de la zona horaria
TZ = pytz.timezone('America/Mexico_City')

class Usuario(UserMixin, db.Model):
    """Modelo para los usuarios del sistema."""
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)  # Campo para el nombre
    email = db.Column(db.String(120), unique=True, nullable=False)  # Correo único
    password_hash = db.Column(db.String(128), nullable=False)  # Contraseña cifrada
    es_admin = db.Column(db.Boolean, default=False)  # Indicador de rol de administrador
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(TZ))  # Fecha de creación
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(TZ), onupdate=lambda: datetime.now(TZ))  # Última modificación

    # Relación con las ventas
    ventas = db.relationship('Venta', backref='usuario', lazy=True)

    def set_password(self, password):
        """Cifra la contraseña del usuario y la guarda."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verifica si la contraseña proporcionada coincide con el hash almacenado."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<Usuario {self.nombre} ({self.email})>"


class Producto(db.Model):
    """Modelo para los productos en el sistema."""
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)  # Nombre del producto
    total_piezas = db.Column(db.Integer, nullable=False)  # Total de piezas registradas
    stock = db.Column(db.Integer, nullable=False)  # Piezas disponibles
    precio = db.Column(db.Float, nullable=False)  # Precio del producto
    ultima_actualizacion = db.Column(db.DateTime, default=lambda: datetime.now(TZ), onupdate=lambda: datetime.now(TZ))  # Última modificación

    # Relación con las ventas
    ventas = db.relationship('Venta', backref='producto', lazy=True)

    def actualizar_stock(self, cantidad_vendida):
        """Disminuye el stock con base en las ventas realizadas."""
        if cantidad_vendida > self.stock:
            raise ValueError("La cantidad vendida excede el stock disponible.")
        self.stock -= cantidad_vendida
        self.ultima_actualizacion = datetime.now(TZ)

    def __repr__(self):
        return f"<Producto {self.nombre} (Stock: {self.stock}, Precio: {self.precio})>"


class Venta(db.Model):
    """Modelo para registrar ventas."""
    id = db.Column(db.Integer, primary_key=True)
    cantidad = db.Column(db.Integer, nullable=False)  # Cantidad vendida
    total = db.Column(db.Float, nullable=False)  # Total de la venta
    fecha = db.Column(db.DateTime, default=lambda: datetime.now(TZ))  # Fecha de la venta

    # Relación con Usuario
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)

    # Relación con Producto
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'), nullable=False)

    def __repr__(self):
        return f"<Venta {self.id} (Cantidad: {self.cantidad}, Total: {self.total})>"
