# Как Helm chart, values, templates и release описывают установку приложения?

**Helm chart** — пакет templates, default values, metadata и зависимостей. **Values** задают параметры, из которых Helm рендерит Kubernetes manifests. **Release** — именованная установка chart в окружении с историей его применений.

Chart version и `appVersion` отражают разные вещи: версия пакета не обязана совпадать с версией приложения или image tag. Для review проверяют итоговый YAML, а не только values: шаблон способен создать дополнительные RBAC, hooks и storage resources. Release metadata и доступ к нему также требуют защиты. [Helm charts](https://helm.sh/docs/topics/charts/).

# Как Helm upgrade, rollback и hooks связаны с фактической готовностью и изменениями данных?

`upgrade` применяет новую версию описания release, а `rollback` возвращает сохранённую предыдущую revision. Факт успешной отправки manifests в API ещё не означает готовность всех workloads; ожидание, timeout и автоматическую реакцию на сбой настраивают для установленной major-версии Helm.

**Hooks** запускают действия в определённых точках lifecycle, но не превращают обновление в транзакцию. Миграция БД, созданная запись или внешний вызов не отменяются обычным rollback manifests. Проверяют повторяемость hooks, их cleanup и совместимость данных; при смене Helm major сверяют доступные flags и их семантику.

# Как фиксировать chart dependencies и проверять итоговые manifests до установки?

Зависимости описывают в `Chart.yaml`, фиксируют разрешённые версии в `Chart.lock` и восстанавливают подходящей dependency-командой. Отдельно контролируют источник chart, integrity и доступ к registry; lockfile не является доказательством безопасности пакета.

До установки выполняют lint, render с реальными values, schema validation и проверки политики для целевого Kubernetes API. `helm template` полезен для просмотра, но не полностью повторяет серверную validation и runtime. Dry-run output может раскрыть Secret, поэтому его не публикуют без проверки. В тестовом окружении проверяют upgrade существующего release, а не только clean install.

# Как Kustomize bases, overlays и patches изменяют manifests без шаблонизации всего YAML?

**Base** содержит общие Kubernetes objects, **overlay** добавляет окружение и преобразования: patches, labels, images и другие поддерживаемые настройки. Kustomize работает со структурой YAML, сохраняя обычные manifests как исходную форму.

Patch выбирают по устойчивой identity ресурса и проверяют после изменения base. Generated ConfigMaps и Secrets могут получать content hash в имени, помогая связать конфигурацию с Pod template. Итог просматривают через `kubectl kustomize` или соответствующий build, фиксируя версию инструмента. Ошибка target patch может дать синтаксически допустимую, но неверную конфигурацию. [Kustomize](https://kubernetes.io/docs/tasks/manage-kubernetes-objects/kustomization/).

# Чем Helm и Kustomize отличаются по модели переиспользования и управлению релизом?

**Helm** использует параметризованные templates, пакет charts и release lifecycle с revisions. **Kustomize** преобразует готовые manifests через композицию и patches, без собственной эквивалентной истории release по умолчанию.

Helm удобен для распространяемых пакетов с интерфейсом values, Kustomize — для небольших отличий собственных environments. Их можно сочетать, но сложная многоступенчатая генерация ухудшает прозрачность. В GitOps ownership и rollback может задавать контроллер поверх этих инструментов. Независимо от выбора проверяют итоговые manifests и не допускают конкурирующего управления одними и теми же полями.

# Как CustomResourceDefinition и Operator расширяют Kubernetes API и reconciliation?

**CustomResourceDefinition**, или CRD, добавляет тип ресурса в Kubernetes API со schema и правилами validation. **Operator** наблюдает custom resources и связанные объекты, затем reconciliation приводит реальную систему к описанному состоянию.

Например, ресурс базы может описывать число replicas и backup policy, а controller управляет StatefulSets, services и внешними операциями. CRD сама по себе не реализует эту бизнес-логику. Operator получает существенные полномочия, поэтому его upgrade, permissions и восстановление рассматривают как часть эксплуатации сервиса, а не просто установку ещё одного YAML.

# Как status conditions, finalizers и повторные вызовы влияют на корректность Operator?

**Status conditions** сообщают, что controller наблюдает и в каком состоянии находится операция. `observedGeneration`, когда предусмотрен API, помогает понять, относится ли status к актуальной spec. Пользователь не должен путать accepted desired state с завершённым действием.

**Finalizer** задерживает окончательное удаление объекта, пока controller не выполнит нужную очистку. Reconciliation может повторяться и прерываться, поэтому внешние действия делают идемпотентными и учитывают неизвестный исход. Зависший finalizer сначала диагностируют; его принудительное удаление может оставить внешний ресурс или потерять нужную cleanup-гарантию.

# Как Role, ClusterRole, RoleBinding и ClusterRoleBinding задают права субъектов?

**Role** задаёт разрешения в namespace. **ClusterRole** может описывать cluster-scoped ресурсы и правила для переиспользования между namespaces. **RoleBinding** выдаёт права внутри своего namespace и может ссылаться на Role или ClusterRole; **ClusterRoleBinding** выдаёт соответствующие права на уровне кластера.

Subjects — users, groups и ServiceAccounts; правила включают API groups, resources и verbs. RBAC складывает разрешения и не предоставляет обычного deny-rule для вычитания уже выданного доступа. Namespace binding к ClusterRole не превращает cluster-scoped permissions в локальные. [Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/).

# Как ServiceAccount, token projection, authentication и admission связаны с доступом workload к API?

**ServiceAccount** задаёт identity workload в namespace. Поддерживаемые projected tokens ограничены временем и audience и могут обновляться kubelet. Приложение должно использовать актуальный token; если API-доступ не нужен, автоматическое подключение credentials отключают.

**Authentication** проверяет, кто обращается, **authorization**, включая RBAC, — разрешено ли действие. **Admission** дополнительно проверяет или изменяет уже авторизованный запрос по правилам кластера. Поэтому валидный token не означает право создавать любой Pod, а RBAC-разрешение не гарантирует прохождение security policy. Содержимое identity и token нельзя считать обычной публичной конфигурацией.

# Как проверять минимальные RBAC-права и избегать неочевидного privilege escalation?

Права проверяют на конкретные verbs, resources, namespace и identity, например через `kubectl auth can-i` при наличии необходимых полномочий на проверку. Затем тестируют реальные действия приложения и запрещённые сценарии.

Риск создают не только `*`, но и создание Pods с доступом к чужим secrets, изменение workloads, `pods/exec`, `bind`, `escalate` и `impersonate`. Для оператора важны также права на finalizers и status. Review учитывает существующие bindings и агрегирование ролей: отдельная узкая Role не ограничивает более широкие разрешения, полученные иначе. [RBAC escalation](https://kubernetes.io/docs/reference/access-authn-authz/rbac/).

# Как построить последовательную диагностику Pod через status, events, logs и describe?

Начинают с **Pod status**, условий и container states, затем читают events и `describe`. Для Pending ищут scheduling или volume-причину; для `ImagePullBackOff` — image name, credentials и registry; для `CrashLoopBackOff` — завершение процесса, probes и его предыдущие logs.

Сопоставляют время ошибки с rollout и изменением конфигурации. Проверяют exit reason, restart count, limits и mounted files. Logs читают для нужного container, включая init containers; при перезапуске полезны previous logs. Интерактивная диагностика и ephemeral containers требуют разрешений и не должны раскрывать secrets.

# Как отличать ошибки приложения, scheduling, сети, storage и control plane при инциденте?

Проверяют путь по слоям: существует ли объект, размещён ли Pod, запущен ли процесс, открыт ли listener, появился ли ready endpoint, проходит ли запрос через Service и внешний gateway. Такой порядок отделяет ошибку приложения от маршрутизации к отсутствующему backend.

Сравнивают несколько workloads и nodes: массовая проблема только одной зоны указывает на другую область, чем ошибка одного release. API errors, недоступность controllers и cluster-wide events помогают выявить control-plane сбой. Сохраняют факты до массовых рестартов: они могут временно скрыть симптом и уничтожить полезные свидетельства.
