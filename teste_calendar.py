from __future__ import print_function
import datetime
import os.path
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Se preferir autenticação interativa (com navegador), ative este bloco:
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle

# Escopo de leitura dos eventos
SCOPES = ['https://www.googleapis.com/auth/calendar.events']

# Função para autenticar e obter o serviço do Google Calendar
def get_calendar_service():
    creds = None

    # Usa token salvo, se existir
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    # Se não houver token válido, faz login e salva novo token
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('calendar', 'v3', credentials=creds)
    return service

# Define início e fim da semana (segunda 7h até sexta 18h)
hoje = datetime.datetime.now()
segunda = hoje - datetime.timedelta(days=hoje.weekday())
inicio = segunda.replace(hour=7, minute=0, second=0, microsecond=0)
fim = (segunda + datetime.timedelta(days=4)).replace(hour=18, minute=0, second=0, microsecond=0)

# Converte para RFC3339 (formato da API do Google)
time_min = inicio.isoformat() + 'Z'
time_max = fim.isoformat() + 'Z'

# Puxa os eventos
service = get_calendar_service()
events_result = service.events().list(
    calendarId='primary', timeMin=time_min, timeMax=time_max,
    singleEvents=True, orderBy='startTime'
).execute()
events = events_result.get('items', [])

print(f"Eventos entre {inicio} e {fim}:\n")

if not events:
    print("Nenhum evento encontrado.")
for event in events:
    start = event['start'].get('dateTime', event['start'].get('date'))
    end = event['end'].get('dateTime', event['end'].get('date'))
    print(f"Título:  {event['summary']}")
    print(f"Início:  {start}")
    print(f"Término: {end}")
    print("-" * 40)
