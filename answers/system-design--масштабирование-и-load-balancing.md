# Как выбрать между scale-up и scale-out по профилю нагрузки и ограничениям сервиса?

**Scale-up** увеличивает ресурсы одного экземпляра и подходит, когда рабочая нагрузка использует дополнительные CPU, RAM или I/O без изменения архитектуры. Его пределы задаются доступным hardware, устройством процесса и риском отказа большого узла.

**Scale-out** добавляет экземпляры и позволяет распределять работу, но требует корректного размещения состояния, routing и координации. Для single-threaded bottleneck дополнительные cores одного процесса могут оказаться бесполезными; для горячей строки БД лишние application replicas также не помогают. Выбор проверяют измерением полезного throughput при прежних latency и error rate.

# Какие виды состояния мешают горизонтальному масштабированию application tier?

Мешают локальные sessions, временные uploads, единственная in-memory очередь, process-local locks и неразделяемое состояние фоновой задачи. После смены экземпляра клиент должен продолжить сценарий без потери нужных данных и нарушения инвариантов.

Состояние делают восстанавливаемым, размещают в подходящем store либо явно назначают владельца partition с процедурой передачи. Sticky sessions могут сохранить привязку, но усложняют балансировку и отказ. Даже stateless HTTP handler использует stateful dependencies: горизонтальное масштабирование приложения не отменяет ограничений общей БД и координации.

# Как определить единицу масштабирования и разделить независимо растущие компоненты?

Выделяют компоненты с различными ресурсными профилями: request handlers, CPU-heavy processing, queue consumers и search workers. Каждый получает собственные concurrency limits и сигнал ёмкости, чтобы увеличение одной нагрузки не увеличивало ненужные компоненты.

Единицей масштабирования может быть process, container, shard или tenant group. Разделение оправдано, когда оно уменьшает конкуренцию или позволяет независимо управлять capacity. Слишком мелкое разделение добавляет network hops и operational cost. До создания нового service часто достаточно отдельного worker pool или deployment с понятной границей состояния.

# Как L4 и L7 load balancing различаются по управлению соединениями и запросами?

**L4 balancing** распределяет transport connections или flows, обычно без понимания отдельных HTTP operations. **L7 balancing** понимает прикладной протокол и может выбирать upstream по маршруту, headers или отдельному запросу, когда режим proxy это допускает.

L7 добавляет возможности TLS termination, policies и request-level telemetry, но требует ресурсов и корректной обработки протокола. L4 может оставить существующее долгое соединение на одном backend независимо от числа запросов внутри. Сравнивают не только latency proxy, но и поведение при отказе, multiplexing и реальный уровень распределения.

# Как round robin, least connections, least requests и consistent hashing распределяют нагрузку?

`Round robin` поочерёдно выбирает endpoints и хорошо работает при похожей стоимости работы; веса учитывают разную capacity. `Least connections` предпочитает меньше открытых соединений, а `least requests` — меньше активных запросов в рамках конкретной реализации.

`Consistent hashing` сохраняет affinity по выбранному ключу и уменьшает перераспределение при смене состава, но не устраняет hot keys. Количество соединений плохо отражает стоимость multiplexed или очень разных запросов. Проверяют алгоритм, weights, scope наблюдений и защиту от медленного backend. Доступность методов зависит от продукта и версии. [NGINX: Load balancing methods](https://docs.nginx.com/nginx/admin-guide/load-balancer/http-load-balancer/).

# Как keep-alive, HTTP/2 и WebSockets влияют на равномерность балансировки?

Keep-alive переиспользует соединения, а HTTP/2 переносит несколько streams внутри одного connection. Поэтому распределение connections не равно распределению requests: несколько крупных клиентов могут перегрузить отдельные backends. Уже установленные WebSocket sessions также не перемещаются автоматически при добавлении replicas.

Используют подходящий уровень balancing, достаточное число upstream connections и наблюдение за активной работой, а не только sockets. Для длительных sessions предусматривают controlled reconnect, drain и восстановление состояния. Принудительное массовое переподключение само способно создать burst авторизации и cold starts. [Google SRE: Datacenter Load Balancing](https://sre.google/sre-book/load-balancing-datacenter/).

# Как health checks, connection draining и slow start обеспечивают безопасное изменение backend pool?

Readiness или health check определяет, можно ли направлять новую работу. Он должен проверять существенную готовность, не вызывая массового исключения всех replicas из-за одной общей временной проблемы. При удалении endpoint сначала прекращают новые назначения и дают текущим operations завершиться в пределах deadline.

**Slow start** постепенно увеличивает долю трафика нового или восстановленного backend, которому нужны cache или runtime warm-up. Он не создаёт дополнительную ёмкость, если холодны сразу все экземпляры. Порядок readiness, drain и shutdown проверяют для используемого proxy и orchestrator. [Envoy: Slow start](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/load_balancing/slow_start).

# Как autoscaling signal, stabilization window и startup time влияют на устойчивость scale-out?

Сигнал должен отражать ограничение компонента: CPU для вычислений, queue age или backlog для workers, активные requests для ограниченной конкурентности. Запаздывающий CPU metric может не успеть предупредить рост latency, а среднее значение скрывает отдельную горячую partition.

Учитывают период измерения, время решения, scheduling, startup и warm-up. Stabilization windows и разные правила scale-up/scale-down уменьшают колебания, но увеличивают задержку реакции. Нужны нижняя граница capacity, максимальный размер и проверка отказа metrics pipeline. Конкретные алгоритмы зависят от autoscaler. [Kubernetes: HPA](https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/).

# Как при масштабировании application tier учитывать database capacity, pools и downstream limits?

Оценивают суммарные DB connections всех процессов, включая rollout overlap, workers и максимальный autoscaling. Добавление replicas с неизменным pool size может исчерпать лимит БД раньше, чем вырастет полезный throughput.

Связывают application concurrency с измеренной downstream capacity, временем удержания ресурсов и quotas внешних API. До превышения лимита применяют bounded queues, admission control и управляемые отказы. Отдельно учитывают cache misses после scale-out и fan-out. Масштабирование одной ступени pipeline не увеличивает пропускную способность всех последующих ступеней.

# Как проверить эффективность масштабирования и обнаружить serial bottleneck или hot partition?

На фиксированном профиле данных и операций измеряют throughput, latency, ошибки и стоимость при разных размерах системы. Линейный рост возможен только пока нет общего ограничивающего ресурса. Следят за распределением нагрузки по replicas и shards, а не только за общим средним.

Если добавление узлов не помогает, проверяют serial sections, shared locks, coordinator, DB и hot partitions. Анализируют overhead coordination и rebalance. После изменения проверяют работу при отказе части capacity: хороший steady-state benchmark не доказывает устойчивость процесса масштабирования.

