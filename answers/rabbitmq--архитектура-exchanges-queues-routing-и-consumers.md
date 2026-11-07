# Как connection, channel, exchange, binding и queue связаны в RabbitMQ?

Для AMQP 0-9-1 `connection` — сетевое соединение с брокером, а `channel` — лёгкий логический канал внутри него. Через channel клиент публикует сообщения в **exchange**, который по своим правилам и **bindings** выбирает queues. Consumer подписывается на queue и получает доставленные сообщения.

Одна публикация может попасть в несколько queues; consumers одной queue обычно делят работу, а отдельные queues получают независимые копии. Topology и права изолируются через virtual hosts. Channels переиспользуют, но модель совместного доступа и восстановления соединений берут из документации конкретной клиентской библиотеки.

# Как direct, topic, fanout и headers exchanges маршрутизируют сообщения RabbitMQ?

`Direct` сопоставляет routing key с binding key по точному совпадению. `Topic` сопоставляет разделённые точками слова: `*` заменяет одно слово, `#` — ноль или несколько. `Fanout` отправляет копию во все связанные queues, игнорируя routing key. `Headers` сопоставляет header values с условиями binding.

Например, binding `orders.*.created` подходит для `orders.eu.created`. Default exchange с именем `""` автоматически связан с queues по их именам. Маршрутизация не означает обработку сообщения, а отсутствие подходящего binding требует отдельного контроля. [RabbitMQ: Exchanges](https://www.rabbitmq.com/docs/exchanges).

# Как durable queues, persistent messages и publisher confirms участвуют в надёжной публикации RabbitMQ?

`Durable` queue сохраняет своё объявление при перезапуске, а persistent delivery mode задаёт сохранение сообщений там, где это имеет значение для выбранного типа queue. Одного успешного вызова publish в клиенте недостаточно: данные могут ещё находиться в buffers или не быть надёжно приняты брокером.

**Publisher confirms** позволяют дождаться broker acknowledgement. Для persistent messages в durable queues подтверждение учитывает сохранение, а для quorum queues — принятие кворумом. При обрыве связи до получения confirm результат может быть неопределённым: повторная публикация создаёт дубли. Поэтому нужны message IDs и дедупликация. [Confirms](https://www.rabbitmq.com/docs/confirms).

# Почему publisher confirm не заменяет mandatory routing и consumer acknowledgement в RabbitMQ?

Publisher confirm сообщает о завершении брокером соответствующего этапа публикации, но **unroutable message тоже может получить положительный confirm**. Для обнаружения отсутствия маршрута используют `mandatory` и обрабатывают `basic.return`; альтернативой в topology может быть alternate exchange.

`Consumer acknowledgement` подтверждает обработку отдельной доставки на стороне consumer и не связан с publisher confirm. Надёжная цепочка отдельно контролирует маршрутизацию, принятие брокером и бизнес-результат. Отсутствие возврата или получение confirm не доказывает, что заказ обработан. [RabbitMQ: Consumer Acknowledgements and Publisher Confirms](https://www.rabbitmq.com/docs/confirms).

# Как manual acknowledgements, nack и prefetch управляют RabbitMQ consumer?

При manual ack consumer подтверждает доставку после успешного завершения нужного действия. `Nack` или `reject` могут вернуть сообщение в очередь либо отклонить без requeue; при настроенном DLX последнее может запустить dead-lettering. После закрытия channel неподтверждённые deliveries обычно становятся доступны для повторной доставки.

`Prefetch` ограничивает число выданных неподтверждённых сообщений: слишком большой лимит увеличивает память и неравномерное распределение, слишком маленький снижает throughput при заметном RTT. Delivery tags относятся к channel; подтверждать их нужно там, где получена доставка. Auto ack не обеспечивает повтор после сбоя обработчика. [Acknowledgements](https://www.rabbitmq.com/docs/confirms).

# Чем quorum queues RabbitMQ отличаются от classic queues и streams?

**Quorum queue** — durable replicated queue на основе Raft: для нормального продвижения требуется большинство её членов. Она подходит для надёжной очереди задач, но требует сети, диска и правильно выбранных failure domains. Потеря кворума останавливает обслуживание, чтобы сохранить гарантии.

В RabbitMQ 4.x classic queues не реплицируются через прежнее mirroring: оно удалено начиная с 4.0. **Streams** — реплицируемый журнал с retention и чтением по offsets, пригодный для replay и большого потока. Выбор делают по модели потребления и восстановления, а не только по скорости публикации. [Quorum Queues](https://www.rabbitmq.com/docs/quorum-queues).

# Какие гарантии порядка сохраняются в RabbitMQ при нескольких consumers и redelivery?

Очередь выдаёт сообщения с учётом правил FIFO, но порядок публикаций разных channels нельзя считать единым глобальным порядком. При нескольких consumers сообщения выполняются с разной скоростью, поэтому порядок завершения отличается от порядка доставки. Requeue, redelivery и priorities также меняют наблюдаемую последовательность.

Для строгой последовательности по entity используют маршрутизацию связанных событий в один последовательный поток и проверяют версии или sequence numbers. Single active consumer помогает ограничить активных получателей, но сам по себе не устраняет параллельность внутри приложения и повторы после сбоев. [RabbitMQ: Message Ordering](https://www.rabbitmq.com/docs/queues#message-ordering).

# Как построить ограниченные retries и dead-letter обработку в RabbitMQ?

Временные ошибки повторяют с задержкой, ограничением числа попыток и общим deadline. Немедленный `nack(requeue=true)` без условий может создать горячий цикл. Применяют retry queues с TTL и DLX либо проверенный механизм отложенной доставки, совместимый с версией брокера. Неисправимые сообщения направляют в отдельную queue для разбора.

DLX — exchange, а не сама «очередь ошибок». Обычное dead-lettering не всегда защищено publisher confirms; для нужных гарантий отдельно настраивают поддерживаемое quorum queues at-least-once dead-lettering. Контролируют routing, доступность назначения и повторную обработку. [Dead Letter Exchanges](https://www.rabbitmq.com/docs/dlx).

# Как RabbitMQ consumers согласуют изменение БД, ack и повторную доставку?

Если consumer сначала отправит ack, а потом упадёт до commit БД, задача может потеряться. Если сначала commit, а затем ack, сбой между ними вызовет повторную доставку. Брокер и БД не становятся одной транзакцией от перестановки этих двух действий.

Типичный порядок: в одной DB transaction записать уникальный event ID в inbox и выполнить бизнес-изменение, затем commit и ack. При повторе unique constraint позволяет распознать уже выполненное событие. Для внешних side effects нужен отдельный идемпотентный протокол или outbox. Флаг redelivered помогает диагностике, но не заменяет устойчивую дедупликацию.

# Как диагностировать рост очереди, unacked messages и resource alarms в RabbitMQ?

Сопоставляют publish rate, delivery rate, ack rate, `messages_ready`, `messages_unacknowledged` и возраст работы. Рост ready при малом unacked может означать отсутствие или нехватку consumers; большой unacked — долгую обработку, зависание или чрезмерный prefetch. Проверяют ошибки consumers, downstream latency, redeliveries и использование CPU, диска и памяти.

Memory и disk alarms могут блокировать publishing connections для защиты брокера. Увеличение watermarks без устранения причины опасно: backlog продолжает расти. Нужны конечный retention или capacity plan, защита admission и проверка восстановления очереди. [Monitoring](https://www.rabbitmq.com/docs/monitoring), [Resource Alarms](https://www.rabbitmq.com/docs/alarms).

