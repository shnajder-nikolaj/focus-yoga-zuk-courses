# Как SQL Server instances и databases отличаются от Oracle instance, database, CDB и PDB?

**SQL Server instance** — работающий экземпляр Database Engine, управляющий databases и общими instance-level ресурсами. Каждая user database имеет собственные объекты и файлы по своей модели; schema является namespace внутри database.

В **Oracle** instance — память и background processes, а database — соответствующий набор persistent files. В multitenant-модели **CDB** содержит root и **PDB**, предоставляющие отдельные логические контейнеры. При RAC несколько instances могут обслуживать одну database. Поэтому слова instance, database и schema нельзя механически переводить один-к-одному между продуктами. [Oracle architecture](https://docs.oracle.com/en/database/oracle/oracle-database/19/cncpt/introduction-to-oracle-database.html).

# Как transaction log SQL Server и redo, undo и archive logs Oracle участвуют в восстановлении?

**Transaction log SQL Server** фиксирует изменения, необходимые для transaction management и recovery. Его lifecycle, reuse и доступность log backups зависят от recovery model и других условий; наличие log не означает автоматически готовый PITR.

В **Oracle redo** описывает изменения для воспроизведения, **undo** хранит данные для rollback и consistent read, а **archived redo logs** сохраняют завершённые журналы для recovery и других задач. Эти роли взаимосвязаны, но undo не является аналогом отдельной полной резервной копии. Durability commit зависит также от configuration и storage. [SQL Server log](https://learn.microsoft.com/en-us/sql/relational-databases/logs/the-transaction-log-sql-server?view=sql-server-ver17), [Oracle storage](https://docs.oracle.com/en/database/oracle/oracle-database/19/cncpt/physical-storage-structures.html).

# Как locking Read Committed и READ_COMMITTED_SNAPSHOT различаются в SQL Server?

При locking **Read Committed** обычное чтение использует соответствующие locks для предотвращения dirty reads и может ждать concurrent writer. Настройки optimized locking и hints способны менять детали, поэтому проверяют реальную configuration.

При `READ_COMMITTED_SNAPSHOT` (**RCSI**) обычное Read Committed чтение использует row versions для statement-level snapshot, уменьшая reader/writer blocking на данных. Это не отменяет все locks, конфликты writers и schema locking. Значение настройки нельзя считать одинаковым во всех SQL Server и Azure deployment. RCSI не делает несколько statements одним transaction snapshot. [Locking и versioning](https://learn.microsoft.com/en-us/sql/relational-databases/sql-server-transaction-locking-and-row-versioning-guide?view=sql-server-ver17).

# Как Oracle Read Committed и consistent read используют undo для чтения согласованной версии?

В обычном **Oracle Read Committed** запрос видит согласованное committed состояние на предусмотренный момент начала statement. Если текущие blocks содержат более новые изменения, система использует **undo** для реконструкции подходящей read-consistent версии.

Обычный consistent read не требует блокировать строки так же, как изменяющий их writer; `SELECT FOR UPDATE` имеет другую семантику. Для долгого чтения нужны доступные прошлые версии: недостаток нужного undo может привести к `snapshot too old`. Успешный один SELECT не гарантирует неизменность следующего SELECT в той же Read Committed transaction. [Oracle read consistency](https://docs.oracle.com/en/database/oracle/oracle-database/19/cncpt/data-concurrency-and-consistency.html).

# Чем statement-level snapshot отличается от transaction-level snapshot в SQL Server и Oracle?

**Statement-level snapshot** фиксирует представление для одного statement: следующий запрос может увидеть новые commits. **Transaction-level snapshot** сохраняет согласованную основу для нескольких запросов transaction с учётом собственных изменений.

В SQL Server RCSI и `SNAPSHOT` — разные режимы и требуют соответствующих настроек. В Oracle обычный Read Committed отличается от transaction-level read consistency в serializable или read-only transaction. Совпадение слова snapshot не доказывает одинаковые update conflict и isolation rules. Бизнес-инварианты проверяют конкурентными сценариями, не перенося семантику одного продукта на другой. [SQL Server isolation](https://learn.microsoft.com/en-us/sql/relational-databases/sql-server-transaction-locking-and-row-versioning-guide?view=sql-server-ver17), [Oracle isolation](https://docs.oracle.com/en/database/oracle/oracle-database/19/cncpt/data-concurrency-and-consistency.html).

# Как clustered index SQL Server отличается от heap и index-organized table Oracle?

У rowstore **clustered B-tree index SQL Server** leaf level содержит table data, организованные по clustered key; **heap** не использует такую clustered структуру. Nonclustered indexes обращаются к строке через соответствующий locator.

Обычная Oracle table также часто heap-organized, а **index-organized table**, или IOT, хранит данные в структуре primary-key index с предусмотренными дополнительными механизмами. Primary key не означает одинаковую физическую организацию в обеих СУБД. Учитывают размер ключа, вторичные indexes, диапазонные чтения и стоимость updates; columnstore — отдельная модель. [SQL Server indexes](https://learn.microsoft.com/en-us/sql/relational-databases/indexes/clustered-and-nonclustered-indexes-described?view=sql-server-ver17), [Oracle IOT](https://docs.oracle.com/en/database/oracle/oracle-database/19/cncpt/indexes-and-index-organized-tables.html).

# Как execution plans, statistics и bind parameters влияют на диагностику запросов в обеих СУБД?

Сравнивают estimates и фактическую cardinality, пути доступа, JOIN order, sorts, I/O и ожидания. Statistics и распределение параметров способны изменить выбор плана: один cached plan может подходить типичному значению и плохо работать для перекошенного tenant.

SQL Server parameter sniffing и Oracle bind-related оптимизации имеют свои механизмы и зависят от версии. Для SQL Server используют доступные actual plans и Query Store, для Oracle — фактический cursor plan и подходящие execution statistics. Предварительный explain не всегда описывает реально выполненный plan. Сбор actual evidence может выполнять запрос и создавать нагрузку. [SQL Server plans](https://learn.microsoft.com/en-us/sql/relational-databases/performance/execution-plans?view=sql-server-ver17).

# Как SQL Server tempdb и Oracle temporary и undo storage участвуют в работе запросов?

**SQL Server tempdb** обслуживает temporary objects и internal work, например spills sorts и hash operations. Он также содержит traditional version store для соответствующих user databases без ADR. При включённом **ADR** размещение versions отличается: user database использует свой persistent version store; новые версии поддерживают и отдельные возможности ADR самого tempdb.

В Oracle **temporary storage** и **undo** имеют разные роли для временной работы и восстановления прошлых версий. Их sizing не сводится к копированию tempdb settings. Проверяют workload, spills, retention versions и configuration конкретной версии. [tempdb](https://learn.microsoft.com/en-us/sql/relational-databases/databases/tempdb-database?view=sql-server-ver17).

# Как blocking, deadlocks и долгие транзакции исследуют без переноса предположений другой СУБД?

**Blocking** — ожидание несовместимого ресурса или lock, **deadlock** — цикл зависимостей, который не разрешится простым ожиданием. Ищут владельцев, blocked operations, transaction boundaries и consistent order доступа, а не завершают случайную долгую session.

В SQL Server выбранная deadlock victim transaction обычно откатывается целиком; в Oracle при обычном deadlock может быть автоматически отменён один statement, а дальнейший transaction lifecycle требует решения приложения. Поэтому retry policy строят по фактическому состоянию. Долгая transaction также удерживает ресурсы log/undo/version retention даже при малом текущем CPU. [Oracle deadlocks](https://docs.oracle.com/en/database/oracle/oracle-database/19/cncpt/data-concurrency-and-consistency.html).

# Как Always On availability groups и Oracle Data Guard отличаются от backup и горизонтального шардирования?

**Always On availability groups** поддерживают replicas набора SQL Server databases между instances с режимами commit и failover по configuration. **Oracle Data Guard** поддерживает standby databases через transport/apply и управляемое переключение ролей.

Они решают HA/DR, но не являются автоматически sharding с независимой записью по partitions. Ошибочное изменение может распространиться на replicas, поэтому backup остаётся нужен. Возможности readable replicas, автоматического failover и защиты данных зависят от mode, версии и edition. Отдельно проектируют client routing и исключение прежнего writer. [Availability groups](https://learn.microsoft.com/en-us/sql/database-engine/availability-groups/windows/overview-of-always-on-availability-groups-sql-server?view=sql-server-ver17), [Data Guard](https://docs.oracle.com/en/database/oracle/oracle-database/19/sbydb/introduction-to-oracle-data-guard-concepts.html).

# Как full, differential, incremental и log backups связаны с point-in-time recovery в этих СУБД?

В **SQL Server** полное восстановление может использовать full backup, подходящий differential и непрерывную цепочку log backups при поддерживающей recovery model. Differential опирается на определённую базу; не каждый внешне похожий full backup меняет её одинаково.

В **Oracle RMAN** full и incremental level 0 не полностью взаимозаменяемы по роли в incremental strategy; последующие increments и необходимые redo позволяют восстановление по выбранному плану. Для PITR нужны доступная цепочка, metadata и ключи. Обе процедуры проверяют реальным restore с измерением RPO/RTO, а не только успешным статусом backup job. [SQL Server backup](https://learn.microsoft.com/en-us/sql/relational-databases/backup-restore/backup-overview-sql-server?view=sql-server-ver17), [RMAN](https://docs.oracle.com/en/database/oracle/oracle-database/19/bradv/rman-backup-concepts.html).

# Как планировать перенос приложения между SQL Server и Oracle с учётом SQL dialect, типов и operational features?

Инвентаризируют queries, procedures, drivers, transaction boundaries и operational dependencies. Проверяют T-SQL против PL/SQL, identity/sequences, pagination, collations, decimal precision и временные types. Например, Oracle `DATE` включает время, а SQL Server `date` — только дату; пустая строка и `NULL` тоже имеют разные правила.

Отдельно тестируют concurrency, error handling и DDL transaction semantics: Oracle DDL часто вызывает implicit commit, поэтому прежняя схема rollback может не перенестись. Планируют data conversion, догоняющую синхронизацию, cutover и возврат. Доступность требуемых HA, backup и monitoring features проверяют для выбранных версии, edition и deployment.
