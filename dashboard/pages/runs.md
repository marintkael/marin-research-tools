---
title: Pipeline-Lauf-Historie
description: Liste der letzten 30 Pipeline-Läufe mit Status, Dauer und Stage-Fehlern.
---

```sql runs
select
  run_at,
  triggered_by,
  duration_ms / 1000.0 as duration_sec,
  stages_ok,
  stages_failed,
  score_percent,
  primary_channel_percent,
  control_channel_percent
from marin.timeseries
order by run_at desc
```

```sql run_summary
select
  count(*) as total_runs,
  sum(case when stages_failed = 0 then 1 else 0 end) as clean_runs,
  sum(stages_failed) as total_stage_failures,
  avg(duration_ms) / 1000.0 as avg_duration_sec
from marin.timeseries
```

## Lauf-Zusammenfassung · letzte 30 Tage

<BigValue data={run_summary} value=total_runs fmt='num0' title="Läufe gesamt"/>
<BigValue data={run_summary} value=clean_runs fmt='num0' title="ohne Stage-Fehler"/>
<BigValue data={run_summary} value=total_stage_failures fmt='num0' title="Stage-Fehler gesamt"/>
<BigValue data={run_summary} value=avg_duration_sec fmt='num1' title="Ø Dauer (sek)"/>

## Lauf-Liste

<DataTable data={runs} rows=30 search=true>
  <Column id=run_at title="Lauf-Zeit (UTC)"/>
  <Column id=triggered_by title="Auslöser"/>
  <Column id=duration_sec fmt='num1' title="Dauer (sek)"/>
  <Column id=stages_ok fmt='num0' title="Stages OK"/>
  <Column id=stages_failed fmt='num0' title="Stages fehlgeschlagen"/>
  <Column id=score_percent fmt='num1' title="Score %"/>
  <Column id=primary_channel_percent fmt='num1' title="Primary %"/>
  <Column id=control_channel_percent fmt='num1' title="Control %"/>
</DataTable>

---

[← zurück zur Overview](/) · [Timeline](/timeline) · [Compare](/compare)
