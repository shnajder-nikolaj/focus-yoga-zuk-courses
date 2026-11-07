# Как durable message log, message ID и client retry организуют надёжную отправку сообщения в чат?

Client присваивает отправке устойчивый operation ID; сервер связывает его с subject и conversation. После authorization сообщение записывают в durable store с уникальностью этого действия и только затем подтверждают принятие в рамках обещанного durability contract.

При потере acknowledgement client повторяет тот же ID и получает исходное logical message, а не вторую копию. Публикацию real-time event связывают с записью через журнал или outbox. WebSocket обеспечивает transport, но не заменяет устойчивое хранение, app-level acknowledgements и retry protocol. [RFC 6455](https://www.rfc-editor.org/rfc/rfc6455.html).

# Как назначать порядок сообщений внутри conversation при нескольких gateways и retries?

Порядок определяют в согласованном scope, например внутри conversation. Один logical sequencer, partition leader или эквивалентный протокол назначает sequence при принятии записи. Разные conversations не обязательно требуют общего глобального порядка.

Client timestamp полезен для отображения, но не является надёжным арбитром конкурентных отправок. Повтор сохраняет исходный message ID и sequence, а failover не должен допускать старого владельца к независимому назначению конфликтующих позиций. Clients обрабатывают delayed events и получают пропущенную историю по server cursor.

# Как различать accepted, delivered и read receipts без ложных гарантий доставки?

**Accepted** означает устойчивое принятие сервером по contract. **Delivered** фиксирует выбранное подтверждение client device, например получение приложением; для нескольких устройств определяют, достаточно ли одного. **Read** означает сообщение клиента о выполнении согласованного UI-условия, а не доказательство чтения человеком.

Receipt имеет scope, ID или cursor и обновляется монотонно по правилам протокола. Push-provider acknowledgement не подтверждает ни отображение, ни прочтение. Duplicate receipts не создают новых side effects, а offline устройства могут долго оставаться без подтверждения. [FCM: Understanding delivery](https://firebase.google.com/docs/cloud-messaging/understand-delivery).

# Как session directory, presence и reconnect поддерживают несколько устройств пользователя?

Session directory связывает user и device sessions с текущими gateways. Heartbeats и leases очищают устаревшие записи; presence является приблизительным состоянием соединения и не доказывает активность человека. Несколько устройств получают события согласно выбранной fan-out policy.

При reconnect клиент заново подтверждает identity и membership, сообщает cursor и восстанавливает пропуски из durable history. Gateway memory не должна быть единственным источником сообщений. Если одна session исчезла, это не означает, что пользователь offline на всех устройствах; агрегирование presence имеет явные правила.

# Как resumable cursor и bounded buffers восстанавливают real-time stream после разрыва?

Cursor обозначает подтверждённую позицию в истории соответствующего stream. Reconnect запрашивает события после неё, а clients дедуплицируют повторные deliveries по ID. Переход между initial snapshot и live subscription должен иметь согласованную границу, чтобы не потерять событие между двумя запросами.

Per-client buffers ограничены. Медленного consumer переводят на backpressure, отключают с возможностью resume или требуют full resync после истечения retention. Нельзя молча выбросить обязательные события и продолжать обещать полную доставку. Позиции разных partitions требуют composite cursor или отдельного порядка.

# Как notification service учитывает preferences, deduplication, retries и разные каналы?

Notification intent имеет stable ID, recipient, channel, template version и связь с source event. Перед отправкой проверяют актуальные preferences, разрешённость контента, quiet hours и действительность destination. Deduplication scope учитывает смысл уведомления и канал.

Temporary failures повторяют с backoff, deadline и provider limits; permanent errors прекращают retry и обновляют адресные данные по policy. Неизвестный исход внешнего send может дать дубликат, если provider не поддерживает нужную idempotency. Внутренний status отличает queued, provider-accepted и подтверждённый delivery outcome; один `sent=true` скрывает существенные различия.

# Как fan-out on write и fan-out on read различаются при проектировании пользовательской ленты?

**Fan-out on write** при публикации обновляет materialized inboxes followers: чтение быстрое, но запись дорогая при большой аудитории. **Fan-out on read** собирает кандидатов из источников при запросе пользователя: меньше предварительной работы, больше read-time merging и ranking.

Hybrid model заранее materializes обычные источники, а очень крупных authors добавляет при чтении. Выбор зависит от отношения активных readers к publishers, размера графа и freshness. Queue backlog и повторная обработка требуют idempotent updates; materialized feed не становится authoritative store самого контента.

# Как celebrity users, ranking и pagination влияют на архитектуру feed generation?

Celebrity user создаёт огромный write fan-out, поэтому его поток часто обрабатывают отдельным путём и объединяют с уже подготовленными candidates. Ranking рассматривает ограниченный набор, иначе read latency растёт вместе со всем графом подписок.

Cursor должен соответствовать устойчивому порядку или snapshot/version ranking. Если scores меняются между страницами, возможны повторы и пропуски; это свойство явно определяют и при необходимости стабилизируют. Добавление уникального tie-breaker решает равенство значений, но не само изменение scores. Измеряют стоимость candidate generation отдельно от scoring.

# Как удаление контента и изменение membership распространяются в чатах, лентах и push?

Delete или membership change записывают в authoritative state и распространяют в materialized inboxes, search, caches и connected clients через versioned events. Read path проверяет текущие ограничения, чтобы lag фонового удаления не оставил доступ к уже запрещённому объекту.

Queued push перед отправкой также проверяет допустимость; sensitive content можно не включать в push payload. Уже показанный клиенту текст нельзя гарантированно отозвать из всех внешних копий, поэтому scope удаления формулируют точно. Background cleanup, retention и восстановление из backup должны сохранять актуальные tombstones и policy.

# Как измерять freshness, delivery latency и backlog и проверять real-time систему при сбоях?

Раздельно измеряют durable acceptance latency, time-to-device, materialized-feed freshness и application-confirmed receipts. Для каждой метрики определяют начало, конец, population и handling отсутствующих подтверждений. Server publish latency не равна пользовательской delivery latency.

Проверяют потерю gateway, повтор события, reconnect storm, медленное устройство, недоступность push provider и backlog fan-out. Контролируют memory buffers, queue age, deduplication и время восстановления. Тест должен подтверждать порядок и полноту в обещанном scope, а не только количество открытых WebSockets.

