# Чем Core NATS отличается от JetStream по хранению, replay и гарантиям доставки?

**Core NATS** предоставляет быстрый обмен с at-most-once delivery в своей модели: сообщение не сохраняется для offline subscriber и не получает автоматический replay. **JetStream** добавляет streams, persistence, consumer state и acknowledgment/redelivery по выбранной configuration.

Это разные требования к durability и эксплуатации, а не просто включение более надёжного socket. Retention, storage, replication и правила consumer определяют, что переживёт сбой. Даже брокерная дедупликация и подтверждение обработки не делают произвольный внешний бизнес-эффект exactly-once без дополнительного протокола. [Core NATS](https://docs.nats.io/learn/core-nats).

# Как subjects, wildcard subscriptions и queue groups маршрутизируют сообщения в NATS?

**Subjects** — имена маршрутизации с разделяемыми tokens. `*` соответствует одному token, а завершающий `>` — последующим tokens по правилам NATS. Subscribers могут подписываться на конкретный subject или допустимый wildcard.

**Queue group** распределяет сообщение между подходящими участниками одной группы, тогда как независимые subscriptions или другие группы могут получить собственную доставку. Это позволяет масштабировать workers без ручного назначения каждому отдельного subject. Core queue group не создаёт долговременную очередь для отсутствующих участников. Subject hierarchy и permissions проектируют вместе, чтобы wildcard не открыл лишние данные.

# Как JetStream stream и durable consumer задают retention, acknowledgment и redelivery?

**Stream** определяет сохраняемые subjects, storage, replication и retention policy. **Durable consumer** сохраняет позицию и acknowledgment state, поэтому клиент может продолжить предусмотренное чтение после reconnect вместо создания независимого transient progress.

Ack policy, `AckWait`, backoff и ограничения pending задают повторную доставку и flow control. При истечении ожидания одна работа может выполняться повторно. Retention policies Limits, Interest и WorkQueue имеют разную семантику удаления; ограничения возраста и объёма тоже учитывают. Durable consumer не означает бессрочное хранение любого неуспевшего сообщения. [JetStream retention](https://docs.nats.io/learn/jetstream/retention-policies), [pull consumers](https://docs.nats.io/learn/jetstream/pull-consumers).

# Как Redis Streams хранит entries и чем XREAD отличается от consumer groups?

**Redis Stream** хранит упорядоченные entries с ID и field/value данными. `XREAD` позволяет читать после позиции, которую клиент отслеживает сам; несколько независимых читателей могут читать один набор.

**Consumer group** добавляет общее состояние доставки через `XREADGROUP`: новые entries распределяются между consumers группы, а разные groups ведут независимый progress. ID задаёт порядок внутри stream, но не глобальную причинность между разными streams. Durability зависит от persistence и replication Redis, а не только от факта успешного `XADD`. [Redis Streams](https://redis.io/docs/latest/develop/data-types/streams/).

# Как pending entries list, XACK и XAUTOCLAIM поддерживают восстановление Redis Streams consumer?

**Pending entries list**, или PEL, учитывает доставленные группе, но ещё не подтверждённые entries. `XACK` снимает соответствующее pending-состояние, но не является обычным удалением самого сообщения из stream.

`XAUTOCLAIM` позволяет перевести достаточно долго idle pending entries другому consumer с cursor-based обходом. Idle threshold не доказывает, что прежний worker умер: он может возобновить работу. Поэтому бизнес-эффект должен выдерживать повтор. Контролируют PEL size, возраст и число доставок; поддержку команды и детали обработки удалённых entries проверяют по версии Redis. [XAUTOCLAIM](https://redis.io/docs/latest/commands/xautoclaim/).

# Как retention и trimming Redis Streams согласовать с отстающими consumers?

Trimming ограничивает stream по длине, ID или доступным правилам версии, чтобы память и storage не росли бесконечно. Но агрессивное удаление может убрать данные, которые отстающая group ещё не обработала или должна перечитать.

Согласуют retention с максимальным допустимым lag и временем восстановления. Проверяют, что происходит с pending references и payloads при выбранном trim-режиме; новые ack-aware возможности нельзя предполагать в старых versions. Если нужен replay глубже retention, предусматривают другой источник. Одна только метрика общего stream length не показывает состояние всех consumer groups.

# Как BullMQ использует queue, worker, job ID и retries для фоновых задач?

**Queue** хранит jobs и их lifecycle, **worker** получает и обрабатывает их. В обычной Redis-backed configuration BullMQ использует Redis для coordination и состояния; точный backend и возможности уточняют для установленной версии.

**Job ID** помогает избегать повторного добавления в пределах заданных правил queue, пока сохраняется необходимая identity. Удаление завершённой job может изменить возможность повторного добавления того же ID. Retries задают attempts и backoff для failures. Ни ID, ни retry policy не заменяют идемпотентность платежа или другого внешнего действия. [BullMQ retries](https://docs.bullmq.io/guide/retrying-failing-jobs).

# Почему BullMQ job становится stalled и как это связано с lock renewal и повторной обработкой?

Работающий worker поддерживает lock активной job. Если lock не продлён вовремя из-за crash, network failure или блокировки event loop, job может быть обнаружена как **stalled** и возвращена к обработке либо завершена ошибкой по правилам configuration.

Прежний handler мог уже выполнить часть эффекта и даже продолжить после паузы, поэтому повтор возможен. CPU-heavy код отделяют от управляющего event loop подходящим способом, а lock timings выбирают по нагрузке. Бесконечное увеличение lock duration только задерживает восстановление после реального отказа. [Stalled jobs](https://docs.bullmq.io/guide/jobs/stalled).

# Как SQS Standard использует visibility timeout и delete для обработки сообщений?

При получении **SQS Standard** сообщение временно скрывается на **visibility timeout**, но остаётся в queue. После успешной обработки consumer удаляет его с подходящим receipt handle. Если обработка не закончилась, timeout может потребовать продления.

При сбое или истечении visibility сообщение доступно для повторной доставки. Standard допускает duplicates и best-effort ordering, поэтому handler должен быть идемпотентным. Слишком короткий timeout вызывает параллельные повторы, слишком длинный задерживает восстановление. Visibility не является атомарной транзакцией с БД приложения. [Visibility timeout](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-visibility-timeout.html), [at-least-once](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/standard-queues-at-least-once-delivery.html).

# Какие гарантии SQS FIFO зависят от message group, deduplication и действий consumer?

**SQS FIFO** упорядочивает сообщения в пределах **message group**, а не задаёт один неизбежный порядок для всех независимых groups. Несколько groups позволяют параллелизм. Consumer должен сохранять нужный порядок бизнес-эффектов и не нарушать его собственной параллельной обработкой batch.

Deduplication на публикации действует по предусмотренному ID или content-based правилу в ограниченном окне. Она не отменяет повтор обработки после сбоя consumer между внешним эффектом и delete. Поэтому выражение exactly-once в документации FIFO нельзя без уточнения переносить на произвольную запись в стороннюю БД. [SQS FIFO](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/FIFO-queues-exactly-once-processing.html).

# Как SNS fan-out и SNS-to-SQS subscriptions разделяют публикацию и независимую обработку?

**SNS** публикует событие нескольким subscriptions, а отдельная **SQS queue** на потребителя сохраняет его для независимой обработки. Так медленный analytics consumer не обязан задерживать worker уведомлений, если они читают разные queues.

Настраивают subscription filter, queue access policy и при необходимости encryption permissions. Ошибка доставки SNS в subscription и ошибка обработки уже принятого SQS-сообщения — разные этапы с разными retry/DLQ настройками. Общее событие не становится общей транзакцией всех подписчиков; их progress и последствия отслеживают отдельно. [SNS-to-SQS fan-out](https://docs.aws.amazon.com/sns/latest/dg/sns-sqs-as-subscriber.html).

# Как выбирать и эксплуатировать эти инструменты с учётом durability, backpressure и восстановления?

Сначала задают durable backlog, replay, ordering scope, допустимые duplicates, ожидаемую нагрузку и способ эксплуатации. Core NATS подходит иной модели, чем persisted stream, job queue или managed SQS; сравнение только по latency публикации неполно.

Проверяют storage recovery, failover, limits, age of oldest message, worker throughput и стоимость operational burden. Backpressure ограничивает вход и concurrency до перегрузки зависимостей. В тестах останавливают worker после эффекта до acknowledgment и проверяют recovery. Backup или persistence broker state не заменяет согласование уже выполненных бизнес-операций.
