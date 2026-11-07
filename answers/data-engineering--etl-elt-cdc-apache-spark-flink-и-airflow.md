# Чем ETL отличается от ELT и как выбрать место преобразования данных?

**ETL** извлекает и преобразует данные до загрузки в целевое хранилище, **ELT** сначала загружает и выполняет преобразования средствами целевой платформы. Граница может быть смешанной: очистка опасных данных до загрузки, тяжёлая агрегация после неё.

Выбор зависит от качества источника, confidentiality, стоимости compute, объёма и возможности повторить обработку. ELT часто сохраняет полезную raw-историю, но требует контроля доступа и retention. ETL не отменяет потребность хранить lineage и объяснять, какие правила изменили данные.

# Как разделить ingestion, raw layer, transformation и serving в data pipeline?

Ingestion отвечает за надёжное получение и фиксацию входа, raw layer сохраняет исходные события или файлы с metadata, transformation формирует проверенные модели, serving предоставляет витрины и интерфейсы потребителям.

У каждого этапа определяют owner, формат, версии, checkpoint и SLA свежести. Нельзя считать pipeline успешным только по попаданию файла в raw, если бизнес-витрина ещё старая. Разделение позволяет повторить преобразование без повторного извлечения, если сохранённых данных и retention достаточно.

# Как CDC согласует начальный snapshot и дальнейшие изменения источника?

CDC должен получить согласованное начальное состояние и продолжить изменения с подходящей log position, не оставив промежутка и корректно обработав перекрытие. Конкретный connector определяет алгоритм snapshot, locks и сохранение offsets.

Сохраняют source identity, key, operation и позиции; учитывают удаления и recovery. Отставший connector может потерять доступ к нужному журналу из-за retention, а replication slot способен увеличивать хранение WAL. Snapshot и поток нельзя просто склеить по приблизительному времени. [CDC PostgreSQL Debezium](https://debezium.io/documentation/reference/stable/connectors/postgresql.html).

# Как schema evolution и изменение бизнес-смысла данных влияют на pipeline?

Добавление поля, смена типа, nullability или единиц требует согласования producers, storage и consumers. Схемный compatibility check полезен, но не обнаружит изменение смысла `amount` при прежнем numeric type.

Используют версии, явные mappings, проверки качества и quarantine для неподдерживаемых записей. Сырые данные и история schema позволяют повторить преобразование, если формат сохранён. При replay старые записи всё ещё должны интерпретироваться по их прежнему смыслу, а не молча по последней схеме.

# Чем Apache Spark и Flink отличаются по основным моделям обработки?

Spark широко используется для batch, SQL/DataFrame и распределённых преобразований; Structured Streaming выражает потоковую обработку через похожую модель и обычно micro-batches. Flink ориентирован на stateful stream processing с длительно работающими операторами, event time и state.

Оба стека имеют дополнительные режимы и развиваются, поэтому нельзя свести выбор к «Spark только batch, Flink только stream». Сравнивают latency, state, connectors, recovery и навыки команды. [Spark Structured Streaming](https://spark.apache.org/docs/latest/streaming/getting-started.html), [Flink stateful processing](https://nightlies.apache.org/flink/flink-docs-stable/docs/concepts/stateful-stream-processing/).

# Как event time, watermarks и late events участвуют в потоковом pipeline?

`Event time` отражает время события, а processing time — момент обработки. **Watermark** выражает продвижение event-time и допущение об опоздании, позволяя управлять окнами и объёмом state.

Он не доказывает, что более старые события физически невозможны. Поздние записи обрабатывают по политике: обновляют результат, отправляют отдельно или отклоняют с учётом допустимого lateness. Слишком агрессивный watermark теряет полноту, слишком медленный удерживает state. Неактивная partition также влияет на общий прогресс.

# Как checkpoints, replay и sink semantics определяют end-to-end гарантии обработки?

Checkpoint фиксирует согласованное состояние операторов и позиции источников, чтобы после сбоя продолжить обработку через replay. Exactly-once state внутри движка ещё не означает однократный внешний эффект.

Источник должен позволять восстановить нужные позиции, а sink — согласовать commit с checkpoint либо безопасно повторять записи. HTTP-вызов без идемпотентности не становится exactly-once от включённого checkpointing. Проверяют recovery на границах отправки и подтверждения, retention и совместимость сохранённого state. [Fault tolerance Flink](https://nightlies.apache.org/flink/flink-docs-stable/docs/concepts/stateful-stream-processing/).

# Как idempotent writes, deduplication и MERGE помогают безопасному backfill?

Backfill повторно обрабатывает исторический интервал, поэтому выход должен иметь устойчивый ключ и понятную политику замены. MERGE/upsert полезен, если вход предварительно согласован по ключу и версии, а одинаковый batch не создаёт дополнительный эффект.

Само слово `MERGE` не устраняет дубли и конфликты любого dataset. Разделяют event time, ingestion time и версию преобразования, проверяют overlap с текущим потоком и прогресс. Побочные уведомления во время backfill требуют отдельного контракта, чтобы не отправить историю заново.

# Как Airflow DAG, tasks и retries организуют запуск data workflows?

Airflow описывает workflow как **DAG** из tasks и зависимостей, а scheduler определяет готовые к запуску task instances. Executor/workers выполняют задачи в выбранной архитектуре. Retries повторяют task при предусмотренном исходе.

Task должна выдерживать повтор и иметь понятный data interval, outputs и timeout. Успех соседней задачи не делает весь DAG одной транзакцией. Catch-up, backfill и зависимости между runs настраивают явно, чтобы повторный запуск не удвоил данные. [Airflow architecture](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/overview.html).

# Почему XCom и scheduler Airflow не предназначены для передачи и обработки всего dataset?

XCom передаёт небольшие результаты и metadata между tasks, например URI файла или идентификатор загрузки. Передача большого DataFrame через scheduler metadata path расходует память, storage и время сериализации.

Сам dataset размещают в подходящем storage, а tasks запускают Spark, SQL, Flink или другой compute и передают ссылки. Даже object-storage XCom backend не отменяет ограничения разумного использования. Код построения DAG также не должен выполнять тяжёлые запросы при каждом разборе scheduler. [XComs](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/xcoms.html).

# Как data quality, freshness, lineage и observability проверяют надёжность pipeline?

Проверяют schema, уникальность, диапазоны, полноту и согласование итогов, а freshness показывает возраст доступного потребителю состояния. Lineage связывает результат с источником, версиями преобразований и конкретным запуском.

Метрики должны отражать не только успешный процесс, но и правильные данные: зелёный task может записать пустую таблицу. Для отклонений задают блокировку публикации, quarantine или явное предупреждение по бизнес-контракту. При расследовании нужны source offsets, run ID и изменения объёма, без утечки чувствительного payload.

# Как учитывать data skew, shuffle, partition count и small files при масштабировании обработки?

Data skew направляет непропорционально много работы на один key/partition и задерживает весь stage. Shuffle требует сети и перераспределения, а слишком много partitions создаёт накладные расходы; слишком мало ограничивает параллелизм.

Small files увеличивают metadata и стоимость чтения, поэтому используют разумную batching/compaction политику. Проверяют распределение ключей, размеры partitions, spills и загрузку отдельных workers. Увеличение общего compute не исправляет один горячий ключ; salting или изменение агрегации должно сохранять правильность результата.
