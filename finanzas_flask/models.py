from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timedelta
db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    email = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(256), nullable=False)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    type = db.Column(db.String(50))
    category = db.Column(db.String(100))
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200))
    date = db.Column(db.DateTime)


class Acciones(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    accion = db.Column(db.String(10), nullable=False)
    tipo_operacion = db.Column(db.String(10), nullable=False, default='compra')
    cantidad = db.Column(db.Float, nullable=False)
    precio = db.Column(db.Float, nullable=False)
    fecha = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    fecha_actualizacion = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def validar(self):
        errors = []
        if not self.accion or len(self.accion) > 10:
            errors.append("Símbolo de acción inválido")
        if self.cantidad <= 0:
            errors.append("Cantidad debe ser positiva")
        if self.precio <= 0:
            errors.append("Precio debe ser positivo")
        return errors


class Criptomonedas(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    cripto = db.Column(db.String(20), nullable=False)  # ID de la cripto en CoinCap (ej: bitcoin)
    simbolo = db.Column(db.String(10), nullable=False)  # Símbolo (ej: BTC)
    tipo_operacion = db.Column(db.String(10), nullable=False, default='compra')
    cantidad = db.Column(db.Float, nullable=False)
    precio = db.Column(db.Float, nullable=False)
    fecha = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    fecha_actualizacion = db.Column(db.DateTime, onupdate=datetime.utcnow)



    def validar(self):
        errors = []
        if not self.cripto or len(self.cripto) > 20:
            errors.append("ID de criptomoneda inválido")
        if not self.simbolo or len(self.simbolo) > 10:
            errors.append("Símbolo de criptomoneda inválido")
        if self.cantidad <= 0:
            errors.append("Cantidad debe ser positiva")
        if self.precio <= 0:
            errors.append("Precio debe ser positivo")
        return errors