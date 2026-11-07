# Как property graph Neo4j использует nodes, relationships, labels и properties?

**Property graph** состоит из nodes и направленных typed relationships; у обоих могут быть properties, а nodes дополнительно классифицируются labels. Одна node может иметь несколько labels, соответствующих разным ролям.

Модель подходит для запросов, где связи и пути являются основной частью данных, например зависимости, рекомендации и fraud patterns. Направление relationship хранится, но query может явно искать обе стороны. Graph database не делает любую агрегацию быстрее relational SQL: результат зависит от структуры, стартовой выборки и объёма обхода.

# Когда связь моделировать relationship, отдельным node или свойством?

Relationship хорошо представляет связь двух entities с типом и ограниченным набором attributes. Отдельный **node** нужен, если у самой связи есть identity, сложный lifecycle или дополнительные связи, например участие нескольких сторон в договоре.

Простое значение, по которому не требуется отдельная topology, может оставаться property. Не превращают каждый scalar в node и не прячут важную связь в строке ID без анализа queries. Оценивают cardinality и supernodes: один узел с огромным числом connections способен сделать даже короткий traversal дорогим.

# Как MATCH и OPTIONAL MATCH различаются по отсутствующим данным и фильтрации?

`MATCH` оставляет строки, для которых pattern найден. **OPTIONAL MATCH** сохраняет исходную строку при отсутствии соответствия, заполняя новые variables значениями `null`, что похоже на outer join по своей цели.

`WHERE` относится к определённой части query, поэтому его placement меняет результат: фильтр optional pattern и последующий фильтр уже полученных rows не всегда эквивалентны. Различают отсутствующее property, отсутствующую связь и пустой результат целиком. Query проверяют на nodes без связей и нескольких совпадениях, а не только на полностью заполненном графе. [Cypher MATCH](https://neo4j.com/docs/cypher-manual/current/clauses/match/).

# Как WITH, aggregations и cardinality влияют на промежуточные результаты Cypher?

**WITH** передаёт выбранные variables на следующий этап, может ограничивать scope, выполнять aggregation, ordering и filtering. Каждое совпадение pattern способно увеличить число rows, поэтому важно понимать **cardinality** после каждого этапа.

Aggregation группирует по неагрегированным expressions; `collect` может сохранить большой набор в памяти. Слишком поздний `DISTINCT` удаляет duplicates после уже выполненной дорогой работы, а слишком ранний способен изменить смысл. Промежуточный query plan помогает найти место размножения rows и перенести подходящий filter ближе к источнику.

# Почему несвязанные patterns и неограниченные traversals могут резко увеличить стоимость запроса?

Несвязанные patterns могут дать **Cartesian product**, перемножая независимые matches. Variable-length traversal без разумных границ способен породить множество paths на циклическом или плотно связанном графе.

Ограничивают стартовые nodes, типы relationships, направление и нужную глубину, выбирают подходящую задаче path semantics. Итоговый `LIMIT` не обязательно устраняет дорогую предшествующую работу. Особенности повторения relationships и path selectors зависят от Cypher version. Стоимость проверяют на реалистичной степени связности, включая supernodes и крайние cases.

# Как indexes и constraints помогают найти стартовые nodes и закрепить инварианты?

Indexes помогают быстро найти **стартовые nodes** по labels и properties; дальнейший traversal использует структуру связей. Constraint закрепляет invariant, например уникальную бизнес-identity, и в предусмотренных случаях опирается на поддерживающий index.

Доступные range, text, full-text, vector indexes и виды constraints зависят от версии и edition. Нельзя считать, что index на одном property ускорит любой путь и любое expression. Проверяют query plan, selectivity и стоимость обслуживания при writes. Уникальность нужного ID задают явно, а не выводят из текущего отсутствия duplicates.

# Чем MERGE отличается от CREATE и почему MERGE не заменяет uniqueness constraint?

`CREATE` создаёт заданные элементы, а **MERGE** пытается сопоставить предусмотренный pattern и создаёт его при отсутствии. Он сопоставляет pattern по своим правилам, а не выполняет произвольный business upsert «по похожим полям».

Для identity используют стабильный key и **uniqueness constraint**, а изменяемые attributes обновляют отдельно. Одного MERGE без constraint недостаточно для гарантии отсутствия duplicates при concurrent transactions. Большой pattern полезно разбить на понятные шаги с bound entities, учитывая семантику каждой связи. Обрабатывают constraint conflicts и безопасный retry. [Cypher MERGE](https://neo4j.com/docs/cypher-manual/current/clauses/merge/).

# Как transactions, locks и retries обеспечивают корректность конкурентных изменений графа?

Neo4j transactions атомарно фиксируют graph changes и используют locks для защиты конкурентных writes. Конкретные reads и expressions не следует автоматически считать serializable read-modify-write всего произвольного business process.

Deadlocks и transient failures могут требовать повторить transaction. Driver-managed retry способен снова вызвать callback, поэтому внешние эффекты внутри него должны иметь свою idempotency или отдельный lifecycle. Ограничивают transaction size и время удержания locks, задают consistent order доступа и constraints. Гарантию проверяют конкурентным сценарием на выбранной версии. [Concurrent access Neo4j](https://neo4j.com/docs/operations-manual/current/database-internals/concurrent-data-access/).

# Как EXPLAIN и PROFILE помогают отличить дешёвый traversal от дорогого поиска?

**EXPLAIN** строит план без обычного выполнения query, **PROFILE** выполняет его и показывает фактическую работу operators. Сравнивают estimates и actual rows, database hits, index seek против scan и промежуточные expansions.

Дешёвый поиск одной стартовой node может сопровождаться огромным обходом downstream, поэтому одного присутствия index в plan мало. PROFILE для изменяющего query действительно меняет данные и создаёт нагрузку. Измерения делают на подходящих данных и проверяют, что оптимизация не изменила множество paths или duplicates, необходимые бизнесу. [Query plans](https://neo4j.com/docs/cypher-manual/current/planning-and-tuning/execution-plans/).

# Как parameters и динамические идентификаторы связаны с безопасным построением Cypher?

Обычные **parameters** передают values отдельно от query text, уменьшая риск injection и помогая планированию. Нельзя превращать пользовательский фрагмент текста в Cypher через конкатенацию и считать quoting достаточной общей защитой.

Labels, relationship types и другие динамические части используют через поддерживаемый соответствующей версией syntax либо ограниченный набор разрешённых вариантов. Новые возможности dynamic identifiers не означают, что любой старый scalar placeholder можно поставить в любое место. Вызов procedures и APOC тоже проверяют по permissions, источнику arguments и доступным side effects.

# Как routing, replicas и bookmarks влияют на чтение после записи в Neo4j cluster?

Driver с поддержкой **routing** направляет операции к подходящим участникам cluster по конфигурации и роли query. Само подключение к произвольному replica не означает чтение только что выполненной записи.

**Bookmark** передаёт causal progress: следующая работа может дождаться доступности состояния как минимум до нужной transaction. Sessions и bookmark manager используют по API выбранного driver; direct connection и routing URI имеют разное назначение. Bookmarks не делают все независимые reads глобально linearizable и не заменяют transaction boundaries. Поведение retry и failover включают в проверку приложения.

# Как различаются transactional graph queries, Graph Data Science и задачи backup и восстановления?

Transactional **Cypher queries** обслуживают текущие reads и writes графа с соответствующими database guarantees. **Graph Data Science** выполняет graph algorithms на подготовленном представлении и может требовать отдельной memory, projection и управляемой записи результатов назад.

Проекция для алгоритма не является автоматическим backup текущей database. План recovery включает данные, constraints/indexes, configuration, identities и поддерживаемые log/backup procedures конкретной версии и edition. Проверяют restore и causal behavior после возврата сервиса. Выбор shortest-path или community algorithm не решает задачу durability и HA основного хранилища.
