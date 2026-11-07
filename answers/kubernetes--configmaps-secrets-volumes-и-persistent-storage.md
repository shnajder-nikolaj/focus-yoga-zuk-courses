# Как ConfigMap и Secret разделяют конфигурацию и чувствительные данные Kubernetes-приложения?

**ConfigMap** хранит обычную конфигурацию, например адрес backend и настройки logging. **Secret** предназначен для чувствительных значений и некоторых специальных форматов credentials. Оба объекта обычно относятся к namespace и могут передаваться через environment или volumes.

Secret не становится защищённым только из-за своего типа: нужны RBAC, encryption at rest и контроль доступа workload. ConfigMap не используют как случайный secret store. Для согласованного выпуска полезны versioned или immutable объекты и явная привязка Pod template к версии конфигурации.

# Как environment variables и volume projections по-разному получают обновления ConfigMap и Secret?

Значения **environment variables** определяются при создании контейнера и не обновляются в уже работающем процессе автоматически. Для изменения такой конфигурации обычно требуется пересоздание Pod через управляемый rollout.

Проекция ConfigMap или Secret в volume может обновляться kubelet с задержкой; приложение должно перечитать файл или поддерживать reload. При `subPath` mount автоматического обновления содержимого таким способом нет. Изменение файла не гарантирует, что процесс перестал использовать старое значение из памяти или открытого дескриптора. [Обновления ConfigMap](https://kubernetes.io/docs/concepts/configuration/configmap/).

# Почему base64 в Secret не заменяет encryption at rest и контроль доступа?

**Base64** кодирует байты для представления в API, но любой читатель значения может их декодировать. Если encryption at rest не настроено, Secret может храниться в etcd без соответствующего шифрования данных; backups тоже требуют защиты.

RBAC ограничивает `get`, `list` и `watch`, а также возможность запускать workload, который получит Secret. Пользователь с правом создать Pod с подходящим доступом может косвенно прочитать секрет, не имея прямого `get secrets`. Шифрование storage не защищает от разрешённого API-чтения и утечки через приложение. [Kubernetes Secrets](https://kubernetes.io/docs/concepts/configuration/secret/).

# Как emptyDir и projected volumes связаны с жизненным циклом Pod?

**emptyDir** создаётся для Pod и переживает перезапуск отдельного контейнера в этом Pod, но удаляется вместе с ним. Он подходит для временных данных и обмена файлами между контейнерами, а не для сохранения БД после пересоздания Pod.

`emptyDir` с memory medium расходует память и должен учитываться при расчёте memory budget. **Projected volume** объединяет поддерживаемые источники, например ConfigMap, Secret, Downward API и ServiceAccount token, в одном пути. Его содержимым управляет kubelet; это не произвольное долговременное writable storage. [Kubernetes volumes](https://kubernetes.io/docs/concepts/storage/volumes/).

# Как PersistentVolume, PersistentVolumeClaim, StorageClass и CSI driver взаимодействуют при provisioning?

**PersistentVolume**, или PV, описывает предоставленное хранилище; **PersistentVolumeClaim**, или PVC, запрашивает capacity, access mode и класс. Pod ссылается на PVC, а не выбирает физический диск напрямую.

**StorageClass** описывает класс и параметры provisioning. При dynamic provisioning соответствующий **CSI driver** и связанные controllers создают storage и PV, а binding связывает PV с PVC. Возможно и заранее подготовленное статическое PV. PVC относится к namespace, PV — к кластеру. Жизненный цикл данных зависит от reclaim policy и backend, а не только от Pod. [Persistent Volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/).

# Как access modes ReadWriteOnce, ReadOnlyMany, ReadWriteMany и ReadWriteOncePod ограничивают доступ?

`ReadWriteOnce` (**RWO**) допускает read-write mount с одного node, что не обязательно означает один Pod: несколько Pods на том же node могут использовать volume. `ReadOnlyMany` допускает read-only использование несколькими nodes, `ReadWriteMany` — read-write несколькими nodes, если backend это поддерживает.

`ReadWriteOncePod` (**RWOP**) ограничивает read-write использование одним Pod для поддерживаемых CSI volumes и версий компонентов. Access modes участвуют в подборе и использовании storage, но не заменяют filesystem permissions и корректную координацию приложения. Особенно опасно считать RWO универсальным distributed lock. [Access modes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/#access-modes).

# Как WaitForFirstConsumer связывает provisioning диска с scheduling и topology?

При `volumeBindingMode: WaitForFirstConsumer` binding и provisioning откладываются до появления Pod-потребителя, чтобы учитывать его placement constraints и topology storage. Иначе zonal disk может быть создан в зоне, где Pod нельзя запустить.

Scheduler согласует requests, affinity, доступные nodes и ограничения volume. Ручное задание `nodeName` способно обойти нужный этап scheduler и оставить PVC Pending; предпочтительнее подходящие constraints. Поддержка режима зависит от provisioner и типа storage. Он не создаёт автоматически дополнительные replicas данных между зонами. [Volume binding mode](https://kubernetes.io/docs/concepts/storage/storage-classes/#volume-binding-mode).

# Как reclaim policy и удаление PVC влияют на сохранность данных?

**Reclaim policy** PV определяет, что делать после освобождения claim. `Delete` для поддерживаемого provisioner может удалить и PV, и соответствующий storage asset; `Retain` оставляет данные для ручного дальнейшего управления.

Удаление Pod обычно не равно удалению его обычного PVC, но дополнительные controllers и политики могут менять общий lifecycle. Удаление PVC тоже может ожидать прекращения использования из-за protection mechanisms. Для важных данных явно проверяют policy, поведение StatefulSet или Operator и восстановление. `Retain` не заменяет backup: оставшийся диск может быть потерян вместе с backend.

# Как volume expansion и изменение StorageClass ограничены возможностями CSI и файловой системы?

Увеличение PVC требует `allowVolumeExpansion` у StorageClass и поддержки backend, CSI driver и, при filesystem volume, расширения файловой системы. Возможность online expansion зависит от этих компонентов; уменьшение существующего PVC обычным запросом не поддерживается как симметричная операция.

Изменение StorageClass не означает автоматическую миграцию уже созданного диска на другой тип или в другую зону. Ряд полей существующих объектов ограничен в изменении. Для нового класса может потребоваться новый PVC и перенос данных. Проверяют status conditions, фактический размер диска и filesystem после операции.

# Как volume snapshots отличаются от согласованного backup приложения?

**VolumeSnapshot** фиксирует состояние поддерживаемого storage через CSI snapshot-механизмы. Он может быть crash-consistent, но не обязан сохранять согласованную бизнес-транзакцию, особенно при нескольких volumes или внешних зависимостях.

Для application-consistent backup нужны подходящие checkpoints, журналы, quiesce или штатный backup СУБД. Учитывают snapshot deletion policy, расположение и независимость от исходного backend. Проверяют восстановление в новый PVC и запуск приложения; готовый snapshot не доказывает полноту disaster recovery. Ресурсы snapshot и controllers должны быть установлены и поддерживаться в кластере. [Volume snapshots](https://kubernetes.io/docs/concepts/storage/volume-snapshots/).

# Как permissions, fsGroup и securityContext влияют на доступ к смонтированным данным?

`runAsUser` и `runAsGroup` определяют identity процесса, filesystem permissions — доступ к файлам. `fsGroup` может задавать дополнительную group и участвовать в подготовке прав volume в зависимости от типа storage и CSI driver.

При некоторых CSI-механизмах изменение mount group делегировано driver, а не рекурсивному `chown` kubelet. Для больших volumes смена ownership может замедлить старт; поддерживаемая политика изменения помогает ограничить работу. `fsGroup` не исправляет любой root-squash или backend ACL. Права проверяют от имени фактического non-root процесса, избегая универсального `chmod 777`.

# Как диагностировать Pending PVC, ошибки attach или mount и нехватку места на volume?

Для **Pending PVC** изучают events, StorageClass, provisioner, quota, capacity, access modes и topology. При `WaitForFirstConsumer` отсутствие binding до scheduling потребителя может быть ожидаемым.

Для attach или mount errors проверяют node, CSI controller и node plugins, доступ к backend, credentials, filesystem и прежнее подключение диска. Нехватка места бывает в самом volume, inode pool или host ephemeral storage — это разные проблемы. Принудительный detach без проверки старого writer способен повредить данные. После исправления проверяют filesystem и работу приложения, а не только статус `Bound`.
