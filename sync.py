import json
from icalendar import Calendar as ICALCalendar
import recurring_ical_events
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build
import requests
import os

# === CONFIGURAÇÕES ===
SCOPES = [
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/calendar.readonly'
]

TEAMS_ICS_URL = 'https://outlook.office365.com/owa/calendar/471f9c9338764ae3bf8839a02fdfcad1@casasbahia.com.br/af786ccf75ac4f05a3909066eb68ad4d1541582488987527822/calendar.ics'
CALENDAR_NAME = 'Trabalho'
CREDENTIALS_PATH = 'credentials.json'

# === FUNÇÕES ===

def get_calendar_service():
    credentials = service_account.Credentials.from_service_account_file(
        CREDENTIALS_PATH, scopes=SCOPES
    )
    return build('calendar', 'v3', credentials=credentials)

def get_calendar_id(service, calendar_name):
    calendar_list = service.calendarList().list().execute()
    for calendar in calendar_list['items']:
        if calendar['summary'] == calendar_name:
            return calendar['id']
    return None

def get_teams_events():
    resp = requests.get(TEAMS_ICS_URL)
    resp.raise_for_status()
    ical = ICALCalendar.from_ical(resp.text)

    hoje = datetime.now()
    segunda = hoje - timedelta(days=hoje.weekday())
    inicio_periodo = segunda.replace(hour=7, minute=0, second=0, microsecond=0)
    fim_periodo = (segunda + timedelta(days=4)).replace(hour=18, minute=0, second=0, microsecond=0)

    events = recurring_ical_events.of(ical).between(inicio_periodo, fim_periodo)

    eventos_teams = []
    for e in events:
        dtstart = e.get('DTSTART').dt
        dtend = e.get('DTEND').dt
        if not isinstance(dtstart, datetime):
            dtstart = datetime.combine(dtstart, datetime.min.time())
        if not isinstance(dtend, datetime):
            dtend = datetime.combine(dtend, datetime.min.time())

        eventos_teams.append({
            'titulo': str(e.get('SUMMARY')),
            'inicio': dtstart.replace(tzinfo=None),
            'fim': dtend.replace(tzinfo=None),
        })

    return eventos_teams, inicio_periodo, fim_periodo

def get_google_events(service, inicio_periodo, fim_periodo, calendar_id):
    eventos_google = []

    events_result = service.events().list(
        calendarId=calendar_id,
        timeMin=inicio_periodo.isoformat() + 'Z',
        timeMax=fim_periodo.isoformat() + 'Z',
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    for event in events_result.get('items', []):
        start = event['start'].get('dateTime', event['start'].get('date'))
        end = event['end'].get('dateTime', event['end'].get('date'))

        inicio = datetime.fromisoformat(start.replace('Z', '')).replace(tzinfo=None)
        fim = datetime.fromisoformat(end.replace('Z', '')).replace(tzinfo=None)

        eventos_google.append({
            'titulo': event['summary'],
            'inicio': inicio,
            'fim': fim
        })

    return eventos_google

def criar_evento(service, evento, calendar_id):
    event = {
        'summary': evento['titulo'],
        'start': {'dateTime': evento['inicio'].isoformat(), 'timeZone': 'America/Sao_Paulo'},
        'end': {'dateTime': evento['fim'].isoformat(), 'timeZone': 'America/Sao_Paulo'},
    }

    try:
        service.events().insert(calendarId=calendar_id, body=event).execute()
        print(f'Evento criado: {evento["titulo"]}')
    except Exception as e:
        print(f'Erro ao criar evento: {e}')

def evento_existe(evento_teams, eventos_google):
    for evento_google in eventos_google:
        if (evento_teams['titulo'] == evento_google['titulo'] and
            abs((evento_teams['inicio'] - evento_google['inicio']).total_seconds()) < 60):
            return True
    return False

def main():
    print("🔐 Iniciando sincronização com autenticação via Service Account...")

    service = get_calendar_service()
    calendar_id = get_calendar_id(service, CALENDAR_NAME)
    if not calendar_id:
        print(f"Agenda '{CALENDAR_NAME}' não encontrada.")
        return

    eventos_teams, inicio, fim = get_teams_events()
    eventos_google = get_google_events(service, inicio, fim, calendar_id)

    for evento in eventos_teams:
        if evento['titulo'].startswith('Cancelado:'):
            print(f"Pulando evento cancelado: {evento['titulo']}")
            continue
        if not evento_existe(evento, eventos_google):
            criar_evento(service, evento, calendar_id)
        else:
            print(f"Evento já existe: {evento['titulo']}")

if __name__ == '__main__':
    main()