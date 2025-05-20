import requests
import json
import pandas as pd
#-------------------------------------------------------------------------------------------------------------------------------------------------
# API_KEY de open router.ai
API_KEY = "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"

#---------------------------------------------------------------------------------------------------------------------------------------------------
# response que da la página para poder hacer consultas a deepseek de manera gratuita.
response = requests.post(
  url="https://openrouter.ai/api/v1/chat/completions",
  headers={
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "HTTP-Referer": "<YOUR_SITE_URL>", # Optional. Site URL for rankings on openrouter.ai.
    "X-Title": "<YOUR_SITE_NAME>", # Optional. Site title for rankings on openrouter.ai.
  },
  data=json.dumps({
    "model": "deepseek/deepseek-r1:free",
    "messages": [
      {
        "role": "user",
        "content": "Explicame el interes compuesto como niño pequeño."   # línea que manda el prompt a deepseek.
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