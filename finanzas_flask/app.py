from flask import Flask, render_template, redirect, url_for, flash, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
import requests
from plotly.offline import plot
import plotly.graph_objs as go
import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
import sqlite3
from datetime import datetime, timedelta  # Añadir timedelta
from flask_migrate import Migrate
from random import randint
from flask import session
import secrets
from datetime import datetime, timedelta
import yfinance as yf
import logging
from openai import OpenAI




app = Flask(__name__)

# Configuración general
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'una-clave-secreta-muy-segura'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path, 'finanzas.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# CONFIGURACIÓN DE CORREO CON GMAIL + CONTRASEÑA DE APLICACIÓN
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'app.financiera.flask@gmail.com'
app.config['MAIL_PASSWORD'] = 'bwvapdfvfreydngr'  # No uses tu contraseña normal
mail = Mail(app)


# Asegurar que la carpeta instance exista
os.makedirs(app.instance_path, exist_ok=True)

# Inicialización extensiones
db = SQLAlchemy(app)
migrate = Migrate(app, db)
mail = Mail(app)
s = URLSafeTimedSerializer(app.secret_key)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


# Configurar logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

#Modelos
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    email = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    
class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    type = db.Column(db.String(50), nullable=False)       # 'ingreso' o 'gasto'
    category = db.Column(db.String(100), nullable=False)  # Ej: 'comida', 'salario'
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200))
    date = db.Column(db.DateTime, default=datetime.utcnow)


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

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return redirect(url_for('inicio'))  # O render_template("index.html")

#---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Rutas de acciones
@app.route('/acciones', methods=['GET', 'POST'])
@login_required
def acciones():
    if request.method == 'POST':
        try:
            # Validación de datos
            accion = request.form.get('accion', '').strip().upper()
            try:
                inversion = float(request.form.get('inversion', 0))
            except ValueError:
                flash('Monto de inversión inválido', 'danger')
                return redirect(url_for('acciones'))

            fecha_compra_str = request.form.get('fecha_compra', '')
            
            if not accion or inversion <= 0 or not fecha_compra_str:
                flash('Complete todos los campos correctamente', 'danger')
                return redirect(url_for('acciones'))

            # Procesamiento de fecha
            try:
                fecha_compra = datetime.strptime(fecha_compra_str, '%Y-%m-%d')
                if fecha_compra > datetime.utcnow():
                    flash('La fecha no puede ser futura', 'danger')
                    return redirect(url_for('acciones'))
            except ValueError:
                flash('Formato de fecha debe ser AAAA-MM-DD', 'danger')
                return redirect(url_for('acciones'))

            # Obtener datos de mercado
            try:
                ticker = yf.Ticker(accion)
                data = ticker.history(
                    start=fecha_compra.date(), 
                    end=datetime.utcnow().date() + timedelta(days=1)
                )
                
                if data.empty:
                    flash('No se encontraron datos para esta acción', 'warning')
                    return redirect(url_for('acciones'))
                    
                precio_compra = float(data['Close'].iloc[0])
                cantidad = inversion / precio_compra
                
            except Exception as e:
                logger.error(f"Error al obtener datos: {str(e)}")
                flash('Error al obtener datos de mercado', 'danger')
                return redirect(url_for('acciones'))

            # Crear registro
            nueva_operacion = Acciones(
                user_id=current_user.id,
                accion=accion,
                tipo_operacion='compra',
                cantidad=round(cantidad, 6),
                precio=round(precio_compra, 2),
                fecha=fecha_compra
            )
            
            # Validar antes de guardar
            if errors := nueva_operacion.validar():
                for error in errors:
                    flash(error, 'danger')
                return redirect(url_for('acciones'))

            db.session.add(nueva_operacion)
            db.session.commit()
            
            # Verificar que realmente se guardó
            op_guardada = db.session.get(Acciones, nueva_operacion.id)
            if not op_guardada:
                raise Exception("No se pudo verificar el guardado")
            
            flash('Inversión registrada exitosamente!', 'success')
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error en transacción: {str(e)}")
            flash('Error al guardar la operación', 'danger')
        finally:
            return redirect(url_for('acciones'))

    # GET: Mostrar operaciones
    transacciones = db.session.execute(
        db.select(Acciones)
        .filter_by(user_id=current_user.id)
        .order_by(Acciones.fecha.desc())
        .limit(5)
    ).scalars()
    
    stock_names = {
    'AAPL': {'name': 'APPLE', 'symbol': 'AAPL'},
    'MSFT': {'name': 'MICROSOFT', 'symbol': 'MSFT'},
    'GOOGL': {'name': 'ALPHABET', 'symbol': 'GOOGL'},
    'AMZN': {'name': 'AMAZON', 'symbol': 'AMZN'},
    'META': {'name': 'META', 'symbol': 'META'},
    'TSLA': {'name': 'TESLA', 'symbol': 'TSLA'},
    'NVDA': {'name': 'NVIDIA', 'symbol': 'NVDA'},
    'JPM': {'name': 'JP MORGAN', 'symbol': 'JPM'},
    'V': {'name': 'VISA', 'symbol': 'V'},
    'WMT': {'name': 'WALMART', 'symbol': 'WMT'}
    }

    return render_template('acciones.html', transacciones=transacciones, stockNames=stock_names, current_user=current_user)



@app.route('/eliminar_inversion/<int:id>', methods=['DELETE'])
@login_required
def eliminar_inversion(id):
    try:
        inversion = db.session.get(Acciones, id)
        if not inversion or inversion.user_id != current_user.id:
            return jsonify({"error": "Inversión no encontrada"}), 404
            
        db.session.delete(inversion)
        db.session.commit()
        return jsonify({"success": True})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'Error eliminando inversión: {str(e)}')
        return jsonify({"error": str(e)}), 500

@app.route('/accion_datos')
@login_required
def accion_datos():
    try:
        simbolo = request.args.get('simbolo', '').strip().upper()
        fecha = request.args.get('fecha', '').strip()
        try:
            inversion = float(request.args.get('inversion', 0))
        except ValueError:
            return jsonify({"error": "Monto de inversión inválido"}), 400
        
        if not simbolo or not fecha or inversion <= 0:
            return jsonify({"error": "Parámetros incompletos o inválidos"}), 400

        fecha_inicial = datetime.strptime(fecha, "%Y-%m-%d").date()
        fecha_final = datetime.utcnow().date()
        
        if fecha_inicial > fecha_final:
            return jsonify({"error": "La fecha de compra no puede ser futura"}), 400

        data = yf.download(simbolo, start=fecha_inicial, end=fecha_final + timedelta(days=1))
        
        if data.empty:
            return jsonify({"error": "No se encontraron datos para esta acción"}), 404
        
        precio_compra = float(data['Close'].iloc[0])
        precio_actual = float(data['Close'].iloc[-1])
        acciones_compradas = inversion / precio_compra
        valor_actual = acciones_compradas * precio_actual
        rendimiento = ((valor_actual - inversion) / inversion) * 100
        
        historial = []
        frames = []
        
        for i, (index, row) in enumerate(data.iterrows()):
            valor = float(row['Close']) * acciones_compradas
            historial.append({
                "fecha": index.strftime("%Y-%m-%d"),
                "valor": valor
            })
            
            if i % 5 == 0 or i == len(data)-1:
                frames.append({
                    "name": index.strftime("%Y-%m-%d"),
                    "data": historial.copy()
                })
        
        return jsonify({
            "rendimiento": {
                "accion": simbolo,
                "inversion": float(inversion),
                "fecha_compra": fecha,
                "valor_actual": float(valor_actual),
                "rendimiento": float(rendimiento)
            },
            "historial": historial,
            "frames": frames[-10:]
        })
        
    except Exception as e:
        logger.error(f'Error obteniendo datos de acción: {str(e)}')
        return jsonify({"error": str(e)}), 500

@app.route('/analisis_accion', methods=['POST'])
@login_required
def analisis_accion():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Datos no proporcionados"}), 400
            
        accion = data.get('accion', '').strip().upper()
        rendimiento = data.get('rendimiento', {})
        
        if not accion or not isinstance(rendimiento, dict):
            return jsonify({"error": "Datos incompletos o inválidos"}), 400

        pregunta = f"Analiza el rendimiento de la acción {accion}. "
        pregunta += f"La inversión inicial fue de ${rendimiento.get('inversion', 0):.2f} y ahora vale ${rendimiento.get('valor_actual', 0):.2f} "
        pregunta += f"(rendimiento del {rendimiento.get('rendimiento', 0):.2f}%). "
        pregunta += "Proporciona un análisis conciso y recomendaciones basadas en este rendimiento."

        # Configuración del cliente de DeepSeek
        client = OpenAI(
            api_key="sk-f96903a695404895a9cc563a7ee3c4c5",
            base_url="https://api.deepseek.com"
        )

        # Llamada a la API de DeepSeek
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role": "system", 
                    "content": "Eres un analista financiero experto. Proporciona análisis concisos y recomendaciones prácticas basadas en datos."
                },
                {"role": "user", "content": pregunta}
            ],
            temperature=0.7,
            max_tokens=500,
            stream=False
        )
        
        analisis = response.choices[0].message.content
        
        return jsonify({"analisis": analisis})
    
    except Exception as e:
        return jsonify({"error": f"Error al generar el análisis: {str(e)}"}), 500

#-----------------------------------------------------------------------------------------------------------------------------------------------------------------
CRIPTO_SIMBOLOS = {
    "bitcoin": "BTC-USD",
    "ethereum": "ETH-USD",
    "tether": "USDT-USD",
    "binance-coin": "BNB-USD",
    "solana": "SOL-USD",
    "usd-coin": "USDC-USD",
    "xrp": "XRP-USD",
    "dogecoin": "DOGE-USD",
    "cardano": "ADA-USD",
    "shiba-inu": "SHIB-USD"
}

API_KEY_COINCAP = "837f7d007ff30e74547acd1bdc8d8c6e462f6b8f8b8528546f1c43357288ed95"




#-----------------------------CRIPTOMONEDAS-----------------------------------------------------------------------------------------------------------------------------------

@app.route('/criptomonedas', methods=['GET', 'POST'])
@login_required
def criptomonedas():
    if request.method == 'POST':
        try:
            # Validación de datos
            cripto = request.form.get('cripto', '').strip().lower()
            try:
                inversion = float(request.form.get('inversion', 0))
            except ValueError:
                flash('Monto de inversión inválido', 'danger')
                return redirect(url_for('criptomonedas'))

            fecha_compra_str = request.form.get('fecha_compra', '')
            
            if not cripto or inversion <= 0 or not fecha_compra_str or cripto not in CRIPTO_SIMBOLOS:
                flash('Complete todos los campos correctamente', 'danger')
                return redirect(url_for('criptomonedas'))

            # Procesamiento de fecha
            try:
                fecha_compra = datetime.strptime(fecha_compra_str, '%Y-%m-%d')
                if fecha_compra > datetime.utcnow():
                    flash('La fecha no puede ser futura', 'danger')
                    return redirect(url_for('criptomonedas'))
            except ValueError:
                flash('Formato de fecha debe ser AAAA-MM-DD', 'danger')
                return redirect(url_for('criptomonedas'))

            # Obtener datos de mercado usando yfinance
            try:
                ticker = yf.Ticker(CRIPTO_SIMBOLOS[cripto])
                data = ticker.history(
                    start=fecha_compra.date(), 
                    end=datetime.utcnow().date() + timedelta(days=1)
                )
                
                if data.empty:
                    flash('No se encontraron datos para esta criptomoneda', 'warning')
                    return redirect(url_for('criptomonedas'))
                    
                precio_compra = float(data['Close'].iloc[0])
                cantidad = inversion / precio_compra
                
                # Obtener símbolo de la cripto (extraer de CRIPTO_SIMBOLOS)
                simbolo = CRIPTO_SIMBOLOS[cripto].split('-')[0]
                
            except Exception as e:
                logger.error(f"Error al obtener datos: {str(e)}")
                flash('Error al obtener datos de mercado', 'danger')
                return redirect(url_for('criptomonedas'))

            # Crear registro
            nueva_operacion = Criptomonedas(
                user_id=current_user.id,
                cripto=cripto,
                simbolo=simbolo,
                tipo_operacion='compra',
                cantidad=round(cantidad, 8),
                precio=round(precio_compra, 6),
                fecha=fecha_compra
            )
            
            # Validar antes de guardar
            if errors := nueva_operacion.validar():
                for error in errors:
                    flash(error, 'danger')
                return redirect(url_for('criptomonedas'))

            db.session.add(nueva_operacion)
            db.session.commit()
            
            # Verificar que realmente se guardó
            op_guardada = db.session.get(Criptomonedas, nueva_operacion.id)
            if not op_guardada:
                raise Exception("No se pudo verificar el guardado")
            
            flash('Inversión registrada exitosamente!', 'success')
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error en transacción: {str(e)}")
            flash(f'Error al guardar la operación: {str(e)}', 'danger')
        return redirect(url_for('criptomonedas'))

    # GET: mostrar página y datos del usuario
    transacciones = db.session.execute(
        db.select(Criptomonedas)
        .filter_by(user_id=current_user.id)
        .order_by(Criptomonedas.fecha.desc())
        .limit(5)
    ).scalars()

    return render_template('criptomonedas.html', transacciones=transacciones)

@app.route('/eliminar_inversion_cripto/<int:id>', methods=['DELETE'])
@login_required
def eliminar_inversion_cripto(id):
    try:
        inversion = db.session.get(Criptomonedas, id)
        if not inversion or inversion.user_id != current_user.id:
            return jsonify({"error": "Inversión no encontrada o no autorizada"}), 404
            
        db.session.delete(inversion)
        db.session.commit()
        return jsonify({"success": True})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'Error eliminando inversión en cripto: {str(e)}')
        return jsonify({"error": str(e)}), 500

# Reemplazar la ruta de cripto_datos para usar yfinance
@app.route('/cripto_datos')
@login_required
def cripto_datos():
    try:
        cripto = request.args.get('simbolo', '').strip().lower()
        fecha = request.args.get('fecha', '').strip()
        
        try:
            inversion = float(request.args.get('inversion', 0))
            if inversion <= 0:
                return jsonify({"error": "El monto debe ser mayor a cero"}), 400
        except ValueError:
            return jsonify({"error": "Monto de inversión inválido"}), 400
        
        if not cripto or not fecha or cripto not in CRIPTO_SIMBOLOS:
            return jsonify({"error": "Parámetros incompletos o inválidos"}), 400

        try:
            fecha_inicial = datetime.strptime(fecha, "%Y-%m-%d").date()
            fecha_final = datetime.utcnow().date()
            
            if fecha_inicial > fecha_final:
                return jsonify({"error": "La fecha de compra no puede ser futura"}), 400
                
        except ValueError as e:
            return jsonify({"error": f"Formato de fecha inválido: {str(e)}. Use YYYY-MM-DD"}), 400

        # Obtener datos históricos con yfinance
        data = yf.download(CRIPTO_SIMBOLOS[cripto], start=fecha_inicial, end=fecha_final + timedelta(days=1))
        
        if data.empty:
            return jsonify({"error": "No hay datos disponibles para el período solicitado"}), 404
        
        # Procesamiento de datos
        precio_compra = float(data['Close'].iloc[0])
        precio_actual = float(data['Close'].iloc[-1])
        cripto_compradas = inversion / precio_compra
        valor_actual = cripto_compradas * precio_actual
        rendimiento = ((valor_actual - inversion) / inversion) * 100
        
        historial = []
        
        for index, row in data.iterrows():
            valor = float(row['Close']) * cripto_compradas
            historial.append({
                "fecha": index.strftime("%Y-%m-%d"),
                "valor": valor
            })
        
        return jsonify({
            "rendimiento": {
                "cripto": cripto,
                "simbolo": CRIPTO_SIMBOLOS[cripto].split('-')[0],
                "inversion": float(inversion),
                "fecha_compra": fecha,
                "valor_actual": float(valor_actual),
                "rendimiento": float(rendimiento)
            },
            "historial": historial
        })
            
    except Exception as e:
        logger.error(f'Error inesperado: {str(e)}')
        return jsonify({"error": f"Error interno del servidor: {str(e)}"}), 500

@app.route('/analisis_cripto', methods=['POST'])
@login_required
def analisis_cripto():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Datos no proporcionados"}), 400
            
        cripto = data.get('cripto', '').strip().lower()
        rendimiento = data.get('rendimiento', {})

        if not cripto or not isinstance(rendimiento, dict):
            return jsonify({"error": "Datos incompletos o inválidos"}), 400

        # Validar y convertir a float
        try:
            inversion_val = float(rendimiento.get('inversion', 0) or 0)
            valor_actual_val = float(rendimiento.get('valor_actual', 0) or 0)
            rendimiento_val = float(rendimiento.get('rendimiento', 0) or 0)
        except (ValueError, TypeError):
            return jsonify({"error": "Datos numéricos inválidos para el análisis"}), 400

        pregunta = (
            f"Analiza el rendimiento de {cripto.upper()} ({rendimiento.get('simbolo', '')}). "
            f"La inversión inicial fue de ${inversion_val:.2f} y ahora vale ${valor_actual_val:.2f} "
            f"(rendimiento del {rendimiento_val:.2f}%). "
            "Proporciona un análisis conciso y recomendaciones basadas en este rendimiento."
        )

        # Configuración del cliente de DeepSeek
        client = OpenAI(
            api_key="sk-f96903a695404895a9cc563a7ee3c4c5",
            base_url="https://api.deepseek.com"
        )

        # Llamada a la API
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role": "system", 
                    "content": "Eres un analista de criptomonedas experto. Proporciona análisis concisos y recomendaciones prácticas basadas en datos."
                },
                {"role": "user", "content": pregunta}
            ],
            temperature=0.7,
            max_tokens=500,
            stream=False
        )
        
        analisis = response.choices[0].message.content
        return jsonify({"analisis": analisis})
    
    except Exception as e:
        return jsonify({"error": f"Error al generar el análisis: {str(e)}"}), 500

#-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        # Validaciones
        errors = []
        
        if not username:
            errors.append('El nombre de usuario es obligatorio.')
        if not email:
            errors.append('El correo electrónico es obligatorio.')
        if not password:
            errors.append('La contraseña es obligatoria.')
        if password != confirm_password:
            errors.append('Las contraseñas no coinciden.')
        if len(password) < 8:
            errors.append('La contraseña debe tener al menos 8 caracteres.')

        # Verificar si usuario o email ya existen
        if User.query.filter_by(username=username).first():
            errors.append('El nombre de usuario ya está en uso.')
        if User.query.filter_by(email=email).first():
            errors.append('El correo electrónico ya está registrado.')

        if errors:
            for error in errors:
                flash(error)
            return redirect(url_for('register'))

        try:
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
            new_user = User(username=username, email=email, password=hashed_password)
            
            db.session.add(new_user)
            db.session.commit()

            flash('¡Registro exitoso! Por favor inicia sesión.')
            return redirect(url_for('login'))  # Redirigir a login después de registro

        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Error en registro: {str(e)}')
            flash('Ocurrió un error al registrar. Por favor intenta nuevamente.')
            return redirect(url_for('register'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash('Por favor ingresa usuario y contraseña.')
            return redirect(url_for('login'))

        user = User.query.filter_by(username=username).first()
        
        if user:
            if check_password_hash(user.password, password):
                login_user(user)
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('inicio'))
            else:
                flash('Contraseña incorrecta.')
        else:
            flash('Usuario no encontrado.')

    return render_template('login.html')


from flask import Flask, render_template, redirect, url_for, flash, request
from random import randint

# Diccionario temporal para almacenar códigos
reset_codes = {}

from flask_mail import Mail

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        if user:
            try:
                code = str(randint(100000, 999999))
                reset_codes[email] = {
                    'code': code,
                    'user_id': user.id,
                    'timestamp': datetime.utcnow()
                }
                
                msg = Message(
                    "Código de Recuperación",
                    sender=app.config['MAIL_USERNAME'],
                    recipients=[email],
                    charset='utf-8'  # Añade esta línea
                )
                msg.body = f"""
                Hola {user.username},

                Tu código de verificación es: {code}

                Ingresa este código en la página de recuperación.
                """
                mail.send(msg)
                
                flash('Código enviado. Revisa tu correo electrónico.', 'success')
                return redirect(url_for('reset_password', email=email))
                
            except Exception as e:
                flash(f'Error al enviar el correo: {str(e)}', 'danger')
                app.logger.error(f"Error enviando correo: {str(e)}")
        
        else:
            flash('Correo no registrado.', 'danger')
    
    return render_template('forgot_password.html')

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        email = request.form.get('email')
        code = request.form.get('code')
        new_password = request.form.get('password')
        
        # Verificar código y user_id
        if email in reset_codes and reset_codes[email]['code'] == code:
            user = User.query.get(reset_codes[email]['user_id'])
            if user:
                user.password = generate_password_hash(new_password)
                db.session.commit()
                del reset_codes[email]  # Eliminar código usado
                flash('Contraseña actualizada. ¡Inicia sesión!', 'success')
                return redirect(url_for('login'))
        
        flash('Código incorrecto o expirado', 'danger')
        return redirect(url_for('reset_password', email=email))
    
    # GET: Mostrar formulario
    email = request.args.get('email')
    return render_template('reset_password.html', email=email)

@app.route('/logout')  
@login_required
def logout():
    # Limpiar todos los mensajes flash antes de cerrar sesión
    session.pop('_flashes', None)
    logout_user()
    flash('Has cerrado sesión correctamente.', 'success')  # Este es el único mensaje que queremos mostrar
    return redirect(url_for('login'))


DEEPSEEK_API_KEY = "sk-f96903a695404895a9cc563a7ee3c4c5"
@app.route('/asistente', methods=['GET', 'POST'])
@login_required
def asistente():
    if request.method == 'GET':
        return render_template("asistente.html")
    
    try:
        # Validación de datos
        data = request.get_json() if request.is_json else request.form
        pregunta = data.get('pregunta', '').strip()
        
        if not pregunta:
            return jsonify({'error': 'La pregunta no puede estar vacía'}), 400
            
        # Configuración de la API call
        headers = {
            'Authorization': f'Bearer {DEEPSEEK_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {
                    "role": "system", 
                    "content": "Eres un experto financiero que responde preguntas claras y prácticas en español."
                },
                {"role": "user", "content": pregunta}
            ],
            "temperature": 0.7,
            "max_tokens": 1000
        }
        
        # Timeout más conservador
        response = requests.post(
            'https://api.deepseek.com/chat/completions',
            headers=headers,
            json=payload,
            timeout=30  # Aumentado de 20 a 30 segundos
        )
        
        # Verificación exhaustiva de la respuesta
        response.raise_for_status()
        response_data = response.json()
        
        if not response_data.get("choices"):
            raise ValueError("Estructura de respuesta inesperada de la API")
            
        respuesta = response_data["choices"][0]["message"]["content"]
        
        return jsonify({
            'success': True,
            'respuesta': respuesta
        })
        
    except requests.exceptions.RequestException as e:
        app.logger.error(f'Error de conexión: {str(e)}')
        return jsonify({
            'error': 'Error al conectar con el servicio de IA',
            'details': str(e)
        }), 503
        
    except (KeyError, ValueError) as e:
        app.logger.error(f'Error procesando respuesta: {str(e)}')
        return jsonify({
            'error': 'Error procesando la respuesta del servicio',
            'details': str(e)
        }), 502
        
    except Exception as e:
        app.logger.error(f'Error inesperado: {str(e)}')
        return jsonify({
            'error': 'Error interno del servidor',
            'details': str(e)
        }), 500
#------------------------------ Ruta de inicio ----------------------------------------
@app.route('/inicio', methods=['GET', 'POST'])
@login_required
def inicio():
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            tipo = request.form.get('type')
            categoria = request.form.get('category')
            monto = float(request.form.get('amount', 0))
            descripcion = request.form.get('description', '').strip()
            fecha_str = request.form.get('transaction_date')

            # Validar campos
            if not tipo or not categoria or monto <= 0:
                flash('Por favor completa todos los campos correctamente.')
                return redirect(url_for('inicio'))

            # Validar fecha
            try:
                fecha = datetime.strptime(fecha_str, '%Y-%m-%d')
                if fecha > datetime.now():
                    flash('La fecha no puede ser futura', 'danger')
                    return redirect(url_for('inicio'))
            except ValueError:
                flash('Formato de fecha inválido', 'danger')
                return redirect(url_for('inicio'))

            # Crear nueva transacción
            nueva_transaccion = Transaction(
                user_id=current_user.id,
                type=tipo,
                category=categoria,
                amount=monto,
                date=fecha,
                description=descripcion
            )
            db.session.add(nueva_transaccion)
            db.session.commit()
            flash('Transacción registrada exitosamente!', 'success')
            return redirect(url_for('inicio'))

        except ValueError:
            flash('El monto debe ser un número válido.', 'danger')
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Error añadiendo transacción: {str(e)}')
            flash('Ocurrió un error al registrar la transacción.', 'danger')

     # Obtener parámetros de filtro si existen
    year = request.args.get('year')
    month = request.args.get('month')
    
    # Consulta base
    query = Transaction.query.filter_by(user_id=current_user.id)
    
    # Aplicar filtros si existen
    if year:
        query = query.filter(db.extract('year', Transaction.date) == year)
        if month:
            query = query.filter(db.extract('month', Transaction.date) == month)
    
    # Obtener transacciones ordenadas
    transacciones = query.order_by(Transaction.date.desc()).all()
    
    # Obtener años disponibles para el filtro
    years_available = db.session.query(
        db.extract('year', Transaction.date).label('year')
    ).filter_by(user_id=current_user.id).distinct().order_by('year').all()
    years_available = [str(int(y[0])) for y in years_available] if years_available else []
    
    # Meses disponibles para el filtro
    months_available = [
        {'value': '1', 'name': 'Enero'},
        {'value': '2', 'name': 'Febrero'},
        {'value': '3', 'name': 'Marzo'},
        {'value': '4', 'name': 'Abril'},
        {'value': '5', 'name': 'Mayo'},
        {'value': '6', 'name': 'Junio'},
        {'value': '7', 'name': 'Julio'},
        {'value': '8', 'name': 'Agosto'},
        {'value': '9', 'name': 'Septiembre'},
        {'value': '10', 'name': 'Octubre'},
        {'value': '11', 'name': 'Noviembre'},
        {'value': '12', 'name': 'Diciembre'}
    ]

    # Obtener transacciones del usuario
    transacciones = Transaction.query.filter_by(user_id=current_user.id)\
                                     .order_by(Transaction.date.desc()).all()

    # Calcular totales
    ingresos = sum(t.amount for t in transacciones if t.type == 'ingreso')
    gastos = sum(t.amount for t in transacciones if t.type == 'gasto')
    balance = ingresos - gastos

    # Gráfico de pastel
    pie_div = ""
    if ingresos > 0 or gastos > 0:
        pie = go.Figure(data=[go.Pie(
            labels=['Ingresos', 'Gastos'], 
            values=[ingresos, gastos],
            marker_colors=['#28a745', '#dc3545']
        )])
        pie.update_layout(title_text='Distribución de Ingresos y Gastos')
        pie_div = plot(pie, output_type='div')

    # Gráfico de barras por categoría (solo si hay datos)
    bar_div = ""
    categorias = {}
    for t in transacciones:
            if t.category not in categorias:
                categorias[t.category] = {'ingresos': 0, 'gastos': 0}
            if t.type == 'ingreso':
                categorias[t.category]['ingresos'] += t.amount
            else:
                categorias[t.category]['gastos'] += t.amount

    if categorias:
        bar = go.Figure()
        bar.add_trace(go.Bar(
            x=list(categorias.keys()),
            y=[v['ingresos'] for v in categorias.values()],
            name='Ingresos',
            marker_color='#28a745'
        ))
        bar.add_trace(go.Bar(
            x=list(categorias.keys()),
            y=[v['gastos'] for v in categorias.values()],
            name='Gastos',
            marker_color='#dc3545'
        ))
        bar.update_layout(
            title_text='Balance por Categoría',
            xaxis_title='Categoría',
            yaxis_title='Monto',
            barmode='group'
        )
        bar_div = plot(bar, output_type='div')


    # Categorías disponibles para el formulario
    categorias_disponibles = {
        'ingreso': [
            {'label': "Ingresos Laborales", 'options': ["Salario", "Freelance", "Comisiones", "Bonos", "Propinas"]},
            {'label': "Ingresos Pasivos", 'options': ["Inversiones", "Dividendos", "Intereses", "Alquiler", "Pensión"]},
            {'label': "Otros Ingresos", 'options': ["Subsidio", "Beca", "Ventas", "Herencia", "Premios"]}
        ],
        'gasto': [
            {'label': "Vivienda", 'options': ["Renta", "Servicios", "Internet", "Mantenimiento"]},
            {'label': "Alimentación", 'options': ["Supermercado", "Restaurantes"]},
            {'label': "Transporte", 'options': ["Gasolina", "Transporte", "Auto", "Seguro de auto"]},
            {'label': "Personales", 'options': ["Ropa", "Personal", "Salud", "Ocio", "Educacion"]},
            {'label': "Finanzas", 'options': ["Deudas", "Impuestos", "Donaciones"]},
            {'label': "Otros", 'options': ["Suscripciones", "Mascotas", "Regalos", "Viajes", "Tecnologia", "Ahorro", "Emergencias", "Honorarios"]}
        ]
    }

    return render_template(
        'inicio.html',
        transacciones=transacciones,
        years_available=years_available,
        months_available=months_available,
        ingresos=ingresos,
        gastos=gastos,
        balance=balance,
        pie_div=pie_div,
        bar_div=bar_div,
        categorias=categorias_disponibles,
        datetime=datetime
    )


# ----------------------------------------------Rutas se  transacciones ---------------------------------------------------------------
@app.route('/obtener_graficos_filtrados')
@login_required
def obtener_graficos_filtrados():
    year = request.args.get('year')
    month = request.args.get('month')
    
    query = Transaction.query.filter_by(user_id=current_user.id)
    
    if year:
        query = query.filter(db.extract('year', Transaction.date) == year)
        if month:
            query = query.filter(db.extract('month', Transaction.date) == month)
    
    transacciones = query.order_by(Transaction.date.desc()).all()
    
    # Calcular totales
    ingresos = sum(t.amount for t in transacciones if t.type == 'ingreso')
    gastos = sum(t.amount for t in transacciones if t.type == 'gasto')
    
    # Datos para gráfico de pastel
    pie_data = {
        'labels': ['Ingresos', 'Gastos'],
        'values': [ingresos, gastos],
        'colors': ['#28a745', '#dc3545']
    }
    
    # Datos para gráfico de barras por categoría
    categorias = {}
    for t in transacciones:
        if t.category not in categorias:
            categorias[t.category] = {'ingresos': 0, 'gastos': 0}
        if t.type == 'ingreso':
            categorias[t.category]['ingresos'] += t.amount
        else:
            categorias[t.category]['gastos'] += t.amount
    
    bar_data = {
        'categorias': list(categorias.keys()),
        'ingresos': [v['ingresos'] for v in categorias.values()],
        'gastos': [v['gastos'] for v in categorias.values()]
    }
    
    return jsonify({
        'pie_data': pie_data,
        'bar_data': bar_data
    })

@app.route('/eliminar_transaccion/<int:id>', methods=['DELETE'])
@login_required
def eliminar_transaccion(id):
    try:
        transaccion = db.session.get(Transaction, id)
        if not transaccion or transaccion.user_id != current_user.id:
            return jsonify({"error": "Transacción no encontrada"}), 404
            
        db.session.delete(transaccion)
        db.session.commit()
        return jsonify({"success": True})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'Error eliminando transacción: {str(e)}')
        return jsonify({"error": str(e)}), 500

@app.route('/analisis_transacciones', methods=['POST'])
@login_required
def analisis_transacciones():
    try:
        # Obtener todas las transacciones del usuario
        transacciones = Transaction.query.filter_by(user_id=current_user.id).all()
        
        if not transacciones:
            return jsonify({"error": "No hay transacciones para analizar"}), 400

        # Preparar datos para el análisis
        total_ingresos = sum(t.amount for t in transacciones if t.type == 'ingreso')
        total_gastos = sum(t.amount for t in transacciones if t.type == 'gasto')
        balance = total_ingresos - total_gastos
        
        # Obtener categorías con más gastos
        gastos_por_categoria = {}
        for t in transacciones:
            if t.type == 'gasto':
                gastos_por_categoria[t.category] = gastos_por_categoria.get(t.category, 0) + t.amount
        top_gastos = sorted(gastos_por_categoria.items(), key=lambda x: x[1], reverse=True)[:3]
        
        pregunta = f"Analiza el comportamiento financiero del usuario. "
        pregunta += f"Total ingresos: ${total_ingresos:.2f}, Total gastos: ${total_gastos:.2f}, Balance: ${balance:.2f}. "
        pregunta += f"Principales categorías de gasto: {', '.join([f'{cat} (${monto:.2f})' for cat, monto in top_gastos])}. "
        pregunta += "Proporciona un análisis conciso de máximo 200 palabras con recomendaciones prácticas para mejorar las finanzas personales."

        client = OpenAI(
            api_key="sk-f96903a695404895a9cc563a7ee3c4c5",
            base_url="https://api.deepseek.com"
        )

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "Eres un asesor financiero personal. Proporciona análisis útiles y recomendaciones prácticas en un tono profesional pero amigable."},
                {"role": "user", "content": pregunta}
            ],
            temperature=0.7,
            max_tokens=400
        )
        
        analisis = response.choices[0].message.content
        
        return jsonify({"analisis": analisis})
    
    except Exception as e:
        return jsonify({"error": f"Error al generar el análisis: {str(e)}"}), 500
    
@app.route('/obtener_transacciones_filtradas')
@login_required
def obtener_transacciones_filtradas():
    year = request.args.get('year')
    month = request.args.get('month')
    
    query = Transaction.query.filter_by(user_id=current_user.id)
    
    if year:
        query = query.filter(db.extract('year', Transaction.date) == year)
        if month:
            query = query.filter(db.extract('month', Transaction.date) == month)
    
    transacciones = query.order_by(Transaction.date.desc()).all()
    
    # Convertir a formato JSON
    transacciones_json = [{
        'id': t.id,
        'type': t.type,
        'category': t.category,
        'amount': float(t.amount),
        'date': t.date.isoformat(),
        'description': t.description or ''
    } for t in transacciones]
    
    return jsonify({
        'transacciones': transacciones_json
    })
#-----------------------------------------------------------------------------------------------------------------------

# Funciones de utilidad
def enviar_recomendacion(email, asunto, cuerpo):
    try:
        msg = Message(
            asunto,
            sender=app.config['MAIL_USERNAME'],
            recipients=[email]
        )
        msg.body = cuerpo
        mail.send(msg)
        return True
    except Exception as e:
        app.logger.error(f'Error enviando recomendación: {str(e)}')
        return False

def obtener_recomendacion_ia(pregunta):
    try:
        response = requests.post(
            'https://api.deepseek.com/chat/completions',
            headers={
                'Authorization': f'Bearer {DEEPSEEK_API_KEY}',
                'Content-Type': 'application/json',
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {
                        "role": "system", 
                        "content": "Eres un asesor financiero experto. Da recomendaciones cortas, prácticas y directas."
                    },
                    {"role": "user", "content": pregunta}
                ],
                "max_tokens": 150
            },
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        app.logger.error(f'Error obteniendo recomendación IA: {str(e)}')
        return f"Lo siento, no pude generar una recomendación en este momento. Error: {str(e)}"

@app.route('/enviar_alertas')
@login_required
def enviar_alertas():
    usuario_email = current_user.email
    revisar_y_enviar_alerta(usuario_email)
    flash('Se han revisado los indicadores y enviado alertas si fueron necesarias.')
    return redirect(url_for('inicio'))

def revisar_y_enviar_alerta(usuario_email):
    token = os.environ.get('BANXICO_TOKEN', 'tu_token_aqui')
    try:
        url = "https://www.banxico.org.mx/SieAPIRest/service/v1/series/SF43718/datos/oportuno"
        headers = {"Bmx-Token": token}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        valor = float(data['bmx']['series'][0]['datos'][0]['dato'])

        if valor > 20:
            pregunta = f"El tipo de cambio actual es {valor}. ¿Qué recomendaciones tienes para invertir o ahorrar en esta situación?"
            recomendacion = obtener_recomendacion_ia(pregunta)
            asunto = f"Recomendación Financiera - Tipo de cambio en {valor}"
            if enviar_recomendacion(usuario_email, asunto, recomendacion):
                app.logger.info(f'Alerta enviada a {usuario_email} por tipo de cambio alto')
            else:
                app.logger.warning(f'Error enviando alerta a {usuario_email}')

    except Exception as e:
        app.logger.error(f'Error revisando alertas: {str(e)}')

# Página de debug (solo para desarrollo)
@app.route('/debug/users')
def debug_users():
    if app.env != 'development':
        return "Acceso no permitido", 403
        
    users = User.query.all()
    return '<br>'.join([f"ID: {u.id}, Usuario: {u.username}, Email: {u.email}, Creado: {u.created_at}" for u in users])



# Crear tablas al iniciar
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)