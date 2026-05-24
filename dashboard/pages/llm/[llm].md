---
title: LLM-Detail · {params.llm}
description: 30-Tage-Drill-Down für ein einzelnes LLM. Score-Trajektorie, Verteilung über Kategorien und Lauf-Historie.
---

```sql llm_meta
select * from marin.by_llm where llm = '${params.llm}'
```

```sql llm_history
select
  run_at::date as run_date,
  percent,
  score,
  n
from marin.llm_timeseries
where llm = '${params.llm}'
order by run_at
```

```sql llm_rank_today
select
  llm,
  percent,
  case when llm = '${params.llm}' then '👉' else '' end as marker
from marin.by_llm
order by percent desc
```

# {params.llm}

<Details title="Was steht hier?">

Ein LLM-spezifischer Drill: aktueller Score, 30-Tage-Verlauf, Position im
Provider-Ranking. Wechsel zu anderem LLM via Tabelle unten oder via Liste
in der [Overview](/).

</Details>

<BigValue
  data={llm_meta}
  value=percent
  fmt='num1'
  title="Score (aktueller Lauf)"
/>
<BigValue
  data={llm_meta}
  value=score
  fmt='num0'
  title="Punkte"
/>
<BigValue
  data={llm_meta}
  value=provider
  title="Provider"
/>
<BigValue
  data={llm_meta}
  value=channel
  title="Channel"
/>
<BigValue
  data={llm_meta}
  value=n
  fmt='num0'
  title="Datenpunkte / Lauf"
/>

## Score-Trajektorie · letzte 30 Tage

<LineChart
  data={llm_history}
  x=run_date
  y=percent
  yAxisTitle="Score in Prozent"
  title="Tagesscore"
/>

<AreaChart
  data={llm_history}
  x=run_date
  y=score
  yAxisTitle="Rohpunkte"
  title="Roh-Punktesumme"
/>

<DataTable
  data={llm_history}
  rows=15
  search=true
>
  <Column id=run_date title="Datum"/>
  <Column id=percent fmt='num1' title="Score %"/>
  <Column id=score fmt='num0' title="Punkte"/>
  <Column id=n fmt='num0' title="Datenpunkte"/>
</DataTable>

## Position im Ranking (heute)

<DataTable data={llm_rank_today} rows=20>
  <Column id=marker title=""/>
  <Column id=llm/>
  <Column id=percent fmt='num1' title="Score %"/>
</DataTable>

---

[← zurück zur Overview](/) · [Compare](/compare) · [Timeline-Deep-Dive](/timeline)
