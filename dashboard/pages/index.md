---
title: Marin Research · Explore
description: Durchklickbare Sicht auf die täglich gemessenen Sichtbarkeits- und Zitations-Daten des Marin T. Kael Forschungs­programms. Slicer · Drill-Down · 30 Tage Historie.
---

<Details title="Was zeigt dieses Dashboard?">

Dieses Dashboard ist die **interaktive Schwester** der statischen
[Research-Dashboard-Seite](https://marin-t-kael.de/research/dashboard).
Während dort der aktuelle Snapshot als feste Grafik gezeigt wird, kannst
Du hier durchklicken, filtern und Zeit­räume vergleichen.

Alle Daten kommen aus den öffentlichen Pipeline-Endpoints
`/api/latest` und `/api/timeseries`. Aktualisierung täglich 04:00 UTC.
Methodische Grundlage: [Methodology Note 01 v4.0](https://doi.org/10.5281/zenodo.20364173).

</Details>

```sql run
select * from marin.run_meta
```

```sql provider_rollup
select
  provider,
  percent,
  score,
  n,
  n_llms
from marin.by_provider
order by percent desc
```

```sql llm_rollup
select
  llm,
  provider,
  channel,
  percent,
  score,
  n,
  '/llm/' || llm as llm_detail_link
from marin.by_llm
order by percent desc
```

```sql category_rollup
select
  category,
  percent,
  score,
  n
from marin.by_category
order by percent desc
```

```sql timeline_overall
select
  run_at::date as run_date,
  score_percent,
  primary_channel_percent,
  control_channel_percent,
  echo_bias_inflation_pp
from marin.timeseries
order by run_at
```

## Aktueller Stand · Lauf {run[0].run_at}

<BigValue
  data={run}
  value=score_percent
  fmt='num1'
  title="Score (Aggregat)"
  comparisonTitle="Punkte"
  comparison=total_score
/>
<BigValue
  data={run}
  value=primary_channel_percent
  fmt='num1'
  title="Primary Channel %"
  comparisonTitle="Datenpunkte"
  comparison=primary_channel_datapoints
/>
<BigValue
  data={run}
  value=control_channel_percent
  fmt='num1'
  title="Control Channel %"
  comparisonTitle="Datenpunkte"
  comparison=control_channel_datapoints
/>
<BigValue
  data={run}
  value=echo_bias_inflation_pp
  fmt='num2'
  title="Echo-Bias-Inflation (pp)"
/>
<BigValue
  data={run}
  value=total_llms
  fmt='num0'
  title="LLMs gemessen"
  comparisonTitle="Fragen"
  comparison=total_questions
/>

---

## Score-Verlauf · letzte 30 Tage

<LineChart
  data={timeline_overall}
  x=run_date
  y={['score_percent','primary_channel_percent','control_channel_percent']}
  yAxisTitle="Prozent"
  title="Aggregat-Score über Zeit (alle Channels)"
/>

Echo-Bias-Inflation (Differenz Web-LLMs ↔ Cutoff-Control) als
Robustheits-Indikator:

<LineChart
  data={timeline_overall}
  x=run_date
  y=echo_bias_inflation_pp
  yAxisTitle="Inflation in Prozentpunkten"
  title="Echo-Bias-Inflation über Zeit"
/>

---

## Aufschlüsselung · aktueller Lauf

### Pro Provider

<BarChart
  data={provider_rollup}
  x=provider
  y=percent
  yAxisTitle="Score in Prozent"
  title="Provider-Vergleich"
/>

<DataTable
  data={provider_rollup}
  rows=10
>
  <Column id=provider/>
  <Column id=percent fmt='num1' title="Score %"/>
  <Column id=score fmt='num0' title="Punkte"/>
  <Column id=n fmt='num0' title="Datenpunkte"/>
  <Column id=n_llms fmt='num0' title="LLMs"/>
</DataTable>

### Pro LLM (klickbar → Drill-Down)

<BarChart
  data={llm_rollup}
  x=llm
  y=percent
  series=provider
  type=grouped
  yAxisTitle="Score in Prozent"
  title="LLM-Vergleich (gruppiert nach Provider)"
/>

<DataTable
  data={llm_rollup}
  rows=20
  link=llm_detail_link
>
  <Column id=llm title="LLM"/>
  <Column id=provider/>
  <Column id=channel/>
  <Column id=percent fmt='num1' title="Score %"/>
  <Column id=score fmt='num0' title="Punkte"/>
  <Column id=n fmt='num0' title="Datenpunkte"/>
</DataTable>

### Pro Kategorie

<BarChart
  data={category_rollup}
  x=category
  y=percent
  yAxisTitle="Score in Prozent"
  title="Kategorie-Vergleich"
/>

<DataTable
  data={category_rollup}
  rows=10
>
  <Column id=category/>
  <Column id=percent fmt='num1' title="Score %"/>
  <Column id=score fmt='num0' title="Punkte"/>
  <Column id=n fmt='num0' title="Datenpunkte"/>
</DataTable>

---

## Weiter erkunden

- **[LLM-Compare](/compare)** — zwei LLMs side-by-side, Zeitfenster wählbar
- **[Timeline-Deep-Dive](/timeline)** — Score-Verlauf pro LLM, alle Channels
- **[Pipeline-Lauf-Historie](/runs)** — 30 Tage Run-Status, Dauer, Stage-Fehler
- **[Zurück zur Research-Übersicht](https://marin-t-kael.de/research)**
