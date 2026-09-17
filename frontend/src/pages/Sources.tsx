const GLOSSARY = [
  ["Richiamo", "Il prodotto è già stato venduto: si chiede al consumatore di non consumarlo e di riportarlo al punto vendita."],
  ["Ritiro", "Il prodotto viene rimosso dalla distribuzione prima di arrivare al consumatore."],
  ["Zona FAO", "Codice dell'area di cattura del pescato, indicato in etichetta (es. FAO 37 per il Mediterraneo)."],
  ["Metodo di produzione", "Indica se il prodotto ittico è pescato o allevato, quando il dato è riportato nel documento ufficiale."],
  ["Specie", "Nome scientifico del pesce o dell'organismo marino, quando presente nell'etichetta o nel documento ufficiale."],
];

const SOURCES_INFO = [
  {
    name: "Ministero della Salute — archivio richiami",
    description: "Avvisi e richiami ufficiali di prodotti alimentari pubblicati dal Ministero della Salute.",
    url: "https://www.salute.gov.it/new/it/avvisi/avvisi-e-richiami-di-prodotti-alimentari/",
  },
  {
    name: "Ministero della Salute — feed richiami",
    description: "Feed ufficiale utilizzato per intercettare i nuovi richiami alimentari pubblicati.",
    url: "https://www.salute.gov.it/new/it/altro/rss/",
  },
  {
    name: "RASFF — Commissione Europea",
    description: "Sistema europeo di allerta rapida per alimenti e mangimi, utilizzato per i richiami notificati in Europa.",
    url: "https://webgate.ec.europa.eu/rasff-window/screen/list",
  },
  {
    name: "FAO Major Fishing Areas",
    description: "Aree, sottozone e divisioni ufficiali utilizzate per identificare la zona di cattura del pescato.",
    url: "https://www.fao.org/fishery/geoserver/fifao/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=fifao:FAO_AREAS_ERASE_LOWRES&outputFormat=json",
  },
];

const FAQ_ITEMS = [
  {
    question: "Food Alert Italia è un servizio ufficiale?",
    answer: "No. È un servizio informativo indipendente: non è un'autorità sanitaria e non sostituisce il Ministero della Salute, il RASFF, la FAO o le comunicazioni del produttore. Ogni scheda rimanda alla fonte originale.",
  },
  {
    question: "Da dove provengono i dati?",
    answer: "I richiami sono raccolti dalle pubblicazioni del Ministero della Salute e dalle notifiche RASFF della Commissione Europea. Le zone di cattura sono ricavate dalle aree ufficiali FAO. I dati vengono organizzati per rendere più semplice la consultazione, senza aggiungere valori non presenti nelle fonti.",
  },
  {
    question: "Cosa devo fare se trovo un prodotto richiamato?",
    answer: "Non consumare il prodotto, conserva la confezione e il lotto, contatta il punto vendita e segui le indicazioni contenute nell'avviso ufficiale. Per una segnalazione sanitaria relativa a un prodotto, il Ministero indica di rivolgersi alla ASL/ATS competente o, in alternativa, ai NAS.",
  },
  {
    question: "La zona FAO dimostra che il pesce è sicuro?",
    answer: "No. Il codice FAO identifica l'area di cattura indicata in etichetta; da solo non certifica la sicurezza del singolo alimento e non sostituisce i controlli o gli avvisi ufficiali.",
  },
  {
    question: "Perché a volte mancano EAN, lotto, scadenza o altri dati?",
    answer: "Non tutti gli avvisi ufficiali riportano gli stessi campi e alcuni documenti possono essere incompleti o difficili da leggere. Quando un dato non è disponibile nella fonte, lo lasciamo non disponibile e invitiamo a verificare il documento originale.",
  },
  {
    question: "Se un prodotto non compare, significa che è sicuro?",
    answer: "No. L'assenza di un prodotto nell'app non costituisce una certificazione di sicurezza. Per la decisione finale bisogna sempre controllare l'etichetta, il lotto e le comunicazioni ufficiali più recenti.",
  },
  {
    question: "Quali dati personali sono necessari?",
    answer: "La consultazione delle pagine pubbliche non richiede un account. L'area amministrativa è riservata. In questa versione sono previsti solo cookie tecnici per la sessione amministrativa e per memorizzare le preferenze cookie; non sono attivi strumenti di analisi, profilazione o pubblicità.",
  },
];

const LEGAL_REFERENCES = [
  ["Regolamento (CE) 178/2002 — sicurezza, tracciabilità, ritiro e richiamo", "https://eur-lex.europa.eu/eli/reg/2002/178/"],
  ["Regolamento (UE) 1169/2011 — informazioni sugli alimenti", "https://eur-lex.europa.eu/legal-content/EN/ALL/?uri=celex:32011R1169"],
  ["Ministero della Salute — avvisi e richiami alimentari", "https://www.salute.gov.it/new/it/avvisi/avvisi-e-richiami-di-prodotti-alimentari/"],
  ["Ministero della Salute — segnalazioni dei consumatori", "https://www.salute.gov.it/new/it/faq/modalita-di-segnalazione-da-parte-dei-consumatori/"],
  ["Garante Privacy — FAQ cookie", "https://www.garanteprivacy.it/faq/cookie"],
];

export default function Sources() {
  return (
    <div className="space-y-8">
      <header className="space-y-2">
        <h1 className="font-heading text-3xl font-extrabold tracking-tight">Fonti e metodologia</h1>
        <p className="max-w-3xl text-slate-600 dark:text-slate-400">
          Qui trovi le fonti ufficiali utilizzate per i dati mostrati nell'app. Ogni scheda rimanda direttamente
          alla pagina originale.
        </p>
      </header>

      <section className="space-y-3">
        <h2 className="font-heading text-2xl font-bold tracking-tight">Le fonti utilizzate</h2>
        <div className="grid gap-4 md:grid-cols-2">
          {SOURCES_INFO.map((source) => (
            <div
              key={source.name}
              data-testid={`source-info-${source.name}`}
              className="rounded-2xl border border-slate-200 bg-card p-4 dark:border-slate-800"
            >
              <h3 className="font-heading text-lg font-semibold">{source.name}</h3>
              <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{source.description}</p>
              <a
                href={source.url}
                target="_blank"
                rel="noreferrer noopener"
                className="mt-3 inline-block text-sm text-sky-700 underline underline-offset-2 dark:text-sky-400"
              >
                Apri fonte ufficiale
              </a>
            </div>
          ))}
        </div>
      </section>

      <section className="space-y-3" aria-labelledby="faq-title">
        <h2 id="faq-title" className="font-heading text-2xl font-bold tracking-tight">FAQ e informazioni importanti</h2>
        <p className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200">
          Le risposte hanno finalità informative e non sostituiscono gli avvisi delle autorità competenti né una consulenza legale o sanitaria.
        </p>
        <div className="space-y-3">
          {FAQ_ITEMS.map((item) => (
            <details key={item.question} className="group rounded-2xl border border-slate-200 bg-card p-4 dark:border-slate-800">
              <summary className="cursor-pointer list-none pr-6 font-semibold marker:hidden after:float-right after:text-slate-400 after:content-['+'] group-open:after:content-['−']">
                {item.question}
              </summary>
              <p className="mt-3 text-sm leading-6 text-slate-600 dark:text-slate-400">{item.answer}</p>
            </details>
          ))}
        </div>
        <div className="rounded-2xl border border-slate-200 bg-card p-4 dark:border-slate-800">
          <h3 className="font-semibold">Riferimenti normativi e istituzionali</h3>
          <ul className="mt-2 space-y-2 text-sm text-sky-700 dark:text-sky-400">
            {LEGAL_REFERENCES.map(([label, url]) => (
              <li key={url}>
                <a href={url} target="_blank" rel="noreferrer noopener" className="underline underline-offset-2">
                  {label}
                </a>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section id="cookie-policy" className="space-y-3" aria-labelledby="cookie-policy-title">
        <h2 id="cookie-policy-title" className="font-heading text-2xl font-bold tracking-tight">Informativa sui cookie e sugli strumenti di tracciamento</h2>
        <div className="rounded-2xl border border-slate-200 bg-card p-4 text-sm leading-6 text-slate-600 dark:border-slate-800 dark:text-slate-400">
          <p>
            Food Alert Italia utilizza esclusivamente cookie tecnici necessari al funzionamento del sito e alla protezione dell&apos;area amministrativa.
            Il sito non utilizza cookie di profilazione, pubblicità o analisi del comportamento.
          </p>
          <ul className="mt-3 space-y-2">
            <li><strong className="text-slate-900 dark:text-slate-100">food_alert_session</strong>: cookie tecnico di sessione che consente l&apos;autenticazione e la sicurezza dell&apos;area amministrativa. Durata massima: 8 ore.</li>
            <li><strong className="text-slate-900 dark:text-slate-100">food_alert_cookie_consent</strong>: cookie tecnico che memorizza le preferenze sui cookie. Durata: 180 giorni.</li>
          </ul>
          <p className="mt-3">
            La consultazione delle pagine pubbliche non richiede la creazione di un account. Le preferenze possono essere modificate in qualsiasi momento selezionando “Gestisci cookie” nel piè di pagina.
          </p>
          <p className="mt-3">
            Qualora venissero introdotti strumenti facoltativi di analisi, profilazione o pubblicità, questi verrebbero descritti nell&apos;informativa aggiornata e attivati esclusivamente dopo una scelta esplicita.
          </p>
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="font-heading text-2xl font-bold tracking-tight">Glossario</h2>
        <dl className="grid gap-3 md:grid-cols-2">
          {GLOSSARY.map(([term, text]) => (
            <div key={term} className="rounded-2xl border border-slate-200 bg-card p-4 dark:border-slate-800">
              <dt className="font-semibold">{term}</dt>
              <dd className="mt-1 text-sm text-slate-600 dark:text-slate-400">{text}</dd>
            </div>
          ))}
        </dl>
      </section>
    </div>
  );
}
