# Для каких нагрузок BigQuery и Snowflake подходят лучше транзакционной backend-БД?

BigQuery и обычные аналитические таблицы Snowflake хорошо подходят для больших сканирований, агрегаций, JOIN и BI по историческим данным. Колонночное хранение и распределённые вычисления оптимизированы под такой профиль, а не обязательно под частые короткие изменения одной строки с минимальной задержкой.

OLTP-backend обычно требует иной формы индексов, конкурентности и транзакций. Нельзя распространять это различие на все продукты платформ: например, Snowflake hybrid tables имеют отдельные возможности для transactional workloads. Выбор проверяют по конкретному типу таблицы и нагрузке. [BigQuery overview](https://cloud.google.com/bigquery/docs/introduction), [Snowflake concepts](https://docs.snowflake.com/en/user-guide/intro-key-concepts).

# Как BigQuery и Snowflake разделяют хранение, вычисления и управление запросами?

Обе платформы разделяют долговременные данные и ресурсы выполнения запросов, позволяя независимо организовать вычислительную нагрузку. BigQuery управляет распределённым выполнением через свою serverless-модель; пользователь не выбирает VM для каждого SQL-запроса.

В Snowflake virtual warehouses предоставляют вычислительные ресурсы для многих операций, а cloud services управляет metadata, доступом и координацией. Отдельные функции могут использовать serverless compute. Разделение storage и compute не означает отсутствия quotas, очередей, стоимости maintenance и ограничений региона.

# Чем BigQuery slots и reservations отличаются от virtual warehouses Snowflake?

**Slot** BigQuery — виртуальная единица вычислений. Reservations и assignments распределяют доступную capacity между workloads; режим оплаты и autoscaling зависят от конфигурации. Это не прямой аналог собственного сервера на каждый запрос.

**Virtual warehouse** Snowflake задаёт вычислительную ёмкость с размером, lifecycle и настройками масштабирования. Увеличение размера и multi-cluster решают разные задачи; дополнительные clusters прежде всего помогают конкурентным workloads. Проверяют реальный выигрыш, очередь и время активности. [BigQuery slots](https://cloud.google.com/bigquery/docs/slots), [Snowflake warehouses](https://docs.snowflake.com/en/user-guide/warehouses-overview).

# Как partitioning и clustering BigQuery отличаются от micro-partitions и clustering Snowflake?

BigQuery partitioning явно делит таблицу по поддерживаемому ключу, например времени, а clustering организует storage blocks по выбранным колонкам. Подходящие фильтры позволяют читать меньше partitions и blocks.

В обычных таблицах Snowflake micro-partitions формируются автоматически, а metadata помогает исключать ненужные части. Clustering key может улучшать расположение данных для определённых фильтров, но имеет стоимость поддержания. Это не требование вручную создавать SQL-партиции и не универсальная замена любому индексу. [Partitioning BigQuery](https://cloud.google.com/bigquery/docs/partitioned-tables), [clustering BigQuery](https://cloud.google.com/bigquery/docs/clustered-tables), [micro-partitions Snowflake](https://docs.snowflake.com/en/user-guide/tables-clustering-micropartitions).

# Как загружать batch, streaming и CDC-данные в аналитическое хранилище?

Batch обычно загружают из файлов или пакетных jobs, streaming — через поддерживаемый API непрерывного приёма. Для Snowflake возможны bulk load, Snowpipe и streaming-механизмы; для BigQuery — load jobs и Storage Write API. Конкретный путь выбирают по свежести, объёму и стоимости.

CDC должен переносить не только insert, но и изменения, удаления, порядок и schema evolution. Сохраняют source position, event time и ingestion time. Наличие строки в raw landing ещё не означает обновления всех витрин. [Storage Write API](https://cloud.google.com/bigquery/docs/write-api), [Snowflake loading](https://docs.snowflake.com/en/user-guide/data-load-overview).

# Как обеспечить идемпотентную загрузку и дедупликацию аналитических событий?

У каждой записи есть стабильный event ID или бизнес-ключ с версией; загрузчик хранит прогресс и обрабатывает повторы по явному контракту. Часто используют raw landing и последующий детерминированный dedup/MERGE, проверяя дубли уже внутри входного batch.

Гарантии конкретного ingestion API имеют область: default stream BigQuery — at-least-once, а offset-механизмы других streams не являются глобальной бизнес-дедупликацией. Объявленный primary key не следует считать автоматически enforced: возможности BigQuery, стандартных и hybrid tables Snowflake различаются. [Ключи BigQuery](https://cloud.google.com/bigquery/docs/primary-foreign-keys), [constraints Snowflake](https://docs.snowflake.com/en/sql-reference/constraints-overview).

# Как JOIN, фильтры и выбор столбцов влияют на стоимость и время аналитического запроса?

Выбирают нужные столбцы, фильтруют по подходящим partition/clustering keys и избегают ненужного размножения строк при JOIN. Предварительная агрегация иногда уменьшает shuffle, но её корректность зависит от cardinality и бизнес-смысла.

`LIMIT` после большого scan не обязательно уменьшает прочитанные данные. В BigQuery on-demand важен объём обработанных данных, в capacity-based и Snowflake — также использование compute и конкуренция. Любую оптимизацию проверяют планом и фактическими метриками, сохраняя результат запроса. [Оптимизация BigQuery](https://cloud.google.com/bigquery/docs/best-practices-performance-compute).

# Как читать query plan и отличать сканирование, shuffle, spill и ожидание compute?

Смотрят bytes/partitions scanned, строки на входе и выходе операторов, время stages, redistribution/shuffle и spill. Большое увеличение числа строк после JOIN может объяснить расходы лучше, чем размер исходной таблицы.

Отделяют execution от ожидания capacity, compilation и очереди. В BigQuery исследуют query stages и slot usage, в Snowflake — Query Profile/History и warehouse load. Число scanned bytes не объясняет все CPU-heavy вычисления. Сравнивают запросы на одинаковых данных и явно учитывают cache hit. [Snowflake query activity](https://docs.snowflake.com/en/user-guide/ui-query-profile).

# Чем materialized views, query result cache и предварительные агрегаты отличаются по гарантиям?

Query result cache повторно использует готовый результат при выполнении условий платформы, а не поддерживает произвольную витрину по расписанию. Materialized view хранит производное представление с поддерживаемой системой логикой обновления. Предварительная агрегатная таблица обычно имеет собственный pipeline и checkpoint свежести.

У механизмов различаются ограничения SQL, invalidation, доступ и стоимость refresh. Изменение источника или недетерминированная функция может исключить cache hit. Свежесть проверяют по фактическому контракту, а не только TTL. [Cache BigQuery](https://cloud.google.com/bigquery/docs/cached-results), [persisted results Snowflake](https://docs.snowflake.com/en/user-guide/querying-persisted-results).

# Как управлять доступом к datasets, schemas, строкам и чувствительным столбцам?

Разделяют роли загрузки, трансформации, BI и администрирования, выдавая доступ к нужным datasets или schemas и объектам. Для строк используют поддерживаемые row access policies, для чувствительных столбцов — column-level control или masking в зависимости от платформы и редакции.

Проверяют service accounts/roles, экспорт, shared datasets, views и производные таблицы: ограничение исходника не всегда автоматически переносит нужную policy на копию. Тестируют отрицательные сценарии разными identity. [Row-level security BigQuery](https://cloud.google.com/bigquery/docs/row-level-security-intro), [row access Snowflake](https://docs.snowflake.com/en/user-guide/security-row-intro).

# Как time travel, snapshots и клонирование помогают восстановлению и тестированию данных?

Time travel позволяет читать или восстанавливать поддерживаемое прошлое состояние внутри настроенного retention window. Snapshots и clones фиксируют состояние для восстановления или проверки; writable clone удобен для изолированных изменений, но имеет собственные ограничения и расходы хранения.

В Snowflake доступный retention зависит от edition и типа объекта, в BigQuery также действуют настройки и ограничения времени. Эти механизмы не заменяют весь disaster recovery plan: права, региональные риски и срок хранения проверяют отдельно. [BigQuery time travel](https://cloud.google.com/bigquery/docs/time-travel), [BigQuery clones](https://cloud.google.com/bigquery/docs/table-clones-intro), [Snowflake Time Travel](https://docs.snowflake.com/en/user-guide/data-time-travel).

# Как сравнивать BigQuery и Snowflake по полной стоимости, свежести данных и требованиям команды?

Сравнивают одинаковый набор данных, queries, конкурентность и требуемую свежесть, отдельно измеряя холодный и кэшированный запуск. Учитывают compute, storage, ingestion, maintenance, history, transfer, BI и операционную поддержку, а не только цену одного запроса.

Важны существующее облако, identity, инструменты команды, SQL-совместимость и доступные интеграции. Целевой критерий — стоимость нужного результата при заданной задержке и достоверности данных. Конкретные тарифы, editions и региональные возможности проверяют на дату расчёта; один синтетический benchmark не определяет выбор.
