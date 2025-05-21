import requests
import json
import pandas as pd
import yfinance as yf
from datetime import datetime

#-------------------------------------------------------------------------------------------------------------------------------------------------
# API_KEY de open router.ai
API_KEY_IA = "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"

#---------------------------------------------------------------------------------------------------------------------------------------------------
# response que da la página para poder hacer consultas a deepseek de manera gratuita.
response = requests.post(
  url="https://openrouter.ai/api/v1/chat/completions",
  headers={
    "Authorization": f"Bearer {API_KEY_IA}",
    "Content-Type": "application/json",
    "HTTP-Referer": "<YOUR_SITE_URL>", # Optional. Site URL for rankings on openrouter.ai.
    "X-Title": "<YOUR_SITE_NAME>", # Optional. Site title for rankings on openrouter.ai.
  },
  data=json.dumps({
    "model": "deepseek/deepseek-r1:free",
    "messages": [
      {
        "role": "user",
        "content": "hola"   # línea que manda el prompt a deepseek.
      }
    ],
    
  })
)

#-------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Un if, si el status code es de 200, dará la resouesta del promp, por otro lado si no es 200, mostrará un error con
# el número del error.

if response.status_code == 200:
    data = response.json()
    # Imprimir la respuesta del asistente
    print(data["choices"][0]["message"]["content"])
else:
    print(f"Error: {response.status_code}")
    print(response.text)



#--------------------API DE INVERSION------------------------------------------------------------------------------------------------
def tabla_precios(simbolo, fecha):
    
    fecha_inicial = datetime.strptime(fecha, "%d/%m/%Y").date()
    fecha_final = datetime.now().date()
    
    data = yf.download(simbolo, start= fecha_inicial, end= fecha_final)
    return data


#--------Funcion de la inversion con el paso del tiempo.--------------

def acciones(simbolo,fecha, inversion):

    precios = tabla_precios(simbolo, fecha) # data frame de el precio de la accion dependiendo de la empresa.
    fecha_final = datetime.now().date()    # Fecha del dia de hoy.

    try:
        precio_compra = precios.loc[datetime.strptime(fecha, "%d/%m/%Y").date(), 'Close']  # dara el precio del dia de hoy (si esta.)
    except KeyError:
        precio_compra = precios['Close'].iloc[0] # si no encuentra el dato de la fecha actual, dara el de la fecha mas reciente.

    acciones_compradas = inversion / precio_compra # formula para calcular el numero de acciones compradas con el precio de la accion en esa fecha.

    precios['Valor_inversion'] = precios['Close'] * acciones_compradas # crea una columna de la variacion del valor de la accion con el tiempo.
    return precios # Regresa el data frame

acciones("AAPL", "15/05/2024", 1000) #----Prueba


import plotly.graph_objects as go
import pandas as pd

# Ejecuta tu función para obtener el DataFrame
df = acciones("AAPL", "15/05/2024", 1000)

# El índice es la fecha, lo ponemos como columna y la renombramos para que coincida con tu ejemplo
df = df.reset_index().rename(columns={"Date": "date", "Valor_inversion": "valor_inversion_usd"})

# Asegúrate que la columna date sea datetime
df["date"] = pd.to_datetime(df["date"])

if not df.empty and "valor_inversion_usd" in df.columns:
    frames = []
    for i in range(2, len(df)):
        frames.append(go.Frame(
            data=[go.Scatter(
                x=df["date"][:i],
                y=df["valor_inversion_usd"][:i],
                mode="lines",
                line=dict(color="green", width=3)
            )],
            name=str(df["date"].iloc[i])
        ))

    fig = go.Figure(
        data=[go.Scatter(
            x=[df["date"].iloc[0], df["date"].iloc[1]],
            y=[df["valor_inversion_usd"].iloc[0], df["valor_inversion_usd"].iloc[1]],
            mode="lines",
            line=dict(color="green", width=3)
        )],
        layout=go.Layout(
            title="Evolución del valor de la inversión en Apple (AAPL)",
            xaxis=dict(title="Fecha", range=[df["date"].min(), df["date"].max()]),
            yaxis=dict(title="Valor en USD", range=[
                df["valor_inversion_usd"].min() * 0.95,
                df["valor_inversion_usd"].max() * 1.05
            ]),
            updatemenus=[dict(
                type="buttons",
                showactive=False,
                buttons=[
                    dict(label="Play",
                         method="animate",
                         args=[None, {
                             "frame": {"duration": 30, "redraw": True},
                             "fromcurrent": True,
                             "transition": {"duration": 0}
                         }]),
                    dict(label="Pause",
                         method="animate",
                         args=[[None], {
                             "frame": {"duration": 0, "redraw": False},
                             "mode": "immediate",
                             "transition": {"duration": 0}
                         }])
                ]
            )]
        ),
        frames=frames
    )

    fig.show()
else:
    print("No hay datos para graficar o falta la columna 'valor_inversion_usd'")










































































































#--------------------API DE CRYPTO------------------------------------------------------------------------------------------------
API_KEY_COINCAP = "837f7d007ff30e74547acd1bdc8d8c6e462f6b8f8b8528546f1c43357288ed95"

def obtener_historial_cripto(moneda: str, fecha_inicio: str, monto_invertido: float = None):
    try:
        fecha_inicio_dt = datetime.strptime(fecha_inicio, "%d/%m/%Y")
        start_ms = int(fecha_inicio_dt.timestamp() * 1000)
        end_ms = int(datetime.now().timestamp() * 1000)

        url = f"https://rest.coincap.io/v3/assets/{moneda}/history?interval=d1&start={start_ms}&end={end_ms}"
        headers = {
            "Authorization": f"Bearer {API_KEY_COINCAP}"
        }

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()["data"]
            df = pd.DataFrame(data)
            df["date"] = pd.to_datetime(df["date"]).dt.date
            df["priceUsd"] = df["priceUsd"].astype(float)
            df = df[df["date"] <= datetime.now().date()]

            if monto_invertido:
                precio_inicial = df.iloc[0]["priceUsd"]
                cantidad_comprada = monto_invertido / precio_inicial
                df["valor_inversion_usd"] = df["priceUsd"] * cantidad_comprada

            if "time" in df.columns:
                df.drop(columns=["time"], inplace=True)

            return df
        else:
            print(f"Error al consultar CoinCap API: {response.status_code}")
            print(response.text)
            return pd.DataFrame()
    except Exception as e:
        print("Error general:", str(e))
        return pd.DataFrame()

# Ejemplo de uso
df = obtener_historial_cripto("bitcoin", "01/05/2024", monto_invertido=1000)
print(df.head())
