# Как scheduler использует requests, node capacity и allocatable при размещении Pod?

Scheduler размещает Pod исходя из заявленных **requests** и ограничений, сравнивая их с доступным для workloads **node allocatable** и уже учтёнными запросами. Allocatable меньше общей capacity, поскольку часть ресурсов оставляют системе и служебным компонентам.

Мгновенно низкое фактическое CPU-потребление node не означает, что на нём достаточно scheduler capacity. В расчёт Pod входят правила для containers, init containers и Pod overhead. Помимо ресурсов учитываются affinity, taints, topology и storage. Поэтому Pending требует изучения events, а не только графика текущей нагрузки.

# Чем CPU request отличается от CPU limit и как возникает throttling?

**CPU request** участвует в scheduling и определяет относительную долю при конкуренции в соответствующей runtime-модели. Это не постоянное выделение физического ядра. **CPU limit** задаёт верхний бюджет CPU-времени, если соответствующее ограничение настроено.

Когда приложение расходует бюджет раньше конца периода, возникает **throttling**: выполнение ждёт, даже если отдельные CPU могут выглядеть не полностью занятыми. Без limit контейнер может использовать свободные CPU сверх request. Для performance оценивают workload, cgroup settings и latency под нагрузкой; простое повышение числа потоков может лишь быстрее исчерпать quota. [Resource management](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/).

# Как memory request, memory limit, OOMKilled и eviction описывают разные события?

**Memory request** — вход scheduling и важный параметр поведения при resource pressure. **Memory limit** ограничивает учитываемую runtime память; при нарушении ограничения может сработать OOM kill процесса, после чего container state часто показывает `OOMKilled`.

**Eviction** — другое действие: kubelet завершает Pod ради освобождения ресурсов node, например при memory или disk pressure. Оно возможно и без превышения собственного container limit. Проверяют reason Pod, container termination details и node events; restart count сам по себе не объясняет причину. [Node-pressure eviction](https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/).

# Как QoS classes и overcommit влияют на поведение при нехватке ресурсов узла?

Для обычных container-level настроек **Guaranteed** требует согласованных CPU и memory requests и limits у всех containers, **BestEffort** означает отсутствие соответствующих запросов и ограничений, остальные подходящие случаи относятся к **Burstable**. При использовании новых resource-возможностей уточняют правила своей версии Kubernetes.

Overcommit позволяет суммарному потенциальному потреблению превышать физический ресурс. При memory pressure kubelet учитывает превышение requests, priority и другие критерии eviction; QoS не является абсолютной защитой от отказа. Даже Guaranteed workload может пострадать при серьёзной нехватке ресурсов. Подбирают requests по измерениям и оставляют системный резерв.

# Как nodeSelector, node affinity и pod affinity ограничивают выбор узла?

`nodeSelector` требует совпадения node labels. **Node affinity** задаёт более выразительные правила с обязательными и предпочтительными условиями. **Pod affinity/anti-affinity** учитывает размещение других Pods относительно topology labels, например зоны или hostname.

Обязательные условия могут оставить Pod Pending, если подходящих nodes нет, а предпочтительные влияют на scoring. Правила `…DuringSchedulingIgnoredDuringExecution` обычно не выселяют уже запущенный Pod только из-за последующего изменения labels. Перед применением оценивают ёмкость каждой зоны и реальную независимость failure domains. [Assigning Pods to Nodes](https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/).

# Как taints, tolerations и topology spread constraints управляют изоляцией и распределением Pods?

**Taint** на node отталкивает неподходящие Pods, **toleration** разрешает соответствующее исключение, но не направляет Pod именно на этот node. `NoSchedule` блокирует новое размещение, а `NoExecute` может также привести к удалению уже работающих Pods по правилам tolerations.

**Topology spread constraints** ограничивают перекос числа Pods между domains по `topologyKey` и `maxSkew`. `DoNotSchedule` задаёт жёсткое условие, `ScheduleAnyway` — предпочтение. Для выделенных nodes часто нужны и toleration, и affinity. Один label зоны без корректного ограничения не гарантирует распределения replicas.

# Как PriorityClass и preemption помогают разместить важный Pod и какие задачи не решают?

**PriorityClass** задаёт относительную важность Pod. При отсутствии подходящей ёмкости scheduler может выполнить **preemption**: убрать менее приоритетные Pods, если это позволяет разместить важный Pod в рамках остальных ограничений.

Preemption не создаёт CPU, storage или подходящую topology и не исправляет несовместимую affinity. Возможны задержки graceful termination и повторный выбор node, поэтому это не мгновенная гарантия доступности. Злоупотребление высоким priority вытесняет чужие workloads. Priority регулируют на уровне политики кластера и capacity planning, а не выдают всем приложениям одинаково высокий класс.

# Как HPA вычисляет число реплик по resource metrics и почему requests влияют на результат?

В упрощённом виде **HPA** оценивает `ceil(currentReplicas × currentMetric / targetMetric)`, затем учитывает ограничения и особенности наблюдений. Для CPU utilization значение обычно считается относительно CPU request, поэтому изменение request меняет процент при том же фактическом потреблении.

Нужны доступные metrics и корректные requests соответствующих containers. Пропущенные metrics, startup и unready Pods обрабатываются специальными правилами, а не просто как нулевая нагрузка. Проверяют HPA conditions и источник metrics. Масштабирование не поможет, если bottleneck находится в общей БД или внешнем rate limit. [Алгоритм HPA](https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/).

# Как custom metrics, stabilization windows и scaling policies ограничивают колебания HPA?

**Custom/external metrics** позволяют масштабировать по очереди, RPS или другой величине через поддерживаемые metrics APIs. Выбирают метрику, которая показывает потребность в replicas, а не только поздний симптом перегрузки.

**Stabilization windows** сглаживают решения, а **scaling policies** ограничивают скорость изменения replicas. Если задано несколько metrics, HPA обычно выбирает наибольшее рассчитанное число replicas; недоступность некоторых metrics влияет на возможность scale down. Настраивают min/max и budget зависимости. Быстрое добавление Pods бесполезно без времени startup и свободных ресурсов node. [HPA behavior](https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/).

# Как VPA и масштабирование узлов взаимодействуют с HPA и scheduling?

**VPA** рекомендует или меняет requests отдельных workloads в зависимости от режима и возможностей установки; изменение ресурсов может требовать пересоздания Pod либо поддерживаемого in-place механизма. **HPA** меняет число replicas, а node autoscaler — доступную ёмкость nodes для подходящих сценариев.

Изменение CPU request через VPA меняет denominator CPU-utilization HPA, поэтому контроллеры способны влиять друг на друга. Часто разделяют метрики и область ответственности. Node scaling учитывает requests и placement, а не просто высокий график CPU. Проверяют min/max, quota, topology и время появления новых nodes.

# Как startup, readiness и liveness проверки отражают разные этапы работы Pod?

**Startup probe** отделяет длительный запуск от рабочего режима и до своего успеха подавляет соответствующие readiness и liveness проверки. **Readiness** сообщает, готов ли Pod/container принимать нужный трафик; неуспех убирает его из обычного ready routing без обязательного restart.

**Liveness** обнаруживает состояние, из которого нужно выйти перезапуском. Проверка общей зависимости вроде БД в liveness может вызвать каскад рестартов при её отказе. Thresholds выбирают по реальному startup и восстановлению; probes не заменяют внешнее наблюдение пользовательских сценариев. [Kubernetes probes](https://kubernetes.io/docs/concepts/workloads/pods/probes/).

# Как PodDisruptionBudget, termination grace period и запас мощности влияют на обслуживание кластера?

**PodDisruptionBudget** ограничивает допустимые добровольные disruptions через учитывающие его eviction-механизмы, например при обычном drain. Он не предотвращает аварийный отказ node и не заменяет собственные правила rolling update controller.

`terminationGracePeriodSeconds` даёт время завершить работу, но не создаёт replacement capacity. Для обслуживания нужны доступные nodes, свободные ресурсы, правильная topology и возможность разместить новые replicas. Слишком строгий PDB при отсутствии резерва может заблокировать drain. Проверяют, что бизнес выдерживает фактическую потерю экземпляров, а не только формально соблюдённый budget. [Disruptions](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/).
