from __future__ import print_function
import datetime
import os.path
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle

# Escopo para leitura e escrita dos eventos
SCOPES = ['https://www.googleapis.com/auth/calendar.events']

def get_calendar_service():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    return build('calendar', 'v3', credentials=creds)

def criar_evento(service, start_time, end_time, summary="Evento de Teste"):
    try:
        event = {
            'summary': summary,
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'America/Sao_Paulo',
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'America/Sao_Paulo',
            },
        }

        event = service.events().insert(calendarId='primary', body=event).execute()
        print(f'Evento criado: {event.get("htmlLink")}')
    except Exception as e:
        print(f'Erro ao criar evento: {e}')

def main():
    service = get_calendar_service()
    
    # Define horário do evento (hoje às 20h, duração 1 hora)
    hoje = datetime.datetime.now()
    inicio = hoje.replace(hour=20, minute=0, second=0, microsecond=0)
    fim = inicio + datetime.timedelta(hours=1)
    
    criar_evento(service, inicio, fim)

if __name__ == '__main__':
    main()
