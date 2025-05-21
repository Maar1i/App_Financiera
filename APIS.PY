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
    print(data.head())

tabla_precios("AAPL", "19/05/2025")



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
