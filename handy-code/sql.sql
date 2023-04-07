delete from states where created <= datetime('now', '-7 days');

delete from events where created <= datetime('now', '-2 days');

delete from states where created < curdate()-7;

delete from events where created < curdate()-7;

delete from events where event_id not in (select event_id from states);

optimize table events;
optimize table states;

VACUUM;

SELECT entity_id, count(*)
FROM "states"
group by 1 order by 2 desc

SELECT count(*) FROM states WHERE created <= datetime('now', '-1 days')

SELECT
 entity_id,
 COUNT(entity_id)
FROM
 states
GROUP BY
 entity_id
ORDER BY COUNT(entity_id) DESC
LIMIT 40;

SELECT
 event_type,
 COUNT(event_type)
FROM
 events
GROUP BY
 event_type
ORDER BY COUNT(event_type) DESC
LIMIT 20;

SELECT verrijkt.entity_id, SUM(LENGTH(attributes)) size, COUNT(*) count, SUM(LENGTH(attributes))/COUNT(*) avg
FROM (SELECT new_states.entity_id, events.event_id, new_states.attributes FROM events LEFT JOIN states as new_states ON events.event_id = new_states.event_id) as verrijkt
GROUP BY verrijkt.entity_id
ORDER BY size DESC
limit 20;

SELECT
    JSON_VALUE(event_data, '$.entity_id') AS entity_id,
    COUNT(*) AS cnt
FROM events
WHERE
    JSON_VALUE(event_data, '$.entity_id') IS NOT NULL
GROUP BY
    JSON_VALUE(event_data, '$.entity_id')
ORDER BY
    COUNT(*) DESC;

SELECT entity_id, SUM(LENGTH(attributes)) size, COUNT(*) count, SUM(LENGTH(attributes))/COUNT(*) avg
FROM states
GROUP BY entity_id
ORDER BY size DESC;

WITH step1 AS (
    SELECT *, INSTR(event_data, '"entity_id": "') AS i
    FROM events),
step2 AS (
    SELECT *, CASE WHEN i>0 THEN SUBSTR(event_data, i+14) ELSE '' END AS sub
    FROM step1),
step3 AS (
    SELECT *, SUBSTR(sub, 0, INSTR(sub, '"')) AS entity_id
    from step2)
SELECT entity_id, SUM(LENGTH(event_data)) size, COUNT(*) count, SUM(LENGTH(event_data))/COUNT(*) avg
FROM step3
GROUP BY entity_id
ORDER BY size DESC;

SELECT
    table_name AS `Table Name`,
	table_rows AS `Row Count`,
	ROUND(SUM(data_length)/(1024*1024*1024), 3) AS `Table Size [GB]`,
	ROUND(SUM(index_length)/(1024*1024*1024), 3) AS `Index Size [GB]`,
	ROUND(SUM(data_length+index_length)/(1024*1024*1024), 3) `Total Size [GB]`
FROM information_schema.TABLES
WHERE table_schema = 'homeassistant'
GROUP BY table_name
ORDER BY table_name;

SELECT
  COUNT(state_id) AS cnt,
  COUNT(state_id) * 100 / (
    SELECT
      COUNT(state_id)
    FROM
      states
  ) AS cnt_pct,
  SUM(
    LENGTH(state_attributes.shared_attrs)
  ) AS bytes,
  SUM(
    LENGTH(state_attributes.shared_attrs)
  ) * 100 / (
    SELECT
      SUM(
        LENGTH(state_attributes.shared_attrs)
      )
    FROM
      states
  ) AS bytes_pct,
  states_meta.entity_id
FROM
  states
LEFT JOIN state_attributes ON (states.attributes_id=state_attributes.attributes_id)
LEFT JOIN states_meta ON (states.metadata_id=states_meta.metadata_id)
GROUP BY
  states.metadata_id
ORDER BY
  cnt DESC