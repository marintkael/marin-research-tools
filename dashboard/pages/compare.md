---
title: LLM-Compare
description: Wähle zwei LLMs aus und vergleiche ihren Score-Verlauf über 30 Tage seite an seite.
---

```sql llm_options
select distinct llm from marin.llm_timeseries order by llm
```

<Dropdown data={llm_options} name=llm_a value=llm defaultValue="gemini" title="LLM A"/>
<Dropdown data={llm_options} name=llm_b value=llm defaultValue="openai_search" title="LLM B"/>

```sql series_a
select
  run_at::date as run_date,
  percent
from marin.llm_timeseries
where llm = '${inputs.llm_a.value}'
order by run_at
```

```sql series_b
select
  run_at::date as run_date,
  percent
from marin.llm_timeseries
where llm = '${inputs.llm_b.value}'
order by run_at
```

```sql combined
select
  run_at::date as run_date,
  llm,
  percent
from marin.llm_timeseries
where llm in ('${inputs.llm_a.value}','${inputs.llm_b.value}')
order by run_at, llm
```

```sql delta
with a as (
  select run_at::date as run_date, percent as percent_a
  from marin.llm_timeseries where llm = '${inputs.llm_a.value}'
),
b as (
  select run_at::date as run_date, percent as percent_b
  from marin.llm_timeseries where llm = '${inputs.llm_b.value}'
)
select
  a.run_date,
  percent_a,
  percent_b,
  (percent_a - percent_b) as delta
from a join b using (run_date)
order by run_date
```

## Vergleichen

Wähle oben zwei LLMs. Der Vergleich aktualisiert sich live.

### Score-Verlauf · beide LLMs überlagert

<LineChart
  data={combined}
  x=run_date
  y=percent
  series=llm
  yAxisTitle="Score in Prozent"
  title="{inputs.llm_a.value} vs. {inputs.llm_b.value}"
/>

### Delta · A minus B (Prozentpunkte)

<AreaChart
  data={delta}
  x=run_date
  y=delta
  yAxisTitle="Differenz in Prozentpunkten"
  title="Delta-Spread über Zeit"
/>

### Roh-Tabelle

<DataTable data={delta} rows=15 search=true>
  <Column id=run_date title="Datum"/>
  <Column id=percent_a fmt='num1' title="A: {inputs.llm_a.value}"/>
  <Column id=percent_b fmt='num1' title="B: {inputs.llm_b.value}"/>
  <Column id=delta fmt='num1' title="Δ (A−B)"/>
</DataTable>

---

[← zurück zur Overview](/) · [Timeline](/timeline)
