import os, json, requests, csv
from datetime import datetime, timedelta
from icalendar import Calendar as ICALCalendar
import recurring_ical_events
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build

# ——————————— CONFIG ———————————
TEAMS_ICS_URL = os.environ['TEAMS_ICS_URL']
CACHE_FILE = 'events_cache.csv'
SCOPES = ['https://www.googleapis.com/auth/calendar']
CALENDAR_ID = os.environ.get('GOOGLE_CALENDAR_ID')
CREDENTIALS_JSON = os.environ.get('GOOGLE_CREDENTIALS')


# ————————— FUNCTIONS —————————
def get_teams_events():
    """Fetch events from Teams calendar for current and next week"""
    resp = requests.get(TEAMS_ICS_URL)
    resp.raise_for_status()
    ical = ICALCalendar.from_ical(resp.text)
    
    hoje = datetime.now()
    seg_atual = hoje - timedelta(days=hoje.weekday())
    
    # Define período para duas semanas
    start = seg_atual.replace(hour=7, minute=0, second=0, microsecond=0)
    end = (seg_atual + timedelta(days=11)).replace(hour=18, minute=0, second=0, microsecond=0)
    
    print(f"📅 From: {start.strftime('%d/%m')} | To: {end.strftime('%d/%m')}")
    events = recurring_ical_events.of(ical).between(start, end)
    out = []
    
    for e in events:
        s = e.get('DTSTART').dt
        f = e.get('DTEND').dt
        if not isinstance(s, datetime): s = datetime.combine(s, datetime.min.time())
        if not isinstance(f, datetime): f = datetime.combine(f, datetime.min.time())
        out.append({
            'titulo': str(e.get('SUMMARY')),
            'inicio': s.replace(tzinfo=None),
            'fim': f.replace(tzinfo=None)
        })
    
    return out, start, end

def load_event_cache():
    """Load cached events from CSV file."""
    cache = set()
    if Path(CACHE_FILE).exists():
        with open(CACHE_FILE, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                cache.add((
                    row['titulo'],
                    row['inicio'],
                    row['fim']
                ))
    return cache

def append_events_to_cache(new_events, cached_set):
    """Append new events to cache file if not already present. Returns list of new events added."""
    file_exists = Path(CACHE_FILE).exists()
    added = []
    with open(CACHE_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['titulo', 'inicio', 'fim'])
        if not file_exists:
            writer.writeheader()
        for event in new_events:
            key = (
                event['titulo'],
                event['inicio'].isoformat(),
                event['fim'].isoformat()
            )
            if key not in cached_set:
                writer.writerow({
                    'titulo': event['titulo'],
                    'inicio': event['inicio'].isoformat(),
                    'fim': event['fim'].isoformat()
                })
                cached_set.add(key)
                added.append(event)
    return added

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

def get_google_events(svc, start, end):
    """Fetch events from Google Calendar in the given period with extended end date"""
    extended_end = end + timedelta(days=1)
    evs = svc.events().list(
        calendarId=CALENDAR_ID,
        timeMin=start.isoformat()+'Z',
        timeMax=extended_end.isoformat()+'Z',
        singleEvents=True, 
        orderBy='startTime',
        maxResults=2500
    ).execute().get('items',[])
    out = []
    for ev in evs:
        s = ev['start'].get('dateTime') or ev['start'].get('date')
        f = ev['end'].get('dateTime') or ev['end'].get('date')
        s = datetime.fromisoformat(s.replace('Z',''))
        f = datetime.fromisoformat(f.replace('Z',''))
        if s.tzinfo is not None:
            s = s.astimezone().replace(tzinfo=None)
        if f.tzinfo is not None:
            f = f.astimezone().replace(tzinfo=None)
        out.append({'titulo':ev.get('summary'), 'inicio':s, 'fim':f})
    return out

def criar_evento_google(svc, ev):
    """Create an event in Google Calendar."""
    body = {
        'summary': ev['titulo'],
        'start': {'dateTime': ev['inicio'], 'timeZone': 'America/Sao_Paulo'},
        'end':   {'dateTime': ev['fim'],    'timeZone': 'America/Sao_Paulo'},
    }
    svc.events().insert(calendarId=CALENDAR_ID, body=body).execute()
    print(f"Created in Google Calendar: {ev['titulo']} ({ev['inicio']} - {ev['fim']})")

def parse_datetime(dtstr):
    """Improved parsing of datetime strings to ensure consistent format."""
    # Remove any timezone information and standardize format
    if isinstance(dtstr, str):
        # Replace T with space for consistent formatting
        dtstr = dtstr.replace('T', ' ')
        
        # Handle timezone information
        if '+' in dtstr:
            dtstr = dtstr.split('+')[0]
        elif '-' in dtstr[11:]:  # Only check for timezone in the time part
            dtstr = dtstr[:19]  # Keep only YYYY-MM-DD HH:MM:SS part
            
        # Parse the datetime
        dt = datetime.fromisoformat(dtstr.strip())
    else:
        # If already a datetime object
        dt = dtstr
        
    # Ensure no timezone info and no microseconds
    if dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)
    
    # Remove microseconds to ensure consistent comparison
    return dt.replace(microsecond=0)

def remover_evento_google_by_id(svc, event_id, event_title, event_start, event_end):
    """Remove um evento do Google Calendar pelo ID."""
    try:
        svc.events().delete(
            calendarId=CALENDAR_ID,
            eventId=event_id
        ).execute()
        print(f"Deleted event from Google Calendar: {event_title} ({event_start} - {event_end})")
        return True
    except Exception as e:
        print(f"Error deleting event {event_title}: {e}")
        return False

def buscar_e_deletar_cancelados(svc):
    """Remove todos os eventos 'Cancelado:' e, se houver, também o par original. Remove ambos do cache também."""
    now = datetime.now()
    start_search = now - timedelta(days=30)
    end_search = now + timedelta(days=30)
    events = svc.events().list(
        calendarId=CALENDAR_ID,
        timeMin=start_search.isoformat()+'Z',
        timeMax=end_search.isoformat()+'Z',
        singleEvents=True,
        maxResults=2500
    ).execute().get('items', [])
    # Index by (title, start, end)
    event_map = {}
    for ev in events:
        title = ev.get('summary', '')
        s = ev['start'].get('dateTime') or ev['start'].get('date')
        f = ev['end'].get('dateTime') or ev['end'].get('date')
        s_dt = parse_datetime(s)
        f_dt = parse_datetime(f)
        event_map.setdefault((title, s_dt, f_dt), []).append(ev)

    to_delete = set()
    cache_to_remove = set()
    for (title, s_dt, f_dt), ev_list in event_map.items():
        if title.startswith("Cancelado:"):
            # Sempre deleta o evento cancelado
            to_delete.add(ev_list[0]['id'])
            cache_to_remove.add((title, s_dt.isoformat(sep='T'), f_dt.isoformat(sep='T')))
            original_title = title.replace("Cancelado:", "").strip()
            original_key = (original_title, s_dt, f_dt)
            if original_key in event_map:
                to_delete.add(event_map[original_key][0]['id'])
                cache_to_remove.add((original_title, s_dt.isoformat(sep='T'), f_dt.isoformat(sep='T')))
                print(f"Found cancel pair, will delete both: '{title}' and '{original_title}' at {s_dt}")
            else:
                print(f"Deleting cancelado event (no pair found): '{title}' at {s_dt}")

    for event_id in to_delete:
        for ev in events:
            if ev['id'] == event_id:
                event_title = ev.get('summary', '')
                event_start = ev['start'].get('dateTime') or ev['start'].get('date')
                event_end = ev['end'].get('dateTime') or ev['end'].get('date')
                remover_evento_google_by_id(svc, event_id, event_title, event_start, event_end)
                break

    # Remover do cache
    if cache_to_remove:
        cache = set()
        if Path(CACHE_FILE).exists():
            with open(CACHE_FILE, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    cache.add((row['titulo'], row['inicio'], row['fim']))
        # Remove os eventos marcados
        cache = {item for item in cache if item not in cache_to_remove}
        with open(CACHE_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['titulo', 'inicio', 'fim'])
            writer.writeheader()
            for titulo, inicio, fim in cache:
                writer.writerow({'titulo': titulo, 'inicio': inicio, 'fim': fim})
        print(f"Removed {len(cache_to_remove)} events from cache.")

# ————————— MAIN —————————
def main():
    print("\n1. Fetching Teams events for current and next week...")
    current_events, start, end = get_teams_events()
    print(f"Found {len(current_events)} events")
    current_events_sorted = sorted(current_events, key=lambda e: e['inicio'])

    print("\n2. Caching events to CSV...")
    cached_set = load_event_cache()
    before_count = len(cached_set)
    new_events = append_events_to_cache(current_events_sorted, cached_set)
    after_count = len(cached_set)
    print(f"Total cached events: {after_count}")
    print(f"New events added in this run: {len(new_events)}")

    if new_events:
        print("\nNew events added:")
        for idx, event in enumerate(new_events, 1):
            print(f"{idx}. {event['inicio']} - {event['fim']}: {event['titulo']}")
    else:
        print("\nNo new events added.")

    print("\n3. Fetching Google Calendar events for the same period...")
    svc = get_calendar_service()
    google_events = get_google_events(svc, start, end)

    google_events_by_title = {}
    for event in google_events:
        title = event['titulo']
        if title not in google_events_by_title:
            google_events_by_title[title] = []
        google_events_by_title[title].append((
            parse_datetime(event['inicio']).strftime('%Y-%m-%d %H:%M:%S'),
            parse_datetime(event['fim']).strftime('%Y-%m-%d %H:%M:%S')
        ))

    print("\n4. Events in cache but NOT in Google Calendar:")
    only_in_cache = []
    for titulo, inicio, fim in cached_set:
        dt_inicio = parse_datetime(inicio).strftime('%Y-%m-%d %H:%M:%S')
        dt_fim = parse_datetime(fim).strftime('%Y-%m-%d %H:%M:%S')
        event_exists = False
        if titulo in google_events_by_title:
            for g_start, g_end in google_events_by_title[titulo]:
                if dt_inicio == g_start and dt_fim == g_end:
                    event_exists = True
                    break
        if not event_exists:
            only_in_cache.append((titulo, inicio, fim))

    if only_in_cache:
        print("\nEvents to create in Google Calendar:")
        svc = get_calendar_service()
        created_count = 0
        for idx, (titulo, inicio, fim) in enumerate(only_in_cache, 1):
            print(f"{idx}. {inicio} - {fim}: {titulo}")
            ev = {
                'titulo': titulo,
                'inicio': inicio if 'T' in inicio else inicio.replace(' ', 'T'),
                'fim': fim if 'T' in fim else fim.replace(' ', 'T')
            }
            criar_evento_google(svc, ev)
            created_count += 1
        if created_count == 0:
            print("No events created.")
    else:
        print("All cached events are present in Google Calendar.")

    # --- NOVA VERIFICAÇÃO: Remover pares cancelados e originais ---
    print("\n5. Checking for 'Cancelado:' events and removing pairs if found...")
    svc = get_calendar_service()
    buscar_e_deletar_cancelados(svc)

if __name__ == '__main__':
    main()
