# Food Alert Italia

Web app italiana per consultare richiami alimentari ufficiali, salvare prodotti
in dispensa e consultare le aree FAO. L'architettura esistente è mantenuta:
FastAPI + SQLAlchemy async + Supabase/Postgres nel backend e Vite + React + TypeScript nel frontend.

## Struttura

```text
backend/   API FastAPI, modelli Pydantic, repository e sincronizzazioni
frontend/  Vite, React 19, TypeScript, Tailwind e interfaccia web/PWA
tests/     configurazione Playwright e fixture e2e
```

Le note di lavoro locali non fanno parte della distribuzione pubblica.

```text
memory/    specifiche e decisioni locali del progetto
```

## Prerequisiti

- Node.js 20 o superiore e Corepack/Yarn;
- Python 3.12 o superiore;
- un progetto Supabase con database Postgres;
- Chromium/Playwright solo per la sincronizzazione delle pagine del Ministero.

## Configurazione Supabase

Copiare `backend/.env.example` in `backend/.env` e impostare almeno:

```dotenv
APP_ENV=development
DATABASE_URL=postgresql+asyncpg://postgres.PROJECT_REF:DB_PASSWORD@aws-1-eu-west-1.pooler.supabase.com:6543/postgres
SUPABASE_URL=https://PROJECT_REF.supabase.co
SUPABASE_PROJECT_REF=PROJECT_REF
```

Nel progetto Supabase usare `backend/migrations/001_initial_supabase.sql` nello
SQL Editor. Il backend usa il pooler Postgres con SQLAlchemy async e non usa
più Motor/MongoDB durante il funzionamento normale. Non committare mai
`backend/.env`, password, API key o token.

## Avvio locale

Da due terminali PowerShell:

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env       # se .env non esiste già
python seed.py                    # idempotente, non cancella dati
python -m uvicorn server:app --host 127.0.0.1 --port 8001 --reload
```

Nel secondo terminale:

```powershell
cd frontend
corepack yarn install --immutable
corepack yarn dev --host 127.0.0.1
```

Aprire `http://127.0.0.1:3000/`. Il proxy Vite inoltra `/api/*` a
`http://127.0.0.1:8001`, quindi il frontend usa sempre percorsi relativi.

Se esiste un vecchio database Mongo da conservare, configurare temporaneamente
`MONGO_URL` e `MONGO_DB_NAME` e lanciare prima un dry-run:

```powershell
python migrate_mongo_to_supabase.py
python migrate_mongo_to_supabase.py --apply
```

Lo script non cancella la sorgente Mongo. Dopo la verifica, rimuovere
`MONGO_URL` dal file `.env`.

L'API non avvia il sincronizzatore. Per eseguire un solo worker scheduler:

```powershell
cd backend
python scheduler.py
```

In produzione eseguire una sola istanza di questo worker, separata dai processi
API. `SCHEDULER_ENABLED=false` lo disabilita. Questo evita duplicazioni di sync
e notifiche quando l'API viene scalata su più worker.

## Health e readiness

- `GET /api/health` è liveness e non richiede il database;
- `GET /api/ready` verifica Supabase/Postgres con timeout limitato e restituisce `503` se
  il database non è disponibile;
- le route applicative possono quindi restituire un errore di dipendenza senza
  bloccare indefinitamente la richiesta.

## Dati e sincronizzazioni

Il seed registra soltanto le fonti ufficiali. I nuovi richiami e le nuove
misurazioni hanno `is_demo=false` per default; nessun dato reale viene
trasformato in demo. Il worker usa Supabase/Postgres e:

- conserva in Postgres la coda Ministero oltre le prime 25 pagine;
- riesamina periodicamente un piccolo gruppo di pagine già note e conserva le
  versioni quando cambia il `content_hash`;
- distingue record inseriti, aggiornati, invariati e falliti;
- usa aggregazioni SQL per le statistiche, senza il precedente limite di 1000
  documenti.

La pulizia di fixture demo o il pruning delle fonti è esplicita e protetta:

```powershell
$env:APP_ENV="development"
$env:ALLOW_DESTRUCTIVE_SEED="true"
python seed.py --purge-demo --prune-sources
```

È rifiutata se il profilo non è `development`/`test` o il flag non è esplicito.
Non usare questa operazione su dati reali.

## Superficie amministrativa

L'area `/admin` è privata e richiede l'autenticazione dell'unico account
amministratore configurato nelle variabili d'ambiente (`ADMIN_EMAIL`,
`ADMIN_PASSWORD_HASH` e `ADMIN_SESSION_SECRET`). Le route operative
`/api/admin/*` richiedono una sessione httpOnly firmata; la pagina pubblica di
metodologia usa invece `GET /api/sources` in sola lettura. Le credenziali non
devono essere inserite nel repository o nel frontend.

## PWA

Il manifest è in `frontend/public/manifest.webmanifest`; il service worker è
registrato solo nelle build di produzione. Non viene promesso il supporto
offline completo: la cache è preparatoria per il task PWA dedicato.

## Verifiche

```powershell
cd frontend
corepack yarn typecheck
corepack yarn lint
corepack yarn build
```

Backend, quando Python e Supabase sono configurati:

```powershell
cd backend
python -c "import server"
python -m pytest -q
```

La suite backend usa il servizio raggiungibile tramite `BACKEND_URL` (default
`http://127.0.0.1:8001`) e deve essere eseguita con un database di test.
