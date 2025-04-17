import requests
from icalendar import Calendar as ICALCalendar
import recurring_ical_events
from datetime import datetime, timedelta

# 1) URL do seu calendário ICS
ics_url = 'https://outlook.office365.com/owa/calendar/471f9c9338764ae3bf8839a02fdfcad1@casasbahia.com.br/af786ccf75ac4f05a3909066eb68ad4d1541582488987527822/calendar.ics'

# 2) Baixa e parseia o .ics
resp = requests.get(ics_url)
resp.raise_for_status()
ical = ICALCalendar.from_ical(resp.text)

# 3) Define o período: segunda 7h → sexta 18h desta semana
hoje = datetime.now()
segunda = hoje - timedelta(days=hoje.weekday())
inicio_periodo = segunda.replace(hour=7, minute=0, second=0, microsecond=0)
fim_periodo    = (segunda + timedelta(days=4)).replace(hour=18, minute=0, second=0, microsecond=0)

print(f"Eventos entre {inicio_periodo} e {fim_periodo}:\n")

# 4) Expande ocorrências (únicas + recorrentes)
events = recurring_ical_events.of(ical).between(inicio_periodo, fim_periodo)

# 5) Extrai dados de cada ocorrência
eventos_periodo = []
for e in events:
    dtstart = e.get('DTSTART').dt
    dtend   = e.get('DTEND').dt

    # Se vier só date, converte para datetime à meia‑noite
    if not isinstance(dtstart, datetime):
        dtstart = datetime.combine(dtstart, datetime.min.time())
    if not isinstance(dtend, datetime):
        dtend = datetime.combine(dtend, datetime.min.time())

    # Remove tzinfo para comparação simples
    dtstart = dtstart.replace(tzinfo=None)
    dtend   = dtend.replace(tzinfo=None)

    eventos_periodo.append({
        'titulo': str(e.get('SUMMARY')),
        'inicio': dtstart,
        'fim':    dtend
    })

# 6) Ordena por início e imprime
eventos_periodo.sort(key=lambda x: x['inicio'])
for ev in eventos_periodo:
    print(f"Título:  {ev['titulo']}")
    print(f"Início:  {ev['inicio']}")
    print(f"Término: {ev['fim']}")
    print("-" * 40)
