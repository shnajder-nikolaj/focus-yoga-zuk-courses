# Как определить API, модель данных и SLA операций создания и разрешения короткой ссылки?

Основные пути — создание mapping и разрешение code в destination. Для записи определяют authentication, custom alias, expiry, изменение ссылки и idempotency. Mapping хранит code, destination, owner, status, version и timestamps; code имеет constraint уникальности.

Read path обычно значительно горячее write path, поэтому отдельно задают latency и availability redirect, свежесть изменений и поведение при удалении. Решают, допустимо ли повторно использовать expired codes. Требования к аналитике и модерации не должны незаметно менять contract основного разрешения ссылки.

# Как выбирать короткий код между random generation, sequence и hash исходного URL?

Random code распределяет значения и усложняет перебор, но требует проверки уникальности и повторной генерации при collision. Sequence с encoding, например Base62, даёт компактный уникальный code при корректном allocator, однако раскрывает порядок и может создать bottleneck генерации.

Hash URL даёт детерминированность, но укороченный hash также сталкивается с collisions. Одинаковый URL не всегда означает одну бизнес-ссылку: owners и campaigns могут различаться. Ёмкость пространства оценивают по alphabet и length, а уникальность закрепляют атомарной записью, не предварительным lookup.

# Как кэширование, HTTP redirect status и изменение destination взаимодействуют в URL Shortener?

Redirect status выбирают по требуемой постоянности и правилам HTTP caching. Длительно закэшированный permanent redirect может продолжать вести на старый destination после изменения mapping; серверная invalidation не очищает произвольный browser cache.

Для изменяемых ссылок задают ограниченную freshness и согласованный read path. Negative cache имеет короткую допустимую устарелость, чтобы не скрывать только что созданную ссылку. При удалении или abuse block проверяют все layers. Выбор между 301, 302, 307 и 308 учитывает также семантику сохранения метода, а не только скорость. [RFC 9110: Redirection](https://www.rfc-editor.org/rfc/rfc9110.html#name-redirection-3xx).

# Как защищать URL Shortener от abuse и собирать аналитику без задержки redirect?

Creation endpoint ограничивает допустимые URL schemes, объём создания и sensitive settings. Сервису нужны правила moderation и блокировки вредоносных destinations; непрозрачный code сам по себе не делает URL безопасным. Если backend загружает preview, это отдельный путь с SSRF-защитой.

Redirect не ждёт тяжёлой аналитики: события передают в отдельный pipeline с выбранной гарантией доставки и явной политикой потери. Повторная доставка требует deduplication, а bot traffic отделяют при расчёте метрик. Собирают только необходимые данные, не превращая аналитический сбой в отказ разрешения ссылок.

# Как задать GET, PUT, DELETE, TTL и compare-and-set contract распределённого Key-Value Store?

`GET` определяет различие отсутствующего, expired и существующего значения. `PUT` задаёт replacement semantics, ограничения value и результат retry. `DELETE` определяет наблюдаемость удаления и повторного вызова. **Compare-and-set** изменяет значение только при совпадении ожидаемой revision.

Отдельно задают per-key consistency, durability после ack, TTL, atomicity и размеры операций. Linearizable CAS требует подходящего протокола владения и координации; его нельзя обещать поверх произвольного eventual read/write. Expiry по времени и физическое удаление разделяют, указывая допустимое отклонение clocks и cleanup.

# Как partitioning, replicas и routing metadata организуют хранение Key-Value Store?

Keyspace делят на partitions, для которых назначены owners и replicas. Router находит владельца по metadata или детерминированному mapping. Replicas размещают по failure domains, а replication protocol выбирают по обещанным read/write guarantees.

При rebalance сначала копируют данные и догоняют изменения, затем управляемо меняют ownership. Epoch или version metadata позволяет отклонять запросы к старому владельцу. Нужны bootstrap, membership и путь восстановления metadata. Равномерный hash не устраняет skew размера values и частоты обращений к hot key.

# Как Key-Value Store обрабатывает concurrent writes, tombstones и восстановление replicas?

Concurrent writes разрешают согласно contract: сериализуют у leader, используют version-based CAS либо допускают конфликтующие версии с определённым resolver. Last-write-wins по clocks может потерять осмысленное конкурентное изменение и не подходит для любого инварианта.

Deletion распространяют как tombstone или эквивалентное версионированное состояние. Если убрать его до синхронизации отставшей replica, старое значение может появиться снова. Repair и восстановление учитывают versions, журнал и минимально безопасную точку cleanup. Нельзя бесконечно возвращать старый узел с устаревшими данными без проверки. [Cassandra: Tombstones](https://cassandra.apache.org/doc/latest/cassandra/managing/operating/compaction/tombstones.html).

# Как определить ключи, окна и семантику квот проектируемого Rate Limiter?

Определяют subject квоты: user, tenant, API key, IP или их сочетание. Identity берут из проверенного контекста; клиент не должен обходить лимит произвольной сменой header. Далее задают временную модель, допустимый burst и cost разных операций.

Contract отвечает, какие попытки расходуют budget, когда можно повторить запрос и как меняется policy. Для HTTP quota rejection обычно используют `429` с понятным retry behaviour; перегрузка инфраструктуры и бизнес-квота могут требовать разных решений. Ограничивают cardinality хранимых ключей и срок жизни состояния. [RFC 6585: 429](https://www.rfc-editor.org/rfc/rfc6585.html#section-4).

# Как распределённый Rate Limiter атомарно расходует budget и обрабатывает отказ хранилища?

Проверка остатка и его уменьшение выполняются одним атомарным действием у владельца budget. Для token bucket это включает refill, ограничение вместимости и списание стоимости. Раздельные read и write позволяют одновременным запросам потратить один остаток несколько раз.

Короткий Redis script — один вариант для совместно размещённого состояния, но atomic execution не устраняет потери при failover. Несколько quotas на разных shards требуют отдельного протокола либо оговорённой погрешности. Для отказа store заранее выбирают ограниченный fallback или отказ, а не неуправляемый общий bypass. [Redis: Scripting](https://redis.io/docs/latest/develop/programmability/eval-intro/).

# Как разделить global quota, local admission control и tenant fairness без потери наблюдаемости?

**Global quota** ограничивает расход за agreed interval, а **local admission control** защищает текущую ёмкость экземпляра. Fairness распределяет ресурс между tenants, чтобы один активный потребитель не вытеснял остальных даже при соблюдении общего лимита.

Локальные leases budget уменьшают зависимость от центрального store, но задают границу возможного превышения и требуют учёта при потере узла. Наблюдают accepted, rejected, queued operations, причины отказа, delay и расход по policy. Rejection не должен маскировать перегрузку: долю полезных выполненных операций измеряют отдельно.

