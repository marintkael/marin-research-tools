---
title: Timeline-Deep-Dive
description: 30-Tage-Verlauf aller LLMs in einem Chart. Filter nach Provider oder Channel.
---

```sql provider_options
select distinct provider from marin.llm_timeseries order by provider
```

```sql channel_options
select distinct channel from marin.llm_timeseries order by channel
```

<Dropdown data={provider_options} name=prov value=provider defaultValue="%" title="Provider">
  <DropdownOption value="%" valueLabel="Alle Provider"/>
</Dropdown>
<Dropdown data={channel_options} name=chan value=channel defaultValue="%" title="Channel">
  <DropdownOption value="%" valueLabel="Alle Channels"/>
</Dropdown>

```sql llm_lines
select
  run_at::date as run_date,
  llm,
  provider,
  channel,
  percent
from marin.llm_timeseries
where provider like '${inputs.prov.value}'
  and channel like '${inputs.chan.value}'
order by run_at, llm
```

```sql llm_avg
select
  llm,
  provider,
  channel,
  avg(percent) as avg_percent,
  min(percent) as min_percent,
  max(percent) as max_percent,
  count(*) as n_obs
from marin.llm_timeseries
where provider like '${inputs.prov.value}'
  and channel like '${inputs.chan.value}'
group by llm, provider, channel
order by avg_percent desc
```

## Alle LLMs · gefiltert auf {inputs.prov.label} · {inputs.chan.label}

<LineChart
  data={llm_lines}
  x=run_date
  y=percent
  series=llm
  yAxisTitle="Score in Prozent"
  title="LLM-Verlauf"
/>

## 30-Tage-Aggregate je LLM

<DataTable data={llm_avg} rows=20 search=true>
  <Column id=llm/>
  <Column id=provider/>
  <Column id=channel/>
  <Column id=avg_percent fmt='num1' title="Ø Score %"/>
  <Column id=min_percent fmt='num1' title="Min %"/>
  <Column id=max_percent fmt='num1' title="Max %"/>
  <Column id=n_obs fmt='num0' title="Läufe"/>
</DataTable>

---

[← zurück zur Overview](/) · [Compare](/compare)
