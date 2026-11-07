# Как TimescaleDB использует PostgreSQL, hypertables и chunks для временных рядов?

TimescaleDB расширяет PostgreSQL для time-series workloads. **Hypertable** выглядит как одна логическая таблица, но данные размещаются в **chunks** по временной dimension и при необходимости дополнительному разбиению. Planner и ingestion используют это размещение для ограничения работы подходящими участками.

Сохраняются PostgreSQL SQL, transactions и интеграция с обычными таблицами, но действуют ограничения extension. Chunks одной hypertable не означают автоматическое распределение по независимым servers. Выбор оправдывают профилем time filters, ingestion и lifecycle данных, а не одним наличием timestamp. [Tiger Data: Hypertable performance](https://www.tigerdata.com/docs/build/performance-optimization/improve-hypertable-performance).

# Как выбирать chunk interval с учётом working set, ingestion и late-arriving data?

Слишком крупный chunk увеличивает активные indexes и I/O при записи, а слишком мелкий создаёт много relations и повышает planning и maintenance overhead. Интервал выбирают по скорости прироста данных и indexes, доступной memory и типичным диапазонам queries.

Учитывают все одновременно изменяемые chunks, включая late-arriving data и несколько hypertables. Изменение chunk interval обычно влияет на новые chunks, поэтому не исправляет мгновенно прежнее разбиение. Реальные размеры и query plans проверяют на характерной нагрузке; guideline по доле memory не является универсальной гарантией. [Tiger Data: Chunk interval](https://www.tigerdata.com/docs/build/performance-optimization/improve-hypertable-performance).

# Как проектировать индексы и unique constraints для time-partitioned hypertable?

Index строят по access pattern: например, lookup ряда устройства и временного диапазона может требовать `(device_id, time)`, тогда как общий временной scan имеет другой профиль. Каждый index увеличивает ingestion и storage cost; partition pruning и index lookup решают разные задачи.

Unique index hypertable должен включать все partitioning columns, включая time. Поэтому `UNIQUE(event_id, time)` не гарантирует уникальность event ID при разных timestamps. Если нужен глобальный registry событий, инвариант обеспечивают отдельной подходящей моделью. Состав primary key согласуют с этим ограничением до миграции. [Tiger Data: Unique indexes](https://www.tigerdata.com/docs/build/performance-optimization/hypertables-and-unique-indexes).

# Как time_bucket, gap filling, LOCF и interpolation меняют смысл time-series запроса?

`time_bucket` группирует наблюдения по временным интервалам; `time_bucket_gapfill` добавляет отсутствующие buckets в заданном диапазоне. Сам gap filling не создаёт реальных измерений: без подходящего заполнения пропуск остаётся `NULL`.

**LOCF** переносит последнее наблюдение вперёд, а interpolation оценивает промежуточное значение по выбранной модели. Это предположения о данных, которые нельзя автоматически применять к любому сигналу. Проверяют treatment явных `NULL`, границы диапазона, timezone и DST; календарный bucket не всегда равен постоянному числу секунд. Доступные arguments зависят от версии. [Tiger Data: Gap filling](https://www.tigerdata.com/docs/reference/timescaledb/hyperfunctions/time_bucket_gapfill/time_bucket_gapfill).

# Как continuous aggregates отличаются от обычного aggregate query и materialized view?

Обычный aggregate query вычисляет результат по доступным raw rows при запросе. PostgreSQL materialized view сохраняет результат и требует предусмотренного refresh. **Continuous aggregate** хранит предварительно рассчитанные time buckets и обновляет затронутые диапазоны через механизм TimescaleDB.

Это уменьшает повторное чтение raw data, но добавляет storage, refresh work и freshness contract. Supported functions и формы JOIN зависят от версии. При JOIN изменения обычной PostgreSQL таблицы сами по себе не отслеживаются как изменения hypertable: необходимость пересчёта dimension-related результатов продумывают отдельно. [Tiger Data: Continuous aggregates](https://www.tigerdata.com/docs/learn/continuous-aggregates).

# Как refresh window, invalidation и real-time aggregation определяют свежесть continuous aggregate?

`start_offset` и `end_offset` задают окно относительно времени запуска refresh policy, а schedule — частоту попыток обновления. Только соответствующие buckets пересчитываются; исторический backfill вне окна может оставаться невидимым до отдельного refresh. Незавершённый текущий bucket обычно исключают из materialization.

**Real-time aggregation** дополняет materialized часть свежими raw rows за watermark, но не исправляет автоматически поздние изменения уже materialized истории. Начиная с TimescaleDB 2.13 real-time aggregates отключены по умолчанию; нужный режим задают явно. [Refresh policies](https://github.com/timescale/docs/blob/latest/use-timescale/continuous-aggregates/refresh-policies.md), [Real-time aggregates](https://www.tigerdata.com/docs/learn/continuous-aggregates/real-time-aggregates).

# Как rowstore, columnstore и Hypercore влияют на запись и аналитические scans TimescaleDB?

Rowstore удобен для поступающих и часто изменяемых строк. Columnstore уменьшает объём чтения нужных columns и может эффективнее сжимать исторические данные при аналитических scans. **Hypercore** объединяет эти формы в TimescaleDB с управлением переходом chunks между ними.

Настройки segmentation и ordering выбирают по filters, повторяемости значений и диапазонам запросов. Слишком высокая cardinality или неподходящий порядок могут уменьшить пользу. Не предполагают, что любые исторические updates имеют ту же стоимость, что свежие inserts: возможности DML, conversion и API проверяют для установленной версии. [Tiger Data: Hypercore](https://www.tigerdata.com/docs/learn/columnar-storage/understand-hypercore).

# Как согласовать retention raw data, aggregates и архивирование временных рядов?

Raw data, summaries и архив имеют разные сроки полезности. Retention может удалять целые старые chunks быстрее row-by-row deletion; chunk удаляется только при соответствии всего его диапазона условию, поэтому граница не обязана совпадать с точностью отдельной строки.

Перед удалением проверяют нужные aggregates и archive. Если затем refresh охватит удалённый raw диапазон, соответствующие aggregate buckets также могут исчезнуть. Поэтому refresh window не должен заходить в удалённую историю, которую требуется сохранить как summary. Отдельно определяют поведение поздних записей и восстановления. [Retention](https://www.tigerdata.com/docs/learn/data-lifecycle/data-retention/about-data-retention), [Retention with aggregates](https://www.tigerdata.com/docs/learn/data-lifecycle/data-retention/data-retention-with-continuous-aggregates).

# Как batching, COPY, indexes и chunk pruning влияют на ingestion и query performance?

Batching и `COPY` уменьшают protocol overhead массовой загрузки, но не отменяют стоимость indexes, WAL, constraints и refresh jobs. Размер batch выбирают по memory, transaction duration и допустимому latency. Поток ограничивают, если downstream storage не успевает.

В queries указывают пригодные для pruning временные predicates, чтобы planner исключал ненужные chunks. Проверяют filters, statistics и число scanned chunks через plan. Ingestion, backfill, columnstore conversion и continuous-aggregate refresh конкурируют за ресурсы, поэтому их throughput и отставание наблюдают совместно, а не отдельными удачными benchmarks.

# Как эксплуатировать TimescaleDB background jobs, upgrades и backup/restore с учётом версии extension?

Контролируют scheduled jobs, ошибки и длительность refresh, retention и conversion, а также WAL, locks, disk и query latency. Наличие policy в catalog не доказывает, что job успешно выполняется. Upgrades требуют проверки совместимости PostgreSQL, TimescaleDB и дополнительных extensions.

Backup должен сохранять необходимые данные и extension metadata. Logical restore использует документированный для версии порядок установки extension и restore mode; physical restore требует совместимого окружения и журналов. После восстановления проверяют hypertables, aggregates, jobs и пользовательские queries. Изменение binaries без предусмотренного extension upgrade недостаточно. [Tiger Data: Administration](https://www.tigerdata.com/docs/reference/timescaledb/administration).

