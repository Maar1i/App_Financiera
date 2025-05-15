from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
import requests
from plotly.offline import plot
import plotly.graph_objs as go
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'clave-secreta'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///finanzas.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configuración correo
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME='tu_email@gmail.com',  # Cambia a tu correo
    MAIL_PASSWORD='tu_contraseña_o_app_password'  # Mejor usa contraseña de aplicación
)

# Inicialización extensiones
db = SQLAlchemy(app)
mail = Mail(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


# Modelos
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    email = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(256), nullable=False)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    type = db.Column(db.String(50))           # Agregado para tipo (ingreso/gasto)
    category = db.Column(db.String(100))      # Agregado para categoría
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200))
    date = db.Column(db.DateTime)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Rutas

@app.route('/')
def home():
    return render_template('home.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user:
            flash('El nombre de usuario ya existe.')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

    
        # Enviar correo de bienvenida
        msg = Message('Bienvenido a tu App de Finanzas',
                      sender=app.config['MAIL_USERNAME'],
                      recipients=[email])
        msg.body = f"Hola {username}, gracias por registrarte en nuestra app."
        try:
            mail.send(msg)
        except Exception:
            flash('Registro exitoso, pero fallo el envío de correo.')

        flash('Registro exitoso. Ya puedes iniciar sesión.')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Credenciales incorrectas.')
            return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    if request.method == 'POST':
        tipo = request.form['type']
        categoria = request.form['category']
        monto = float(request.form['amount'])
        nueva = Transaction(user_id=current_user.id, type=tipo, category=categoria, amount=monto)
        db.session.add(nueva)
        db.session.commit()
        flash('Transacción registrada exitosamente.')

    transacciones = Transaction.query.filter_by(user_id=current_user.id).all()

    ingresos = sum(t.amount for t in transacciones if t.type == 'ingreso')
    gastos = sum(t.amount for t in transacciones if t.type == 'gasto')

    pie = go.Figure(data=[go.Pie(labels=['Ingresos', 'Gastos'], values=[ingresos, gastos])])
    pie_div = plot(pie, output_type='div')

    categorias = {}
    for t in transacciones:
        if t.category not in categorias:
            categorias[t.category] = 0
        categorias[t.category] += t.amount if t.type == 'gasto' else -t.amount

    bar = go.Figure([go.Bar(x=list(categorias.keys()), y=list(categorias.values()))])
    bar.update_layout(title='Balance por categoría', xaxis_title='Categoría', yaxis_title='Monto')
    bar_div = plot(bar, output_type='div')

    return render_template('dashboard.html', transacciones=transacciones, pie_div=pie_div, bar_div=bar_div)


@app.route('/indicadores')
@login_required
def indicadores():
    token = "TU_TOKEN_AQUI"
    url = "https://www.banxico.org.mx/SieAPIRest/service/v1/series/SF43718/datos/oportuno"
    headers = {"Bmx-Token": token}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        valor = data['bmx']['series'][0]['datos'][0]['dato']
        fecha = data['bmx']['series'][0]['datos'][0]['fecha']
    else:
        valor = "Error"
        fecha = "Error"

    return render_template('indicadores.html', valor=valor, fecha=fecha)


DEEPSEEK_API_KEY = "TU_API_KEY_DEEPSEEK"

@app.route('/asistente', methods=['GET', 'POST'])
@login_required
def asistente():
    respuesta_ia = ""
    if request.method == 'POST':
        pregunta = request.form['pregunta']

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
                        {"role": "system", "content": "Eres un asesor financiero profesional. Da respuestas claras y útiles sobre finanzas personales, inversiones y ahorro."},
                        {"role": "user", "content": pregunta}
                    ]
                }
            )
            data = response.json()
            respuesta_ia = data["choices"][0]["message"]["content"]

        except Exception as e:
            respuesta_ia = f"Ocurrió un error: {e}"

    return render_template("asistente.html", respuesta=respuesta_ia)


def enviar_recomendacion(email, asunto, cuerpo):
    msg = Message(asunto,
                  sender=app.config['MAIL_USERNAME'],
                  recipients=[email])
    msg.body = cuerpo
    mail.send(msg)


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
                    {"role": "system", "content": "Eres un asesor financiero experto. Da recomendaciones cortas y prácticas."},
                    {"role": "user", "content": pregunta}
                ]
            }
        )
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Error al obtener recomendación: {e}"


def revisar_y_enviar_alerta(usuario_email):
    token = "TU_TOKEN_BANXICO"
    url = "https://www.banxico.org.mx/SieAPIRest/service/v1/series/SF43718/datos/oportuno"
    headers = {"Bmx-Token": token}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        valor = float(data['bmx']['series'][0]['datos'][0]['dato'])

        if valor > 20:
            pregunta = f"¿Es buen momento para invertir con tipo de cambio actual {valor}?"
            recomendacion = obtener_recomendacion_ia(pregunta)
            asunto = "Recomendación Financiera - Buen momento para invertir"
            enviar_recomendacion(usuario_email, asunto, recomendacion)


@app.route('/enviar_alertas')
@login_required
def enviar_alertas():
    usuario_email = current_user.email
    revisar_y_enviar_alerta(usuario_email)
    return "Alerta enviada si se cumplió la condición"


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
