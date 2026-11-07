# Почему MySQL и MariaDB нельзя считать полностью взаимозаменяемыми современными СУБД?

MySQL и MariaDB имеют общее происхождение и много совместимого SQL, но независимо развивают optimizer, types, authentication, replication и operational features. Одинаковый client protocol не доказывает совместимость файлов данных, GTID или результатов всех запросов.

Для переноса фиксируют конкретные versions и storage engines, проверяют SQL modes, collations, drivers и процедуры backup/restore. Переход нельзя считать безопасным только потому, что приложение установило соединение и выполнило простой SELECT. Upgrade и cross-product migration имеют разные supported paths. [MariaDB/MySQL compatibility](https://mariadb.com/docs/release-notes/community-server/about/compatibility-and-differences/mariadb-vs-mysql-compatibility).

# Как storage engine и InnoDB определяют транзакции, блокировки и восстановление таблицы?

**Storage engine** определяет значительную часть хранения и concurrency semantics таблицы. **InnoDB** предоставляет transactions, row-oriented locking, MVCC и crash recovery; другой engine может иметь другие гарантии и ограничения.

Поэтому транзакция приложения не становится атомарной для любых смешанных таблиц только из-за `BEGIN`. Проверяют фактический engine, поддержку constraints и особенности DDL. В современных MySQL и MariaDB InnoDB обычно является основным выбором для транзакционных данных, но детали реализации и defaults зависят от продукта и версии. Полезны проверки schema metadata вместо предположения по имени сервера.

# Как clustered primary key InnoDB влияет на secondary indexes и стоимость записи?

InnoDB организует row data в **clustered index**, обычно по primary key. Secondary index содержит свой ключ и clustered key для последующего нахождения строки, поэтому длинный primary key увеличивает не только одну структуру.

Случайные и часто меняемые keys могут увеличивать page splits и стоимость updates, а монотонный ключ способен концентрировать запись на определённых участках. Выбор учитывает concurrency и реальный профиль, а не правило «UUID всегда плох». При отсутствии объявленного primary key InnoDB выбирает подходящую альтернативу по своим правилам; лучше задавать identity явно.

# Как consistent reads и locking reads различаются при Repeatable Read и Read Committed в InnoDB?

В **MySQL 8.4 InnoDB Repeatable Read** обычные consistent reads используют snapshot, обычно установленный первым таким чтением transaction; в Read Committed каждый consistent read получает более свежий statement snapshot. Собственные изменения transaction видны по установленным правилам.

**Locking reads**, например `FOR UPDATE`, и изменяющие statements работают иначе, чем обычный snapshot SELECT, и могут ждать locks. Смешение этих путей требует понимания результата: Repeatable Read не означает, что любые операции используют одну старую версию. Для MariaDB проверяют её версию и configuration, не копируя все детали MySQL. [InnoDB isolation](https://dev.mysql.com/doc/refman/8.4/en/innodb-transaction-isolation-levels.html).

# Как record locks, gap locks и next-key locks защищают диапазоны InnoDB?

**Record lock** защищает index record, **gap lock** — промежуток для контроля вставок, а **next-key lock** объединяет record и прилегающий gap по модели InnoDB. Такие locks помогают защищать диапазон от определённых concurrent inserts.

Их применение зависит от isolation, query plan и уникальности поиска. Точное совпадение полного unique key может требовать иной набор locks, чем range scan. Отсутствие подходящего index увеличивает область просмотренных и потенциально заблокированных данных. В Read Committed gap locking ограничен, но существуют исключения, например проверки constraints. [InnoDB locks](https://dev.mysql.com/doc/refman/8.4/en/innodb-locking.html).

# Как исследовать deadlock InnoDB и безопасно повторить отменённую транзакцию?

Для deadlock исследуют участвующие transactions, удерживаемые и ожидаемые locks, порядок statements и indexes. InnoDB обычно выбирает victim и отменяет её transaction, чтобы разорвать цикл; приложение должно быть готово повторить логическую операцию целиком.

**Lock wait timeout** не следует автоматически считать тем же исходом: объём rollback зависит от error и settings. Перед retry освобождают или проверяют состояние transaction, задают ограничение попыток и сохраняют idempotency для внешних эффектов. Уменьшают длительность transactions и согласуют порядок доступа, а не просто увеличивают timeout.

# Чем redo log, undo log и binary log отличаются по роли в MySQL и MariaDB?

**Redo log** поддерживает crash recovery изменений storage engine, **undo** нужен для rollback и MVCC-представлений, а **binary log** фиксирует предусмотренные server-level изменения для replication и восстановления по журналу.

Redo и binlog не взаимозаменяемы: различаются формат, потребители и lifecycle. Durability зависит от синхронизации journal и storage, а согласование commit engine с binlog — от реализации продукта. Long transactions удерживают необходимые versions и затрудняют cleanup. Форматы и operational tools MySQL и MariaDB проверяют отдельно; наличие файла с похожим именем не гарантирует совместимость.

# Как binlog replication, GTID и failover зависят от конкретного продукта и конфигурации?

**Binlog replication** передаёт изменения от source к replicas, а **GTID** помогает идентифицировать transactions и продолжать replication без ручного сопоставления только file/position. MySQL и MariaDB имеют различающиеся GTID models и compatibility rules.

При failover выбирают узел по применённой истории, исключают прежний writer и переводят клиентов. Получение event replica не всегда означает его применение и видимость. Async и доступные semi-sync или cluster-механизмы дают разные гарантии. Отдельно проверяют lag, divergence и recovery старого primary; GTID не делает это автоматическим consensus-протоколом.

# Как implicit commit, metadata locks и online DDL влияют на изменение схемы?

Многие **DDL statements** вызывают implicit commit, поэтому нельзя рассчитывать на rollback migration как обычной DML transaction. Atomic DDL конкретного engine описывает устойчивость самой операции, а не обещает откат любых DDL вместе с бизнес-изменениями.

**Metadata locks** способны задержать даже внешне быструю операцию из-за открытой transaction. `INSTANT`, `INPLACE`, разрешённый lock level и переписывание таблицы зависят от изменения, продукта и версии. Перед production проверяют алгоритм и объём на похожих данных, ограничивают ожидание и планируют совместимость приложений. [Implicit commit MySQL](https://dev.mysql.com/doc/refman/8.4/en/implicit-commit.html).

# Как EXPLAIN, фактическое выполнение и statistics помогают оптимизировать запросы MySQL и MariaDB?

`EXPLAIN` показывает план и estimates, а поддерживаемый вариант фактического анализа действительно выполняет query и добавляет измерения. В MySQL и MariaDB syntax, поля и поддержка этих режимов различаются по версии.

Сравнивают estimated и actual rows, loop counts, index access, join order, сортировки и temporary work. Устаревшая statistics и skew параметров способны дать плохой выбор. Actual execution создаёт реальную нагрузку и возможные изменения, поэтому его запускают в подходящих условиях. Улучшение проверяют на типичных и крайних параметрах, а не по одному красивому plan. [EXPLAIN MySQL](https://dev.mysql.com/doc/refman/8.4/en/explain.html).

# Как SQL modes, collations, JSON и типы времени создают различия при переносе приложения?

**SQL modes** влияют на допустимость значений, группировку и обработку ошибок; **collations** — на сравнение, сортировку и uniqueness строк. Различие defaults может изменить результат без изменения query text.

**JSON** имеет различающиеся implementation и functions; нельзя предполагать одинаковое внутреннее хранение и index-поведение. Для времени проверяют `TIMESTAMP`, `DATETIME`, timezone session и диапазоны значений, а для чисел — precision и rounding. В migration tests включают Unicode, case/accent comparison, NULL, invalid dates и boundary values. Совместимость types не подтверждается только успешным импортом нескольких строк.

# Как согласовать logical или physical backup с binlog position и point-in-time recovery?

**Logical backup** экспортирует schema и данные, **physical backup** сохраняет storage в поддерживаемом согласованном формате. Инструмент должен соответствовать продукту, engine и версии; обычное копирование работающей data directory не является достаточным протоколом.

Фиксируют согласованную binlog position или GTID context и сохраняют необходимую непрерывную историю для **PITR**. Учитывают nontransactional tables, DDL во время dump, users, routines и encryption keys. Restore проверяют на отдельном экземпляре до нужной точки. Реплика не заменяет backup, поскольку ошибочный update или delete может воспроизвестись на ней.
