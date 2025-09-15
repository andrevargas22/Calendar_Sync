# Calendar_Sync

## Visão Geral
Sincroniza eventos do calendário do Microsoft Teams (via ICS) com o Google Calendar, sempre refletindo o que está no Teams no Google. Se um evento for cancelado (título começa com `Cancelado:`), o evento correspondente é removido do Google Calendar.

## Como funciona
- Busca eventos do Teams e do Google Calendar para o período configurado.
- Remove do Google qualquer evento que não esteja mais no Teams.
- Cria no Google qualquer evento novo do Teams.
- O script é idempotente: rodar várias vezes não gera duplicidade.

## Configuração
- Variáveis de ambiente (definidas nos secrets do Actions):
  - `TEAMS_ICS_URL`: URL do ICS do Teams
  - `GOOGLE_CREDENTIALS`: JSON da conta de serviço Google
  - `GOOGLE_CALENDAR_ID`: ID do Google Calendar
- O período de sincronização pode ser ajustado em `src/config.py`.

## Estrutura
- `calendar_sync.py`: Script principal
- `src/`: Funções auxiliares e integração com APIs

---
Projeto pessoal, privado, para uso próprio.