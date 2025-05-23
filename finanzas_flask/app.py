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


app = Flask(__name__)
#app.secret_key = 'clave_secreta'

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'una-clave-secreta-muy-segura'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path, 'finanzas.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configuración correo
# Actualiza la configuración del mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'tu_correo@gmail.com'
app.config['MAIL_PASSWORD'] = 'tu_contraseña_de_app'  # No uses tu contraseña normal
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
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    accion = db.Column(db.String(10), nullable=False)  # Símbolo de la acción (AAPL, MSFT, etc.)
    tipo_operacion = db.Column(db.String(10), nullable=False)  # 'compra' o 'venta'
    cantidad = db.Column(db.Integer, nullable=False)
    precio = db.Column(db.Float, nullable=False)  # Precio por acción
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return redirect(url_for('dashboard'))  # O render_template("index.html")


@app.route('/indicadores')
@login_required
def indicadores():
    return render_template('indicadores.html')

@app.route('/acciones', methods=['GET', 'POST'])
@login_required
def acciones():
    if request.method == 'POST':
        try:
            accion = request.form.get('accion')
            tipo_operacion = request.form.get('tipo_operacion')
            cantidad = int(request.form.get('cantidad'))
            precio = float(request.form.get('precio'))
            
            nueva_operacion = Acciones(
                user_id=current_user.id,
                accion=accion,
                tipo_operacion=tipo_operacion,
                cantidad=cantidad,
                precio=precio,
                fecha=datetime.utcnow()
            )
            
            db.session.add(nueva_operacion)
            db.session.commit()
            flash('Operación registrada exitosamente!', 'success')
        
        except Exception as e:
            db.session.rollback()
            flash(f'Error al registrar operación: {str(e)}', 'danger')

    # Obtener operaciones del usuario
    transacciones = Acciones.query.filter_by(user_id=current_user.id)\
                               .order_by(Acciones.fecha.desc())\
                               .all()

    return render_template('acciones.html', transacciones=transacciones)

@app.route('/criptomonedas')
@login_required
def criptomonedas():
    return render_template('criptomonedas.html', show_blue_stripe=True)

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
                return redirect(next_page) if next_page else redirect(url_for('dashboard'))
            else:
                flash('Contraseña incorrecta.')
        else:
            flash('Usuario no encontrado.')

    return render_template('login.html')


from flask import Flask, render_template, redirect, url_for, flash, request
from random import randint

# Diccionario temporal para almacenar códigos
reset_codes = {}

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Genera código de 6 dígitos
            code = str(randint(100000, 999999))
            reset_codes[email] = {
                'code': code,
                'user_id': user.id
            }
            return render_template('forgot_password.html', 
                                code=code, 
                                email=email,
                                show_code=True)
        else:
            flash('Correo no registrado', 'danger')
    
    return render_template('forgot_password.html', show_code=False)

@app.route('/reset_password', methods=['POST'])
def reset_password():
    email = request.form.get('email')
    code = request.form.get('code')
    new_password = request.form.get('password')
    
    if email in reset_codes and reset_codes[email]['code'] == code:
        user = User.query.get(reset_codes[email]['user_id'])
        user.password = generate_password_hash(new_password)
        db.session.commit()
        flash('Contraseña actualizada. ¡Inicia sesión!', 'success')
        return redirect(url_for('login'))
    else:
        flash('Código incorrecto', 'danger')
        return redirect(url_for('forgot_password'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión correctamente.')
    return redirect(url_for('login'))


DEEPSEEK_API_KEY = "sk-f96903a695404895a9cc563a7ee3c4c5"

@app.route('/asistente', methods=['GET', 'POST'])
@login_required
def asistente():
    if request.method == 'GET':
        return render_template("asistente.html")
    
    # Obtener datos según el tipo de solicitud
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    try:
        if is_ajax:
            data = request.get_json()
            pregunta = data.get('pregunta', '').strip()
        else:
            pregunta = request.form.get('pregunta', '').strip()
        
        if not pregunta:
            return jsonify({'error': 'La pregunta no puede estar vacía'}), 400
            
        # Llamada a la API de DeepSeek
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
        
        response = requests.post(
            'https://api.deepseek.com/chat/completions',
            headers=headers,
            json=payload,
            timeout=20
        )
        response.raise_for_status()
        
        respuesta = response.json()["choices"][0]["message"]["content"]
        
        return jsonify({
            'success': True,
            'respuesta': respuesta
        })
        
    except Exception as e:
        app.logger.error(f'Error en asistente: {str(e)}')
        return jsonify({
            'error': 'Error al procesar tu pregunta',
            'details': str(e)
        }), 500
    

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    # Obtener transacciones del usuario (para GET y POST)
    transacciones = Transaction.query.filter_by(user_id=current_user.id)\
                                   .order_by(Transaction.date.desc())\
                                   .all()

    # Calcular totales
    ingresos = sum(t.amount for t in transacciones if t.type == 'ingreso')
    gastos = sum(t.amount for t in transacciones if t.type == 'gasto')
    balance = ingresos - gastos

    # Gráfico de pastel
    pie = go.Figure(data=[go.Pie(
        labels=['Ingresos', 'Gastos'], 
        values=[ingresos, gastos],
        marker_colors=['#28a745', '#dc3545']
    )])
    pie.update_layout(title_text='Distribución de Ingresos y Gastos')
    pie_div = plot(pie, output_type='div')

    # Gráfico de barras por categoría
    categorias = {}
    for t in transacciones:
        if t.category not in categorias:
            categorias[t.category] = {'ingresos': 0, 'gastos': 0}
        if t.type == 'ingreso':
            categorias[t.category]['ingresos'] += t.amount
        else:
            categorias[t.category]['gastos'] += t.amount

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

    # Manejo de solicitudes POST (añadir nuevas transacciones)
    if request.method == 'POST':
        try:
            tipo = request.form.get('type')
            categoria = request.form.get('category')
            monto = float(request.form.get('amount', 0))
            descripcion = request.form.get('description', '').strip()

            if not tipo or not categoria or monto <= 0:
                flash('Por favor completa todos los campos correctamente.')
                return redirect(url_for('dashboard'))

            nueva_transaccion = Transaction(
                user_id=current_user.id,
                type=tipo,
                category=categoria,
                amount=monto,
                description=descripcion
            )
            
            db.session.add(nueva_transaccion)
            db.session.commit()
            flash('Transacción registrada exitosamente!')
            
            # Actualizar los datos después de añadir nueva transacción
            return redirect(url_for('dashboard'))

        except ValueError:
            flash('El monto debe ser un número válido.')
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Error añadiendo transacción: {str(e)}')
            flash('Ocurrió un error al registrar la transacción.')

    return render_template(
        'dashboard.html',
        transacciones=transacciones,
        ingresos=ingresos,
        gastos=gastos,
        balance=balance,
        pie_div=pie_div,
        bar_div=bar_div
    )

               



    
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
    return redirect(url_for('dashboard'))

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
