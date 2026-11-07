# Как модель выполнения команд Redis влияет на latency и выбор дорогих операций?

В типичной архитектуре Redis Open Source выполнение обычных команд над keyspace в основном последовательно, хотя network I/O и фоновые задачи могут использовать другие threads или процессы. Поэтому одна дорогая команда или длительный script способны задержать несвязанные обращения к тому же экземпляру.

Учитывают сложность, размер values и количество возвращаемых элементов. `KEYS` на большом keyspace и чтение огромной коллекции опаснее небольшого bounded запроса; `SCAN` позволяет дробить обход, но не создаёт согласованный snapshot. Pipelining уменьшает сетевые round trips, а не стоимость команды. Детали threading и modules сверяют с версией и продуктом. [Latency](https://redis.io/docs/latest/operate/oss_and_stack/management/optimization/latency/).

# Как выбирать Redis Strings, Hashes, Lists, Sets, Sorted Sets и Streams по операциям?

`String` хранит байты и подходит для небольших values и атомарных counters. `Hash` представляет поля объекта. `List` — упорядоченную последовательность с операциями на концах. `Set` удобен для уникальности и проверки принадлежности. `Sorted Set` связывает уникальный member с score для рейтингов и диапазонов.

`Stream` хранит записи с IDs и поддерживает чтение и consumer groups. Выбирают структуру по нужным операциям и их сложности, а не по привычному JSON-представлению. Большая коллекция под одним ключом остаётся hot key и не делится автоматически между shards. Для queue-сценария отдельно проектируют acknowledgements и восстановление.

# Как expiration, eviction и maxmemory определяют поведение Redis при нехватке памяти?

**Expiration** делает ключ недоступным после TTL; физическое удаление происходит при обращении и фоновом обслуживании. **Eviction** удаляет подходящие ключи из-за превышения memory budget. Политики `allkeys-*` рассматривают все ключи, `volatile-*` — ключи с TTL; LRU и LFU используют приближённые оценки.

При `noeviction` Redis отклоняет команды, которым нужна дополнительная память, сохраняя возможность многих чтений. `maxmemory` не равен полному RSS процесса: нужен запас на buffers, fragmentation и background persistence. Для ценных данных и кэша часто требуются разные instances и политики. [Key eviction](https://redis.io/docs/latest/develop/reference/eviction/).

# Чем Redis pipelining отличается от MULTI/EXEC, WATCH и Lua-скрипта?

**Pipelining** отправляет несколько команд без ожидания каждого ответа, уменьшая RTT; изоляцию от других клиентов оно не даёт. `MULTI/EXEC` выполняет накопленные команды последовательно без вклинивания чужих команд. `WATCH` позволяет отменить `EXEC`, если отслеживаемые ключи изменились, реализуя optimistic concurrency.

Lua-script выполняет логику рядом с данными и может объединять чтение, проверку и запись без такого interleaving. При этом Redis transaction и script не предоставляют SQL-подобного rollback уже сделанных изменений при runtime error. Script должен быть коротким, а Redis Cluster ограничивает multi-key операции совместимым размещением ключей. [Transactions](https://redis.io/docs/latest/develop/using-commands/transactions/).

# Как RDB и AOF различаются по восстановлению, потере данных и стоимости записи?

`RDB` сохраняет snapshot: он удобен для компактной копии и восстановления, но изменения после последнего snapshot могут потеряться. `AOF` журналирует изменения; фактическая долговечность зависит от политики `fsync`. При `everysec` возможна потеря недавних записей, обычно порядка секунды, а сбои и настройки могут расширить окно.

Сохранение RDB и rewrite AOF требуют I/O и ресурсов, включая copy-on-write память при фоновой работе. Совместное использование механизмов не заменяет внешнюю копию и restore drill. Выбор связывают с допустимой потерей, временем загрузки и latency записи. [Redis persistence](https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/).

# Какие гарантии даёт Redis replication и почему WAIT не делает Redis строго согласованным?

Обычная Redis replication асинхронна: primary может подтвердить запись до получения её replicas. Чтение с replica допускает stale data, а failover может потерять подтверждённую запись. Репликация повышает доступность и распределяет чтения, но не является резервным копированием.

`WAIT` на том же соединении ждёт подтверждения получения предыдущих записей указанным количеством replicas либо timeout и возвращает фактически достигнутое число. Его обязательно проверяют. Это улучшает вероятность сохранения, но не создаёт consensus и не гарантирует сохранение записи при любом failover или её `fsync` на дисках. [Replication](https://redis.io/docs/latest/operate/oss_and_stack/management/replication/), [WAIT](https://redis.io/docs/latest/commands/wait/).

# Чем Redis Sentinel отличается от Redis Cluster при отказах и масштабировании?

**Sentinel** наблюдает за нешардированным primary/replica deployment, координирует failover и помогает клиенту найти новый primary. Он не распределяет keyspace между несколькими primaries. Для выбора и авторизации failover важны quorum и доступное большинство Sentinel processes.

**Redis Cluster** делит keyspace на slots между primaries, использует replicas для failover и требует cluster-aware клиента. Он добавляет горизонтальное распределение данных, но усложняет multi-key операции и обработку topology changes. Ни Sentinel, ни Cluster не устраняют ограничения асинхронной репликации. Размещают компоненты по failure domains и проверяют сетевые разделения. [Sentinel](https://redis.io/docs/latest/operate/oss_and_stack/management/sentinel/).

# Как hash slots, hash tags, MOVED и ASK влияют на клиент Redis Cluster?

Redis Cluster распределяет ключи по **16384 hash slots**. Обычно slot вычисляется по ключу; непустой hash tag в фигурных скобках позволяет связать ключи, например `{user:42}:profile` и `{user:42}:limits`, с одним slot. Это помогает multi-key операциям, но чрезмерное объединение создаёт горячий shard.

`MOVED` указывает актуального владельца slot и повод обновить routing cache. `ASK` используется при миграции: запрос временно перенаправляют с `ASKING`, не считая это постоянной сменой владельца. Клиент должен поддерживать эти ответы, discovery и ограниченные retries. Возможности cross-slot операций зависят от команды и deployment. [Cluster specification](https://redis.io/docs/latest/operate/oss_and_stack/reference/cluster-spec/).

# Как безопасно использовать Redis для временной блокировки с учётом истечения lease?

Базовый lease получают атомарным `SET lock_key unique_token NX PX timeout`. Освобождение и продление выполняют атомарно с проверкой token, чтобы старый владелец не удалил lease нового. Timeout и задержки сети учитывают в доступном времени работы. [Redis: Distributed Locks](https://redis.io/docs/latest/develop/clients/patterns/distributed-locks/).

Истечение lease не останавливает процесс: после паузы он может продолжить устаревшую запись. Для строгой защиты ресурс должен проверять fencing token или версию из источника с нужными гарантиями. Обычный Redis counter при failover не гарантирует такую монотонность. Для критичного инварианта используют constraints или подходящий coordination service; lease не заменяет идемпотентность.

# Как искать причины Redis latency через SLOWLOG, latency monitoring и метрики?

Начинают с client end-to-end latency и разделяют ожидание pool, сеть, выполнение на сервере и передачу большого ответа. `SLOWLOG` фиксирует дорогие выполнения команд, исключая network I/O, поэтому пустой slowlog не доказывает отсутствие проблемы. Latency monitoring помогает сопоставить задержки с внутренними событиями.

Проверяют CPU, memory, fragmentation, evictions, big keys, hot keys, fork, persistence I/O, swap и replication lag. Длинные scripts и большие pipelines могут увеличивать ожидание соседних клиентов. Измерения собирают в момент симптома и подтверждают улучшение под прежней нагрузкой. [Diagnosing latency issues](https://redis.io/docs/latest/operate/oss_and_stack/management/optimization/latency/).

