# Как virtual memory, page tables и page faults связывают память процесса с физической RAM?

**Virtual memory** даёт процессу адресное пространство, а **page tables** связывают виртуальные pages с физической памятью и задают разрешения. Часть адресов может быть зарезервирована без немедленного выделения RAM.

**Page fault** возникает, когда доступ требует участия kernel: например, выделения zero page, copy-on-write или загрузки file-backed page. Это не обязательно ошибка приложения. Major fault обычно связан с необходимым I/O, minor обходится без такого чтения storage. Частота faults интерпретируется вместе с workload и latency, а не только как признак нехватки памяти.

# Чем RSS, PSS, virtual size и page cache отличаются при анализе памяти?

**Virtual size** отражает mappings и резервирование адресов, **RSS** — resident pages процесса, **PSS** распределяет вклад shared pages между их пользователями. Сумма RSS многих процессов может многократно учитывать общие страницы.

**Page cache** хранит файловые данные в памяти; часть его может быть reclaimable, но dirty pages требуют writeback и не всегда освобождаются мгновенно. Большой cache не равен memory leak. Сопоставляют process mappings, доступную память host и cgroup accounting: `memory.current` не является просто RSS одного process. [smaps](https://man7.org/linux/man-pages/man5/proc_pid_smaps.5.html).

# Как reclaim, swap и memory pressure влияют на latency до срабатывания OOM?

При нехватке памяти kernel выполняет **reclaim**: освобождает подходящие caches, пишет dirty pages и при наличии swap перемещает допустимые pages. Direct reclaim может заставить сам allocating thread ждать освобождения памяти.

Swap и повторные faults способны резко увеличить latency задолго до OOM. Поэтому отсутствие kill не означает здоровую систему. Наблюдают reclaim activity, swap I/O, major faults и PSI вместе с application tail latency. Простое уменьшение cache или отключение swap без анализа может перенести проблему в более ранний отказ, а не устранить demand.

# Как kernel OOM killer, cgroup OOM и userspace oomd различаются по области действия?

**Kernel OOM killer** срабатывает при невозможности удовлетворить выделение в соответствующей ситуации и выбирает жертву по правилам kernel. **Cgroup OOM** ограничивает проблему областью resource group: host может иметь свободную RAM, пока container достиг своего предела.

**Userspace oomd**, например systemd-oomd, использует pressure и другие критерии для упреждающего завершения подходящих cgroups по configuration. Это не тот же механизм, что kernel OOM. Причину устанавливают по kernel logs, cgroup events и журналу oomd; факт `SIGKILL` сам по себе её не доказывает. [systemd-oomd](https://man7.org/linux/man-pages/man8/systemd-oomd.service.8.html).

# Как cgroup v2 memory.max, memory.high и memory.events помогают ограничивать и наблюдать память?

В **cgroup v2** `memory.max` задаёт жёсткую границу, при достижении которой kernel пытается reclaim, а при невозможности может вызвать scoped OOM. `memory.high` задаёт pressure boundary с reclaim и throttling, а не обычный немедленный kill по одному превышению.

`memory.events` содержит счётчики relevant events; учитывают иерархию, а для локальных событий — предусмотренный интерфейс. Дополняют их `memory.current`, breakdown и pressure. Порог выбирают с запасом на runtime и page cache, не только по application heap. Эти интерфейсы относятся к v2 и не копируются буквально на v1. [Cgroup v2](https://docs.kernel.org/admin-guide/cgroup-v2.html).

# Как scheduler распределяет CPU между runnable tasks и что означает fair scheduling?

Scheduler выбирает среди **runnable tasks**, учитывая scheduling class, weights, доступные CPU и ограничения. Fair scheduling стремится распределять процессорное время справедливо по установленной модели, а не поровну между приложениями независимо от числа tasks и группировки.

Детали зависят от kernel: после исторического CFS fair class развивается в направлении **EEVDF**, использующего eligibility и virtual deadlines. Это не гарантирует жёсткий deadline обычному process. I/O wait, real-time classes, cgroups и topology требуют отдельного учёта. Нельзя диагностировать современный host только по названию старого scheduler. [EEVDF](https://docs.kernel.org/scheduler/sched-eevdf.html).

# Как nice, CPU weight, quota и affinity задают разные ограничения процессорного времени?

**Nice** меняет относительный вес обычной task в поддерживаемом scheduling class. **Cgroup CPU weight** распределяет долю между конкурирующими группами. Эти веса не являются абсолютным лимитом и позволяют использовать свободный ресурс сверх обычной доли.

**Quota** ограничивает CPU budget за период, а **affinity/cpuset** сужают набор разрешённых CPU. Quota не закрепляет собственное физическое ядро, а affinity не гарантирует отсутствие конкурентов на нём. При настройке проверяют иерархию cgroups и реальные права: ограничения родительской группы могут оказаться сильнее локального значения.

# Как CPU throttling, run queue и steal time объясняют задержки при невысокой средней загрузке?

**CPU throttling** возникает, когда task исчерпала разрешённый quota budget и ждёт следующего периода. **Run queue** отражает runnable работу, ожидающую CPU. **Steal time** в VM показывает время, когда guest не получил процессор из-за действий hypervisor, если платформа предоставляет такую метрику.

Средняя загрузка всех cores может быть невысокой при перегрузке одного core, ограниченной affinity или quota. Поэтому смотрят per-core utilization, task states и cgroup counters с подходящим временным разрешением. Один низкий общий процент CPU не исключает scheduling bottleneck.

# Как NUMA locality и huge pages влияют на задержки и расход памяти?

В **NUMA** доступ к памяти локального node обычно отличается по latency и bandwidth от удалённого. Placement threads и allocation policy, включая first-touch в подходящих случаях, влияют на locality и миграции pages.

**Huge pages** уменьшают число page-table entries и TLB pressure, но могут увеличить внутреннюю фрагментацию, требования к contiguous memory и задержки allocation или compaction. Transparent и явно управляемые huge pages имеют разный lifecycle. Изменения проверяют на конкретной БД или runtime, учитывая tail latency; универсальное «включить для ускорения всего» неверно.

# Как PID, mount, network, user и другие namespaces создают разные представления ресурсов?

**PID namespace** меняет видимость идентификаторов процессов, **mount** — представление дерева mounts, **network** — interfaces, routing и sockets. **User namespace** отображает identities и связанную область привилегий. Дополнительно существуют IPC, UTS и другие namespace types.

Они дают отдельные представления общих ресурсов, но не создают отдельное kernel для каждой группы. Процесс может одновременно принадлежать разным namespace instances разных типов. Переход между namespaces и управление ими требуют соответствующих прав; namespace isolation дополняют permissions, MAC и resource limits. [Namespaces](https://man7.org/linux/man-pages/man7/namespaces.7.html).

# Как cgroups и namespaces взаимодействуют в контейнере, не заменяя полноценную security boundary?

**Namespaces** в основном определяют, что процесс видит, а **cgroups** — как учитываются и ограничиваются его ресурсы. Container runtime объединяет эти механизмы с filesystem, credentials, capabilities и другими ограничениями.

Доступ к host mounts, privileged mode, широкие capabilities или уязвимость общего kernel способны ослабить границу. Resource limit также не является защитой от каждого вида DoS: CPU, memory, PIDs и I/O имеют разные controllers и зависимости. Проверяют фактическую configuration и hierarchy, а не только наличие слова «container» в deployment. [Cgroup model](https://docs.kernel.org/admin-guide/cgroup-v2.html).

# Как исследовать memory leak, allocator fragmentation и рост cache внутри ограниченного процесса?

Сначала разделяют рост live application objects, **allocator fragmentation**, native allocations и file cache. Heap profile может быть стабильным, пока RSS растёт из-за allocator arenas или библиотек вне управляемого heap.

Сопоставляют heap metrics, mappings, RSS/PSS и cgroup breakdown во времени под сравнимой нагрузкой. Memory, освобождённая приложением, не обязана сразу возвращаться ОС. Проверяют, стабилизируется ли потребление после рабочей фазы, и исследуют ownership удерживаемых объектов. Повышение limit может отсрочить OOM, но не объясняет причину роста и не заменяет оценку безопасного memory budget.
