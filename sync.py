import os, json, requests
from datetime import datetime, timedelta
from icalendar import Calendar as ICALCalendar
import recurring_ical_events
from google.oauth2 import service_account
from googleapiclient.discovery import build

# ——————————— CONFIG ———————————
SCOPES = ['https://www.googleapis.com/auth/calendar']
TEAMS_ICS_URL    = os.environ['TEAMS_ICS_URL']
CALENDAR_ID      = os.environ['GOOGLE_CALENDAR_ID']
CREDENTIALS_JSON = os.environ['GOOGLE_CREDENTIALS'] 

# ————————— AUTENTICAÇÃO —————————
def get_calendar_service():
    """Initialize the Calendar API using Service Account"""
    try:
        credentials_json = os.environ.get('GOOGLE_CREDENTIALS')
        if not credentials_json:
            raise ValueError("GOOGLE_CREDENTIALS environment variable not found")
            
        credentials_info = json.loads(credentials_json)
        credentials = service_account.Credentials.from_service_account_info(
            credentials_info,
            scopes=SCOPES
        )
        return build('calendar', 'v3', credentials=credentials)
    except Exception as e:
        print(f"❌ Erro ao autenticar com Service Account: {e}")
        raise

# ————— GET TEAMS EVENTS —————————
def get_teams_events():
    resp = requests.get(TEAMS_ICS_URL); resp.raise_for_status()
    ical = ICALCalendar.from_ical(resp.text)
    hoje   = datetime.now()
    seg    = hoje - timedelta(days=hoje.weekday())
    start  = seg.replace(hour=7,  minute=0)
    end    = (seg + timedelta(days=4)).replace(hour=18, minute=0)
    evs = recurring_ical_events.of(ical).between(start, end)
    out = []
    for e in evs:
        s = e.get('DTSTART').dt; f = e.get('DTEND').dt
        if not isinstance(s, datetime): s = datetime.combine(s, datetime.min.time())
        if not isinstance(f, datetime): f = datetime.combine(f, datetime.min.time())
        out.append({'titulo':str(e.get('SUMMARY')), 'inicio':s, 'fim':f})
    return out, start, end

# ————— LIST GOOGLE EVENTS —————————
def get_google_events(svc, start, end):
    evs = svc.events().list(
        calendarId=CALENDAR_ID,
        timeMin = start.isoformat()+'Z',
        timeMax = end.isoformat()+'Z',
        singleEvents=True, orderBy='startTime'
    ).execute().get('items',[])
    out = []
    for ev in evs:
        # Handle both date and dateTime formats safely
        s = ev['start'].get('dateTime') or ev['start'].get('date')
        f = ev['end'].get('dateTime') or ev['end'].get('date')
        
        # Parse dates consistently
        s = datetime.fromisoformat(s.replace('Z',''))
        f = datetime.fromisoformat(f.replace('Z',''))
        
        out.append({'titulo':ev.get('summary'), 'inicio':s, 'fim':f})
    return out

# ————— CRIAÇÃO —————————
def criar_evento(svc, ev):
    body = {
      'summary': ev['titulo'],
      'start': {'dateTime': ev['inicio'].isoformat(), 'timeZone':'America/Sao_Paulo'},
      'end':   {'dateTime': ev['fim'].isoformat(),    'timeZone':'America/Sao_Paulo'},
    }
    svc.events().insert(calendarId=CALENDAR_ID, body=body).execute()
    print("Criado:", ev['titulo'])

def get_original_title(canceled_title):
    """Extrai o título original de um evento cancelado"""
    if canceled_title.startswith('Cancelado:'):
        return canceled_title.replace('Cancelado:', '').strip()
    return None

def deletar_evento(svc, titulo, inicio):
    """Procura e deleta um evento específico"""
    try:
        # Busca eventos num intervalo de 1 hora
        start = inicio - timedelta(hours=1)
        end = inicio + timedelta(hours=1)
        
        events = svc.events().list(
            calendarId=CALENDAR_ID,
            timeMin=start.isoformat() + 'Z',
            timeMax=end.isoformat() + 'Z',
            singleEvents=True
        ).execute().get('items', [])
        
        for event in events:
            event_start = datetime.fromisoformat(
                event['start'].get('dateTime', event['start'].get('date')).replace('Z','')
            )
            if (event['summary'] == titulo and 
                abs((inicio - event_start).total_seconds()) < 3600):
                svc.events().delete(
                    calendarId=CALENDAR_ID,
                    eventId=event['id']
                ).execute()
                print(f"Removido evento cancelado: {titulo}")
                return True
    except Exception as e:
        print(f"Erro ao deletar evento: {e}")
    return False

# ————— MAIN —————————
def main():
    svc = get_calendar_service()
    teams, start, end = get_teams_events()
    google = get_google_events(svc, start, end)

    for ev in teams:
        # Ignora eventos DTV
        if ev['titulo'].startswith('DTV'):
            print("Ignorando evento DTV:", ev['titulo'])
            continue
            
        # Trata eventos cancelados
        original_title = get_original_title(ev['titulo'])
        if original_title:
            deletar_evento(svc, original_title, ev['inicio'])
            continue
            
        # Cria eventos normais
        if not any(abs((ev['inicio']-g['inicio']).total_seconds())<60 
                  and ev['titulo']==g['titulo'] for g in google):
            criar_evento(svc, ev)
        else:
            print("Já existe:", ev['titulo'])

if __name__=='__main__':
    main()
