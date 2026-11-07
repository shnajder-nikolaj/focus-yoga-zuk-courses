# Как Prometheus scrape, exporters, service discovery и time series labels формируют metrics pipeline?

В обычной **Prometheus pull-модели** сервер обнаруживает targets, получает metrics через scrape и сохраняет samples как time series с labels. **Exporter** адаптирует состояние системы к поддерживаемому exposition format; application также может публиковать собственные metrics напрямую.

Service discovery и relabeling определяют, что именно будет опрошено и с какой identity. Label set отличает series, поэтому случайные IDs создают cardinality explosion. Проверяют scrape interval, timeout и reachability. Наличие target в configuration не подтверждает успешный scrape или корректность бизнес-метрики.

# Как rate, increase и aggregation в PromQL учитывают counter resets и разбиение по instances?

Для **counter** `rate` оценивает скорость роста, учитывая предусмотренные resets, а `increase` оценивает прирост на окне с extrapolation; результат не обязан быть целым числом. Gauge требует иной interpretation.

Обычно сначала вычисляют rate каждой instance series, затем агрегируют нужные labels: раннее объединение counters может скрыть resets отдельного process. Окно должно содержать достаточно samples, а missing data не автоматически равно нулю. Проверяют labels после rollout и границы aggregation, чтобы не объединить unrelated services. [PromQL functions](https://prometheus.io/docs/prometheus/latest/querying/functions/).

# Как recording rules и histogram queries помогают строить быстрые и корректные dashboards?

**Recording rule** заранее вычисляет и сохраняет expression, уменьшая query cost часто используемых views. Но она фиксирует семантику и labels, поэтому неверная aggregation распространяет ошибку на dashboards и alerts.

Для classic histogram сначала корректно агрегируют bucket rates с сохранением `le`, затем вычисляют quantile. Усреднение готовых instance p99 не даёт общий p99. Native histograms используют другую модель query и требуют поддержки всей цепочки. Rules проверяют на resets, low traffic и missing series, а не только на обычном графике. [Recording rules](https://prometheus.io/docs/prometheus/latest/configuration/recording_rules/), [histograms](https://prometheus.io/docs/practices/histograms/).

# Как retention, local TSDB и remote write связаны с восстановлением и масштабированием metrics?

**Local TSDB** хранит recent time series, WAL помогает восстановить предусмотренные незавершённые данные после restart, а retention ограничивает объём или длительность хранения. Несколько writers не объединяют произвольно одной writable data directory.

**Remote write** передаёт samples внешнему backend, но queue, retry и доступная история ограничены: длительный outage способен вызвать потерю. HA replicas и remote storage требуют собственной deduplication и capacity-модели. Сохраняют configuration и правила отдельно от raw data, проверяют restore и свободный disk. [Prometheus storage](https://prometheus.io/docs/prometheus/latest/storage/).

# Как Grafana data sources, variables и dashboards отделяют визуализацию от хранения данных?

**Grafana data source** описывает подключение к backend и query API, а dashboard задаёт визуализацию. Variables параметризуют query и navigation. В обычной архитектуре наличие dashboard не означает, что raw telemetry хранится в Grafana metadata database.

Units, time range, aggregation и transformations могут сделать даже правильные данные вводящим в заблуждение графиком. Проверяют permissions на backend и datasource, не полагаясь только на скрытую panel. Configuration и dashboard versions хранят управляемо; секреты подключения не публикуют в exported artifacts. [Grafana data sources](https://grafana.com/docs/grafana/latest/datasources/).

# Как Loki labels и LogQL отличаются от полнотекстовой индексации Elasticsearch в ELK?

**Loki** прежде всего индексирует labels log streams и хранит log content в chunks; **LogQL** сочетает выбор streams и дальнейшую обработку logs. Дополнительные acceleration mechanisms зависят от версии и configuration.

**Elasticsearch** в ELK поддерживает индексирование содержимого и fields по mappings, а Logstash/Kibana решают ingest и exploration задачи в соответствующей схеме. Различие меняет storage, query cost и требования к label/index design. В Loki request ID обычно не превращают в бесконечно меняющийся stream label. Ни одна модель не устраняет необходимость retention и sizing. [Loki labels](https://grafana.com/docs/loki/latest/get-started/labels/).

# Как parsing, structured fields и index или stream design влияют на поиск logs?

Logs разбирают в согласованную структуру: timestamp, service, severity, event и identifiers. **Parsing** должен обрабатывать malformed records, multiline exceptions и schema changes без молчаливой потери данных.

В Elasticsearch field types и mappings влияют на точные filters, full-text search и aggregations; uncontrolled dynamic fields создают mapping explosion. В Loki выбирают ограниченные labels и подходящие structured fields или query-time parsing. Clock и timezone нормализуют. Сопоставляют sample raw log с фактически сохранённым record, чтобы обнаружить неверную extraction, а не только красивый dashboard. [Elastic Common Schema](https://www.elastic.co/docs/reference/ecs).

# Как Jaeger получает traces и какие ограничения задают sampling и storage?

**Jaeger** принимает traces через поддерживаемый ingest pipeline и предоставляет querying и visualization поверх configured storage. В архитектуре v2 используется настраиваемая role/pipeline-модель; старый tutorial с обязательным отдельным agent не следует переносить без проверки версии.

Sampling определяет coverage ещё до поиска, storage и retention — что осталось доступным. Отсутствующий trace может означать dropped data, неверное context propagation или sampling, а не отсутствие операции. Неполные spans и clock skew ограничивают анализ critical path. Проверяют ingest, exporter errors и search fields. [Jaeger architecture](https://www.jaegertracing.io/docs/latest/architecture/).

# Как Alertmanager grouping, deduplication, inhibition и silence управляют уведомлениями?

**Grouping** объединяет связанные alerts в удобное notification, **deduplication** уменьшает повтор одних и тех же уведомлений, **inhibition** подавляет подходящие зависимые alerts при наличии определённого source alert. **Silence** временно отключает notifications по matchers.

Эти действия не исправляют underlying condition и не заменяют запись состояния. У silence задают owner, reason и срок, а inhibition проверяют на слишком широкое совпадение. Routing tree должен отправлять actionable notification нужной команде. Пустой mailbox после изменения rules не доказывает, что система выздоровела. [Alertmanager](https://prometheus.io/docs/alerting/latest/alertmanager/).

# Как pending period и multi-window burn-rate alerts уменьшают шум без сокрытия инцидентов?

**Pending period**, например `for`, требует сохранять условие для соответствующей series заданное время до firing, уменьшая реакцию на короткий шум. Изменение labels или исчезновение данных может повлиять на это ожидание.

**Burn rate** связывает скорость ошибок с допустимым error budget SLO. Multi-window rules используют короткое и длинное окна для быстрого подтверждения существенного расхода и более устойчивого обнаружения медленной деградации. Они не являются просто длинным `for`. Проверяют low traffic, denominator и missing data; пороги выбирают по целям сервиса. [SLO alerting](https://sre.google/workbook/alerting-on-slos/).

# Как runbook, ownership и routing превращают alert в выполнимое действие?

Alert должен сообщать **влияние**, affected service, severity и полезный context, а **ownership** — определять ответственного и fallback. Routing отражает эти границы, а не отправляет все события всем командам.

**Runbook** даёт первые безопасные проверки, relevant dashboards и критерии escalation или recovery. Ссылка без актуального содержания не делает alert actionable. Отделяют срочное notification от задачи плановой оптимизации. Проверяют реальные примеры firing/resolved, изменения contact points и доступ получателя к нужным данным, не раскрывая secrets в уведомлении.

# Как наблюдать сам telemetry stack и обнаруживать scrape failures, dropped data и недоступность alert delivery?

Telemetry stack наблюдают по scrape failures, queue occupancy, dropped samples/spans/logs, ingest latency, disk и exporter errors. Отдельно проверяют evaluation rules и фактическую доставку notifications, поскольку работающий dashboard не подтверждает alert delivery.

Используют независимый heartbeat или предусмотренную end-to-end проверку, чтобы отказ общей monitoring-системы не выглядел как исчезновение всех проблем. Missing data отличают от нулевого значения. Восстановление проверяют после restart и backend outage, учитывая backlog и retention. Самонаблюдение не должно создавать бесконечный поток повторных alerts при собственной перегрузке.
