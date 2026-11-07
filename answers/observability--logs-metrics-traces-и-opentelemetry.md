# Как logs, metrics и traces отвечают на разные вопросы о работе распределённого сервиса?

**Metrics** показывают агрегированное поведение во времени, например error rate и latency distribution. **Logs** фиксируют отдельные события с context. **Traces** связывают этапы работы через сервисы и помогают исследовать конкретный путь.

Один сигнал не заменяет остальные: низкая средняя latency скрывает tail, отсутствие sampled trace не доказывает отсутствие запроса, а большой log volume не даёт готовую картину SLO. Проектируют наблюдение от пользовательских сценариев и возможных failure modes, затем связывают сигналы стабильными identifiers. [OpenTelemetry signals](https://opentelemetry.io/docs/concepts/signals/).

# Как instrumentation, OpenTelemetry API, SDK, exporter и Collector разделяют ответственность?

**Instrumentation** создаёт observations в application code или libraries. **API** задаёт интерфейс вызова, **SDK** реализует сбор, processing и нужную configuration. **Exporter** передаёт данные в поддерживаемом protocol или backend.

**OpenTelemetry Collector** принимает telemetry, преобразует и маршрутизирует её через configured pipelines; это не обязательно долговременное хранилище для поиска. Backend отвечает за storage и querying по своей модели. Автоматическая instrumentation покрывает только поддержанные interactions и может потребовать ручных spans для бизнес-операций. Проверяют versions и semantic compatibility всех компонентов. [Collector configuration](https://opentelemetry.io/docs/collector/configuration/).

# Как trace, span, parent context и span links описывают синхронную и асинхронную работу?

**Trace** объединяет связанный execution context, а **span** описывает определённую операцию с временем, attributes и status. Parent-child связь показывает выбранную причинную структуру, но не всегда всю business transaction.

**Span links** полезны для batches, messaging и нескольких источников причинности, когда один parent искажает модель. Queue delay нужно instrumentировать явно, если он важен. Duration параллельных children нельзя просто суммировать как end-to-end latency. Clock skew и потерянные spans также ограничивают вывод о порядке и критическом пути.

# Как context propagation и baggage передают correlation через HTTP и messaging?

**Context propagation** переносит trace context через поддерживаемые HTTP headers или message metadata, а instrumentation извлекает и внедряет его на границах. Async execution внутри процесса тоже должен сохранять нужный context, иначе spans распадутся на несвязанные traces.

**Baggage** переносит дополнительный context, но не является trusted authentication data и может попасть в downstream requests. Ограничивают размер, список fields и передачу через внешние boundaries. Не кладут туда credentials и персональные данные без необходимости. Context caller может быть недоверенным, поэтому policy нельзя строить только на переданном trace ID. [Propagation](https://opentelemetry.io/docs/concepts/context-propagation/).

# Как resource attributes и semantic conventions помогают сопоставлять telemetry разных сервисов?

**Resource attributes** описывают источник telemetry, например `service.name`, версию и instance context. **Semantic conventions** согласуют имена и смысл attributes разных instrumentation libraries, чтобы запросы и dashboards работали с сопоставимыми данными.

Неправильное service name объединяет несвязанные сервисы, а случайные значения создают лишнюю cardinality. Schema и conventions меняются по версиям, поэтому upgrade проверяют на dashboards, routing и rules, а не только на сборке SDK. Не переименовывают один attribute без оценки downstream pipeline. [Semantic conventions](https://opentelemetry.io/docs/concepts/semantic-conventions/).

# Как counter, gauge и histogram различаются по измеряемому поведению?

**Counter** описывает накапливаемое количество предусмотренных событий; monotonic counter не используют для произвольного уменьшения текущего состояния. **Gauge** отражает значение состояния, которое может расти и уменьшаться. **Histogram** описывает distribution observations, например durations.

В OpenTelemetry instrument и exported data model связаны через aggregation и temporality: cumulative и delta имеют разные правила интерпретации. Выбирают units и attribute set заранее. Нельзя вычислять rate gauge теми же предположениями, что monotonic counter, или считать один total достаточным для percentile latency. [OTel metrics model](https://opentelemetry.io/docs/specs/otel/metrics/data-model/).

# Как histogram buckets, percentiles и aggregation влияют на измерение tail latency?

**Histogram buckets** группируют observations по диапазонам, а percentile оценивается из distribution с соответствующей погрешностью. Если около нужного SLO слишком грубые boundaries, p99 будет недостаточно точным для решения.

Percentiles разных instances нельзя усреднить для получения общего p99. Для aggregation нужны совместимые данные histogram и единое окно; native/exponential representations имеют свои правила поддержки backend. Среднее duration не описывает tail. Проверяют units, boundaries и count, включая малый трафик и timeouts, которые instrumentation могла исключить из observations. [Histograms](https://prometheus.io/docs/practices/histograms/).

# Почему high-cardinality attributes создают разную цену в metrics, logs и traces?

В **metrics** каждый новый набор labels или attributes способен создать отдельную time series, поэтому user IDs, raw URLs и request IDs быстро увеличивают storage и query cost. Вместо произвольного URL часто используют ограниченный route pattern.

В **logs** и **traces** высокая cardinality иногда необходима для расследования, но цена зависит от indexing, retention и search design. Перенос любого field в Loki label или metrics label не является бесплатной корреляцией. Определяют cardinality budget и отдельно сохраняют нужный event context с минимальными sensitive data.

# Как head sampling и tail sampling влияют на видимость ошибок и нагрузку?

**Head sampling** решает судьбу trace в начале, часто по probability и parent context, поэтому не знает будущий error или slow span. **Tail sampling** принимает решение позже по собранным данным, например сохраняя проблемные traces.

Tail требует buffering, timeout и routing relevant spans к согласованному decision point. Поздние и потерянные spans ухудшают completeness; уже отброшенные на head данные tail sampler не восстановит. Sampling меняет coverage диагностики и может искажать derived metrics, если не учесть модель. Policy проверяют на редких, но важных failures. [Sampling](https://opentelemetry.io/docs/concepts/sampling/).

# Как structured logging, severity и trace correlation помогают исследовать конкретный запрос?

**Structured log** имеет отдельные fields для timestamp, severity, event, service и relevant context, а не только свободную строку. Trace ID и span ID, где доступны, позволяют перейти от события к execution path.

Severity отражает action и влияние по согласованным правилам: не каждый expected validation failure должен выглядеть как авария всего сервиса. Сохраняют error cause и stack, избегая многократного логирования одного exception на каждом layer. Корреляция полезна даже при sampled-out trace, но не гарантирует наличие полного trace в backend. Redaction выполняют до нежелательного распространения данных.

# Как retries, batching, memory limits и очереди Collector влияют на потерю telemetry?

**Batching** снижает overhead, но добавляет latency и данные, ещё не отправленные при crash. Sending queue и retries переживают часть временных ошибок exporter, однако имеют capacity и time limits. Persistent queue требует storage и собственной recovery policy.

Memory limiter и backpressure могут отказать или отбросить данные, а receiver acknowledgement не всегда означает их долговременное сохранение конечным backend. Наблюдают queue occupancy, retries, dropped records и exporter failures. Ограничение ресурсов Collector нужно самому сервису, чтобы telemetry outage не исчерпал весь application budget. [Collector resiliency](https://opentelemetry.io/docs/collector/resiliency/).

# Как защищать sensitive data и проверять, что instrumentation не меняет существенно работу сервиса?

Определяют allowlist нужных attributes, ограничивают payload capture, убирают credentials, cookies и лишние personal data до export. Hashing произвольного identifier не делает его автоматически безопасным и всё ещё может сохранять high cardinality.

Сравнивают application CPU, memory, latency и error behavior с instrumentation и без неё, включая outage telemetry backend. SDK queues и exporters не должны бесконечно блокировать полезную работу. Проверяют context correctness, отсутствие duplicate instrumentation и закрытие при shutdown. Access control, transport encryption и retention применяют ко всем raw artifacts, а не только dashboards.
