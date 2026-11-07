# Как embedded-архитектура SQLite влияет на соединения, latency и выбор нагрузки?

SQLite — library внутри процесса приложения, работающая с database file без отдельного DB server. Локальный вызов не требует network round trip, что удобно для embedded, desktop и части серверных нагрузок. Несколько connections и процессов могут обращаться к одной базе при корректных условиях хранения и locking.

Однако запись в один database file сериализуется. Большой поток одновременно пишущих сервисов, независимое масштабирование storage и сетевой доступ многих hosts часто требуют иной архитектуры. Оценивают размер транзакций, частоту записи и доступность файла, а не только число пользователей приложения. [SQLite: Appropriate Uses](https://www.sqlite.org/whentouse.html).

# Как type affinity и STRICT tables различаются при проверке типов SQLite?

В обычной таблице SQLite declared type задаёт **affinity**, то есть предпочтение преобразования значения. Если значение нельзя привести, оно во многих случаях может сохраниться с другим storage class. Например, объявление `INTEGER` само по себе не всегда запрещает произвольный текст.

**STRICT tables**, доступные с SQLite 3.37.0, ограничивают набор типов и требуют совместимого значения или допустимого преобразования без потерь. Тип `ANY` сохраняет возможность хранения разных значений. STRICT не заменяет `NOT NULL`, `CHECK` и бизнес-валидацию. Проверяют версию library, реально используемой приложением. [SQLite: STRICT Tables](https://www.sqlite.org/stricttables.html).

# Как DEFERRED, IMMEDIATE и autocommit определяют транзакции SQLite?

Без явного `BEGIN` SQLite автоматически начинает транзакцию для SQL operation и завершает implicit transaction после завершения последнего активного statement. Открытый cursor может влиять на момент завершения. Поведение high-level driver дополнительно зависит от его transaction settings.

`BEGIN DEFERRED` откладывает получение нужных locks до обращения к данным; чтение может позже потребовать upgrade к writer и получить конфликт. `BEGIN IMMEDIATE` сразу пытается начать write transaction, чтобы обнаружить конкурирующую запись до выполнения логики read-modify-write. Вложенные единицы работы строят через savepoints, а транзакции держат короткими. [SQLite: Transactions](https://www.sqlite.org/lang_transaction.html).

# Как WAL, readers, writer и checkpoint взаимодействуют в SQLite?

В **WAL mode** изменения сначала добавляются в журнал, а readers видят согласованный snapshot. Чтения и запись могут выполняться одновременно, но writers одной базы по-прежнему работают по очереди. WAL не превращает SQLite в multi-writer database.

**Checkpoint** переносит допустимые страницы из WAL в основной файл. Долгий reader может удерживать старый snapshot и мешать полному продвижению checkpoint, вызывая рост WAL. Наблюдают размер журнала, длительность transactions и политику checkpoint. Durability зависит также от settings синхронизации и корректности filesystem. [SQLite: WAL](https://www.sqlite.org/wal.html).

# Как SQLITE_BUSY, busy timeout и повтор транзакции обрабатывают конкуренцию в SQLite?

`SQLITE_BUSY` сообщает, что нужное действие сейчас конфликтует с другим connection. Busy timeout позволяет ограниченно ждать, но не увеличивает способность базы обслуживать параллельных writers. Некоторые конфликты требуют прекращения текущей transaction, а не ожидания.

Например, `SQLITE_BUSY_SNAPSHOT` в WAL возникает при невозможности безопасно повысить устаревший read snapshot до writer: нужно начать transaction заново и повторить решения. При ошибке `COMMIT` проверяют, остаётся ли transaction активной и допустим ли повтор commit. Общие retries ограничивают и согласуют с идемпотентностью внешних side effects. [SQLite: Isolation](https://www.sqlite.org/isolation.html).

# Почему foreign key enforcement в SQLite нужно проверять для каждого соединения?

Наличие `FOREIGN KEY` в schema не доказывает, что конкретный connection исполняет constraints. Поддержка зависит от build, а runtime setting задаётся на соединении. При его создании устанавливают `PRAGMA foreign_keys = ON` и проверяют фактическое значение.

Настройку выполняют вне активной transaction: попытка изменить её внутри может не дать ожидаемого эффекта. В connection pool нужен общий initialization hook. Для существующих данных используют `PRAGMA foreign_key_check`; включение enforcement не исправляет автоматически исторические нарушения. Migration и tests должны работать с теми же существенными settings. [SQLite: Foreign Keys](https://www.sqlite.org/foreignkeys.html).

# Чем INTEGER PRIMARY KEY, rowid и AUTOINCREMENT различаются в SQLite?

В обычной rowid table стандартное объявление `INTEGER PRIMARY KEY` связывает column с 64-bit signed `rowid`. При вставке без значения SQLite уже умеет выбрать свободный integer; `AUTOINCREMENT` для этого не обязателен. `WITHOUT ROWID` tables используют другую организацию.

`AUTOINCREMENT` меняет выбор автоматически создаваемого ID, предотвращая повторное использование ранее committed rowids, и поддерживает состояние в `sqlite_sequence`. Это добавляет overhead и не обещает последовательность без пропусков. Применяют его только при требовании не переиспользовать такие IDs, а не для обычного surrogate key. [SQLite: AUTOINCREMENT](https://www.sqlite.org/autoinc.html).

# Как EXPLAIN QUERY PLAN и индексы помогают исследовать запрос SQLite?

`EXPLAIN QUERY PLAN` показывает стратегию доступа: scans, searches по indexes, порядок вложенных loops и временные структуры сортировки. Сопоставляют выбранный index с фильтрами, join conditions и `ORDER BY`. Full scan не обязательно ошибка: он может быть дешевле для маленькой таблицы или большого результата.

Это описание плана, а не измерение фактического времени. Эффект проверяют на характерных данных с актуальной статистикой и ценой записи новых indexes. Текстовый формат вывода может меняться между версиями, поэтому на него не строят стабильный application protocol. [SQLite: EXPLAIN QUERY PLAN](https://www.sqlite.org/eqp.html).

# Как SQLite Online Backup API и VACUUM INTO обеспечивают согласованную резервную копию?

**Online Backup API** копирует согласованное состояние через механизмы SQLite и позволяет выполнять работу частями, учитывая конкурентный доступ. Проверяют результаты каждого этапа, завершение и ошибки. `VACUUM INTO` создаёт согласованную компактную копию в отдельном файле, выполняя полную перестройку представления данных.

Копирование только основного файла во время работы WAL может потерять часть состояния или дать некорректную копию. Выбирают поддерживаемую процедуру, проверяют устойчивое сохранение результата, integrity и восстановление. Прерванная операция не считается готовым backup. [SQLite Backup API](https://www.sqlite.org/backup.html), [VACUUM INTO](https://www.sqlite.org/lang_vacuum.html#vacuuminto).

# Как безопасно развёртывать SQLite в контейнерах, на shared storage и при нескольких replicas?

Database file размещают на persistent storage с проверенными locking и durability semantics, задают доступы и контролируют свободное место. В WAL mode связанные процессы должны работать на одном host; обычная сетевая filesystem между hosts не поддерживает требуемую модель shared memory.

Отдельные локальные files у replicas являются разными базами и не синхронизируются автоматически. Совместный mount также не создаёт распределённую БД. При необходимости нескольких application replicas выделяют управляемый путь доступа к данным или выбирают соответствующую DB architecture. Rollout, migrations и backups учитывают наличие всех процессов, использующих файл. [SQLite: WAL limitations](https://www.sqlite.org/wal.html).

