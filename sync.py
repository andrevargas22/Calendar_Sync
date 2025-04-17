import requests
from icalendar import Calendar as ICALCalendar
import recurring_ical_events
from datetime import datetime, timedelta
import os.path
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle

# Configurações
SCOPES = [
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/calendar.readonly'
]

TEAMS_ICS_URL = 'https://outlook.office365.com/owa/calendar/471f9c9338764ae3bf8839a02fdfcad1@casasbahia.com.br/af786ccf75ac4f05a3909066eb68ad4d1541582488987527822/calendar.ics'
CALENDAR_NAME = 'Trabalho'

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
            
        dtstart = dtstart.replace(tzinfo=None)
        dtend = dtend.replace(tzinfo=None)
        
        eventos_teams.append({
            'titulo': str(e.get('SUMMARY')),
            'inicio': dtstart,
            'fim': dtend
        })
    
    return eventos_teams, inicio_periodo, fim_periodo

def get_google_events(service, inicio_periodo, fim_periodo):
    eventos_google = []
    
    calendar_id = get_calendar_id(service, CALENDAR_NAME)
    if not calendar_id:
        return eventos_google
    
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
        # Remove timezone info after parsing
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
        'start': {
            'dateTime': evento['inicio'].isoformat(),
            'timeZone': 'America/Sao_Paulo',
        },
        'end': {
            'dateTime': evento['fim'].isoformat(),
            'timeZone': 'America/Sao_Paulo',
        },
    }
    
    try:
        event = service.events().insert(calendarId=calendar_id, body=event).execute()
        print(f'Evento criado!')
    except Exception as e:
        print(f'Erro ao criar evento: {e}')

def evento_existe(evento_teams, eventos_google):
    for evento_google in eventos_google:
        if (evento_teams['titulo'] == evento_google['titulo'] and
            abs((evento_teams['inicio'] - evento_google['inicio']).total_seconds()) < 60):
            return True
    return False

def get_original_title(canceled_title):
    """Extrai o título original de um evento cancelado"""
    if canceled_title.startswith('Cancelado:'):
        return canceled_title.replace('Cancelado:', '').strip()
    return None

def encontrar_e_deletar_evento(service, calendar_id, titulo, inicio):
    """Procura e deleta um evento específico"""
    events_result = service.events().list(
        calendarId=calendar_id,
        timeMin=(inicio - timedelta(hours=1)).isoformat() + 'Z',
        timeMax=(inicio + timedelta(hours=1)).isoformat() + 'Z',
        singleEvents=True
    ).execute()
    
    for event in events_result.get('items', []):
        event_start = datetime.fromisoformat(event['start'].get('dateTime', event['start'].get('date')).replace('Z', ''))
        if (event['summary'] == titulo and 
            abs((inicio - event_start).total_seconds()) < 3600):  # 1 hour tolerance
            try:
                service.events().delete(calendarId=calendar_id, eventId=event['id']).execute()
                print(f'Evento cancelado removido: {titulo}')
                return True
            except Exception as e:
                print(f'Erro ao deletar evento: {e}')
                return False
    return False

def main():
    # Obtém eventos do Teams
    eventos_teams, inicio_periodo, fim_periodo = get_teams_events()
    
    # Conecta ao Google Calendar
    service = get_calendar_service()
    
    # Obtém ID da agenda específica
    calendar_id = get_calendar_id(service, CALENDAR_NAME)
    if not calendar_id:
        print(f"Agenda '{CALENDAR_NAME}' não encontrada!")
        return
    
    # Obtém eventos do Google Calendar
    eventos_google = get_google_events(service, inicio_periodo, fim_periodo)
    
    # Sincroniza eventos
    for evento_teams in eventos_teams:
        if evento_teams['titulo'].startswith('DTV'):
            print(f"Pulando evento DTV: {evento_teams['titulo']}")
            continue
            
        # Verifica se é um evento cancelado
        titulo_original = get_original_title(evento_teams['titulo'])
        if titulo_original:
            print(f"Procurando evento cancelado: {titulo_original}")
            encontrar_e_deletar_evento(service, calendar_id, titulo_original, evento_teams['inicio'])
            continue
            
        if not evento_existe(evento_teams, eventos_google):
            print(f"Criando novo evento: {evento_teams['titulo']}")
            criar_evento(service, evento_teams, calendar_id)
        else:
            print(f"Evento já existe: {evento_teams['titulo']}")

if __name__ == '__main__':
    main()
