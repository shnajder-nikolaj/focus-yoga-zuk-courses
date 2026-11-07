# Как разделить metadata, object bytes и authorization в проектируемом файловом сервисе?

Metadata store хранит logical file ID, owner, tenant, version, status, checksum и ссылку на object. Bytes размещают в object storage с собственным immutable key или version ID. Публичный API работает с logical IDs, не предоставляя пользователю произвольный доступ к storage namespace.

Authorization проверяют при создании upload, чтении, изменении и выдаче временного доступа. Совместный commit metadata и object storage обычно отсутствует, поэтому задают промежуточные состояния и cleanup orphan objects. Наличие bytes не означает, что файл уже разрешён для скачивания.

# Как direct upload, multipart upload и resumable protocol переживают обрыв передачи?

Backend создаёт upload session и разрешение на конкретный object, а bytes могут идти напрямую в storage. Multipart делит объект на parts, которые можно повторять отдельно; resumable protocol хранит подтверждённую позицию или набор частей.

Upload ID, part metadata, ожидаемый размер и срок хранят устойчиво. Resume выполняет повторную authorization и сверяет состояние, а finalize собирает только согласованный набор частей. Незавершённые uploads очищают по policy, поскольку они могут занимать место без готового файла. Конкретный protocol и checksums зависят от storage API. [S3: Multipart upload](https://docs.aws.amazon.com/AmazonS3/latest/userguide/mpuoverview.html).

# Как finalize upload проверяет целостность объекта и исключает публикацию незавершённого файла?

Finalize проверяет принадлежность upload session, завершённость storage operation, размер и предусмотренный checksum, затем переводит metadata в нужное состояние. Проверки безопасности могут требовать промежуточного `processing` или `quarantined`, а не немедленного `ready`.

Прочитанная и проверенная object version должна совпадать с публикуемой. Повторный upload по ещё действующему URL не должен подменить уже проверенные bytes: используют version pinning, immutable keys или подходящий запрет перезаписи. ETag не считают универсальным MD5 всего файла, особенно для multipart. Повтор finalize возвращает тот же результат. [S3: Presigned URLs](https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-presigned-url.html).

# Как организовать версии, дедупликацию и удаление objects без потери ссылок и прав доступа?

Logical file имеет последовательность versions, каждая из которых ссылается на определённые bytes. Content hash может помочь deduplication, но одинаковые bytes у разных tenants не дают общего права доступа. Нельзя раскрывать существование чужого файла через небезопасный deduplication API.

Удаление сначала делает logical reference недоступной по policy, затем garbage collection удаляет bytes, больше никому не нужные. Reference counting или tracing references должны учитывать конкурентное создание версий, derivatives и задержанные jobs. Retention и backups имеют отдельные правила; physical cleanup не подменяет немедленную authorization.

# Как media pipeline связывает очередь заданий, идемпотентные workers и публикацию derivatives?

Задание содержит source file version, operation profile и version обработчика. Worker пишет результат под устойчивым output key и публикует metadata только после успешной проверки. Повтор того же задания не создаёт другое логическое производное.

Queue ack выполняют после устойчивой фиксации результата или уже завершённой операции. Несколько derivatives можно готовить независимо, а readiness manifest определяет доступный набор. Устаревший worker не должен заменить результат новой source version. Retry ограничен, постоянная ошибка наблюдаема, а orphan outputs можно безопасно удалить позже.

# Как resource isolation и limits защищают обработку изображений, видео и документов?

Untrusted media разбирают обновлёнными libraries в изолированном worker с минимальными правами, ограниченными mounts и без лишнего network access. Проверяют формат и структуру, а не только filename или Content-Type.

Лимитируют исходный и распакованный размер, dimensions, количество frames или pages, CPU, memory и длительность. Таймаут должен реально ограничивать subprocess или job, а не только ожидание клиента. Очереди и concurrency bounds защищают соседние workloads. Ошибка parser или повторная попытка не должна сделать quarantined source публично доступным.

# Как download path использует range requests, CDN и временные права доступа?

После проверки прав download может идти через application proxy, signed URL или CDN policy. Range requests позволяют передавать часть объекта и продолжать загрузку; resume связывают с прежней version, например через подходящие validators, чтобы не смешать bytes разных версий.

Временная ссылка является bearer capability в пределах её условий. Её scope и срок ограничивают, а CDN не должен выдать private object по общему cache key без проверки доступа. Немедленный отзыв требует специального механизма, если уже выданные credentials иначе продолжают действовать. [S3: Presigned URLs](https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-presigned-url.html).

# Как search index строится из system of record и обновляется после изменения документа?

Search index является derived view authoritative metadata и содержимого. Изменения передают через outbox или CDC с document ID и version; индексатор применяет их идемпотентно и не позволяет старому событию перезаписать новую версию.

Обновление store и появление в search могут иметь lag. Для read-your-writes задают отдельный contract, а delete и permission changes не оставляют исключительно надежде на фоновое обновление индекса. В Elasticsearch принятие операции и search visibility разделяет refresh; его параметры влияют на latency и нагрузку. [Elastic: Near real-time search](https://www.elastic.co/docs/manage-data/data-store/near-real-time-search).

# Как full-text search, ranking, filters и pagination проектируются под пользовательский сценарий?

Определяют типы queries: точный ID, full-text, phrase, filters и sorting. Analyzer, tokenization и normalizing выбирают по языкам и содержимому. Ranking должен соответствовать цели, например сочетать text relevance, freshness и разрешённые business signals.

Filters выполняют с учётом tenant и текущих прав, включая facets, counts и snippets. Для глубокой pagination нужен устойчивый cursor и при необходимости snapshot поиска. Сравнивают качество на размеченных queries и измеряют tail latency. Быстрый index не исправляет неверный analyzer или отсутствие важного документа в corpus.

# Как reindex, schema evolution и observability поддерживают файлово-поисковый сервис?

Новую schema или analyzer обычно вводят через отдельный index: выполняют backfill, догоняют изменения с согласованной границы и проверяют counts, versions, permissions и relevance. Затем переключают read path через предусмотренный механизм alias или routing.

Само копирование данных не переносит автоматически все конкурентные изменения. План учитывает catch-up, rollback и срок хранения прежнего index. Наблюдают ingestion lag, queue age, failed documents, query latency и долю неполных результатов. Semantics переключения и обработки частичных ошибок проверяют по конкретной API. [Elastic: Aliases](https://www.elastic.co/docs/manage-data/data-store/aliases).

