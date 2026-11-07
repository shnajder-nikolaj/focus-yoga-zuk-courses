# Как document model MongoDB и collections/documents Firestore влияют на границы агрегатов?

**MongoDB** хранит BSON documents в collections; документ может содержать вложенные объекты и arrays. **Firestore** native document API использует documents с paths внутри collections и subcollections. Ни одна модель не требует раскладывать каждый объект в SQL-подобную строку.

Границу документа выбирают по совместному чтению, изменению и допустимому размеру. Subcollection Firestore не является автоматически частью атомарного родительского document. Возможности разных режимов Firestore и MongoDB-compatible API различаются, поэтому сравнение ниже относится к соответствующим обычным document APIs, а не обещает их взаимозаменяемость.

# Когда embedding лучше references и какие ограничения роста документа нужно учитывать?

**Embedding** удобно, когда данные читаются и меняются вместе, принадлежат одному агрегату и имеют ограниченный рост. **References** подходят для независимого lifecycle, многократного переиспользования и больших или неограниченных наборов.

Вложенный список всех событий пользователя способен превратить document в hot spot и упереться в size limits. Ссылки требуют дополнительных запросов или поддерживаемого серверного соединения данных и отдельной проверки согласованности. Денормализованные копии получают источник истины и механизм обновления. Конкретные document limits, index costs и операции проверяют для выбранного продукта.

# Как schema validation и правила эволюции документов дополняют гибкую структуру данных?

Гибкая структура не означает отсутствие контракта. В MongoDB **schema validation** может проверять типы и обязательные поля по настроенным правилам, а приложение должно уметь читать допустимые прежние версии документов.

В Firestore validation зависит от пути доступа: client Security Rules и backend code решают разные части задачи. Для эволюции добавляют совместимые поля, задают defaults и при необходимости version marker, затем выполняют идемпотентный backfill. Простое изменение TypeScript interface не преобразует сохранённые документы и не защищает записи от другого клиента.

# Какие гарантии даёт атомарное изменение одного MongoDB document и как защититься от lost update?

MongoDB атомарно изменяет один document, включая несколько его полей. Условие update проверяется при конкурентном выполнении, поэтому можно добавить ожидаемую **version** или текущее значение в filter и проверить число изменённых документов.

Две безусловные операции `$set`, рассчитанные из старого чтения, способны перезаписать результаты друг друга. Для подходящих счётчиков используют атомарный `$inc`, а для общего read-modify-write — условный update или transaction. Single-document atomicity не распространяется автоматически на несколько документов одной коллекции. [MongoDB atomicity](https://www.mongodb.com/docs/manual/core/write-operations-atomicity/).

# Как MongoDB transactions и Firestore transactions различаются по API, конфликтам и повтору callback?

**MongoDB transaction** связывает несколько операций через session в поддерживаемом deployment; driver helpers могут повторять transaction или commit по своим правилам. Нужно понимать, какие ошибки и неизвестные исходы обрабатываются автоматически.

**Firestore transaction** читает документы и атомарно применяет зависимые writes, а callback может запускаться повторно при contention. Mobile/web SDK и server SDK используют разные механизмы concurrency, связанные с доступными режимами. Поэтому внутри повторяемого callback нельзя безусловно отправлять платёж или уведомление. Для независимых writes отдельно рассматривают atomic batch, который не заменяет conditional read-modify-write. [Firestore contention](https://firebase.google.com/docs/firestore/transaction-data-contention).

# Как write concern, read concern и read preference задают поведение MongoDB при репликации?

**Write concern** определяет необходимые подтверждения записи, **read concern** — свойства видимости и изоляции прочитанных данных, **read preference** — выбор подходящих участников replica set для чтения. Это связанные, но разные настройки.

Чтение с secondary может отставать, а `majority` не означает автоматически «самая свежая запись по реальному времени». Для causal read-your-writes нужны предусмотренные sessions и совместимые concerns. Выбор latency и failover проверяют на операциях приложения, включая timeout commit с неизвестным исходом. Опции по умолчанию и допустимые сочетания зависят от deployment и версии. [MongoDB read concern](https://www.mongodb.com/docs/manual/reference/read-concern/).

# Как indexes MongoDB и single-field/composite indexes Firestore связаны с допустимыми запросами?

В MongoDB indexes ускоряют поддерживаемые filters и sort; composite key order, multikey arrays и selectivity влияют на реальный план. Отсутствие подходящего index может приводить к дорогому scan, а лишние indexes увеличивают запись и storage.

В Firestore native queries опираются на index-модель: single-field и **composite indexes** обслуживают разные сочетания filters и ordering. Нужный composite index должен быть создан и готов. Index exemptions уменьшают fanout, но меняют доступные запросы. Не предполагают, что произвольный MongoDB query переводится в эквивалентный Firestore query без изменения модели. [Firestore indexes](https://firebase.google.com/docs/firestore/query-data/index-overview).

# Как pagination, сортировка и ограничения query API влияют на проектирование document database?

Для стабильной pagination задают явный sort и уникальный tie-breaker, например document ID. Cursor или keyset-подход уменьшает работу по сравнению с пропуском большого префикса, но требует сохранения точных значений позиции.

Изменения данных между страницами способны дать пропуски и повторы, если нет подходящего snapshot или явно принятой семантики. В MongoDB проверяют index и explain, в Firestore — поддерживаемые combinations и cursors выбранного API. Проектирование начинают с важных запросов; дополнительные client-side чтения для соединения данных имеют latency и стоимость.

# Как MongoDB shard key и распределение нагрузки Firestore влияют на hot documents и hotspots?

**MongoDB shard key** задаёт распределение документов и маршрутизацию запросов. Неудачные cardinality, monotonic values и skew способны создать hot shard или scatter-gather. Разделение по shards не устраняет конкуренцию за один document.

Firestore управляет распределением, но частые updates одного document и последовательные patterns ID или indexed values всё равно могут создавать contention и hotspots. Уменьшают ненужный index fanout, распределяют подходящие aggregates и проверяют нагрузку постепенно. Нельзя выбирать произвольный random key без учёта запросов и локальности данных. [Firestore best practices](https://firebase.google.com/docs/firestore/best-practices).

# Как change streams и Firestore listeners отличаются от долговременной бизнес-очереди?

**MongoDB change stream** сообщает об изменениях с механизмом resume, но возможность продолжения зависит от доступной истории и корректного checkpoint. Consumer не получает автоматически общую транзакцию между обработкой события и внешним эффектом.

**Firestore listener** поддерживает наблюдаемое состояние результата, включая initial snapshot и доступные cache/pending metadata клиентского SDK. Это не неизменяемый бизнес-журнал с отдельным ack для каждой операции. Reconnect, повтор и пересоздание subscription учитывают явно. Для надёжного процесса сохраняют собственную event identity и progress либо используют соответствующую messaging-архитектуру.

# Как Firestore Security Rules, IAM и MongoDB roles разделяют доступ клиентов и backend?

**Firestore Security Rules** проверяют доступ клиентских SDK к документам и допустимость запросов; они не являются фильтром, который молча убирает запрещённые строки. Server clients с подходящими credentials используют IAM и обходят client Rules, поэтому backend тоже валидирует полномочия.

В MongoDB roles и authentication ограничивают действия database users, а application authorization определяет доступ конкретного пользователя продукта. Не передают административные credentials в browser. Разделяют tenants, проверяют все пути записи и тестируют запреты, а не только успешные reads. [Firestore Rules](https://firebase.google.com/docs/firestore/security/rules-conditions).

# Как проверять миграции документов, backup и восстановление без предположения о полной совместимости эмулятора?

Проверяют mixed document versions, повтор backfill, конкурентную запись и восстановление после частичного сбоя. Отдельно убеждаются, что миграция не увеличила document size, index fanout и query latency сверх допустимого.

Backup или export оценивают по реальному restore, полноте metadata и поддержке выбранного режима. Правила удаления вложенных данных и subcollections не выводят из внешнего сходства JSON. Эмулятор полезен для быстрых проверок, но production indexes, scaling, IAM и recovery подтверждают в соответствующей среде. Сохраняют источник повторного построения денормализованных данных и измеряют RPO/RTO.
