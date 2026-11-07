# Как сравнивать pgvector, Qdrant, Milvus и Weaviate по модели данных и интеграции с приложением?

**pgvector** добавляет vector types и поиск в PostgreSQL, позволяя хранить vectors рядом с transactional data и использовать SQL. **Qdrant** организует поиск по points с vectors и payload в collections. **Milvus** предоставляет специализированную vector database architecture и управляемые schema/indexes. **Weaviate** связывает objects, vectors и keyword/hybrid retrieval.

Сравнивают нужные filters, consistency, operational model, распределение данных и интеграцию с source of truth. Название продукта не гарантирует одинаковых возможностей каждой версии и deployment. [pgvector](https://github.com/pgvector/pgvector), [Qdrant](https://qdrant.tech/documentation/manage-data/collections/), [Milvus](https://milvus.io/docs/architecture_overview.md), [Weaviate](https://docs.weaviate.io/weaviate/search/hybrid).

# Почему embedding model, размерность и версия пространства должны совпадать при поиске?

Расстояние имеет смысл между совместимыми representations одного согласованного пространства. Одинаковая размерность двух models недостаточна: координаты могут описывать разные признаки. Query и document encoders могут различаться, если обучены работать совместно; это не разрешает смешивать произвольные embeddings.

Хранят model ID, версию preprocessing, dimensions и необходимые параметры. При смене model создают новую generation vectors и проверяют retrieval до переключения. Простая запись новых embeddings в старое поле может смешать несовместимые данные и незаметно ухудшить результаты без ошибки типов.

# Как cosine similarity, inner product и L2 distance связаны с нормализацией vectors?

Для ненулевых vectors **cosine similarity** сравнивает направление, деля inner product на произведение норм. **Inner product** зависит также от длины vectors, а **L2 distance** измеряет евклидово расстояние. Направление сортировки score зависит от выбранной API.

Для unit-normalized vectors `L2² = 2 − 2 × inner_product`, поэтому соответствующие rankings совпадают при прочих равных. Без нормализации это неверно. Метрику выбирают согласно model и задаче, а не по привычному названию. Zero vector требует специальной обработки, поскольку cosine для него не определён.

# Как HNSW и IVFFlat меняют recall, latency, память и стоимость построения индекса?

**HNSW** строит многоуровневый граф и позволяет менять поиск компромиссом между шириной обхода и recall. Его graph structure расходует память и время построения. **IVFFlat** группирует vectors в lists и при query исследует часть списков; качество зависит от обучения и числа probes.

Оба метода приближённые: рост скорости оплачивается риском пропуска соседей. Сравнивают build, updates, memory и filtered queries на своём dataset. Маленький или очень селективный набор может быть выгоднее искать точно. [pgvector: Indexing](https://github.com/pgvector/pgvector#indexing).

# Как metadata filters и tenant authorization взаимодействуют с approximate nearest neighbor search?

Metadata filter задаёт допустимое подмножество, а ANN ищет близкие vectors. Если engine сначала ограничил candidates, а затем применил filter, результат может содержать меньше `k` строк. Нужны подходящие payload indexes, параметры обхода или поддерживаемое расширение поиска.

Tenant и ACL conditions строит сервер из проверенной identity. Они ограничивают выдачу, counts и дальнейшую передачу context, включая reranker или LLM. Высокий recall не компенсирует утечку чужих документов. Поведение pre/post filtering и доступные controls проверяют для engine и версии. [Qdrant: Filtering](https://qdrant.tech/documentation/search/filtering/).

# Как hybrid search, reciprocal rank fusion и reranking улучшают retrieval?

**Hybrid search** объединяет lexical retrieval, например BM25, с semantic vector retrieval: точные термины и смысловая близость дополняют друг друга. Их raw scores часто имеют разные шкалы, поэтому прямое сложение требует обоснованной calibration.

**Reciprocal rank fusion** объединяет позиции документов в ranked lists, уменьшая зависимость от шкал scores. Reranker затем оценивает ограниченный candidate set более дорогой моделью. Он не найдёт документ, отсутствующий среди candidates. Candidate limits и порядок stages проверяют одновременно по relevance и end-to-end latency. [Qdrant: RRF](https://qdrant.tech/documentation/search/hybrid-queries/#reciprocal-rank-fusion-rrf).

# Как chunking, document IDs и embedding pipeline обеспечивают обновление поискового корпуса?

Chunking задаёт retrieval unit: слишком большой фрагмент смешивает темы, слишком маленький теряет контекст и увеличивает число vectors. Учитывают structure документа, overlap, язык и границы token budget, сохраняя связь с оригинальным source.

Каждый chunk имеет stable identity в рамках document version, model version и metadata о permissions. Изменения проходят идемпотентный pipeline с retry, reconciliation и удалением старых chunks. Новую generation публикуют после проверки completeness, чтобы не смешать часть старого и нового документа. Embedding computation и запись в index не должны терять обновление source.

# Как consistency, deletes и replica lag влияют на свежесть и права доступа в vector search?

Acknowledgement записи, её durability и видимость в search — разные свойства. Они зависят от replication, indexing и выбранного consistency level. Например, Milvus предоставляет несколько режимов consistency, поэтому нельзя считать default эквивалентом немедленного read-your-writes во всех сценариях.

Delete и изменение ACL должны распространяться во все derived representations. При строгом отзыве read path проверяет актуальное право до передачи данных пользователю или model, не полагаясь только на lagging metadata. Consistency видимости не равна качеству ANN и не заменяет backup. [Milvus: Consistency](https://milvus.io/docs/consistency.md).

# Как измерять Recall@k, MRR, nDCG и качество retrieval на репрезентативном наборе запросов?

Для **ANN Recall@k** результат сравнивают с exact nearest-neighbor baseline на том же corpus, metric и filters. Это проверяет approximation index, а не semantic полезность соседей. Для retrieval Recall@k сравнивают top-k с размеченными релевантными документами.

**MRR** учитывает позицию первого релевантного результата; **nDCG** — порядок и градуированную релевантность с нормализацией относительно идеальной выдачи. Dataset включает languages, редкие intents, большие и малые tenants и permission filters. Дополнительно измеряют latency, coverage и downstream task quality, не подбирая параметры только по удачным примерам.

# Как планировать ёмкость, reindex, backups и восстановление vector database?

Базовый объём float32 vectors равен `N × dimensions × 4 bytes`: миллион vectors размерности 1536 требует около 6,14 GB только для числовых значений. Отдельно добавляют metadata, graph или lists, replicas, logs и запас на rebuild. Quantization уменьшает часть объёма с собственным quality tradeoff.

Reindex или смена model могут временно требовать две generations и удвоенный ingest. Backup сохраняет данные, metadata, конфигурацию и версии, необходимые для восстановления; source documents могут потребоваться для повторного embedding. Restore проверяют реальными queries, filters, ACL и quality baseline.

