# Как построить диагностику Linux от пользовательского симптома к CPU, памяти, диску и сети?

Сначала формулируют наблюдаемый **симптом**: рост latency, ошибки, падение throughput или завершение процесса. Фиксируют время, affected workloads и последние изменения, затем проверяют CPU, memory pressure, storage и network вместе с зависимостями приложения.

Идут от широкого наблюдения к конкретной гипотезе, например «threads ждут disk I/O», а не запускают все tracing tools сразу. Сравнивают host и cgroup metrics, поскольку процесс может упираться в свой limit при свободном host. Вывод подтверждают несколькими независимыми сигналами и воспроизводимой проверкой.

# Как load average, utilization, saturation и latency различаются при оценке нагрузки?

**Utilization** показывает степень использования ресурса, **saturation** — наличие неудовлетворённой потребности или очереди, **latency** — время выполнения операции. Высокая utilization допустима для batch, но опасна для latency-sensitive workload без запаса.

Linux **load average** включает runnable tasks и определённые tasks в uninterruptible sleep, поэтому не является процентом CPU. Большой load может быть связан с I/O. Учитывают число доступных CPU, affinity, quota и временное окно. Среднее значение скрывает короткие bursts и дисбаланс между отдельными cores.

# Как strace показывает системные вызовы и какие задержки и риски вносит tracing?

**strace** показывает syscalls, arguments, результаты и при нужных настройках время наблюдаемого вызова. Он помогает увидеть `ENOENT`, отказ permissions, блокирующий `read`, частые короткие записи и другие interactions с kernel.

Длительный syscall может отражать ожидание, а не CPU внутри ядра. Tracing через ptrace способен заметно замедлять особенно syscall-heavy процесс и менять timing races. Ограничивают набор процессов, вызовов, длительность и размер данных. Arguments и buffers могут раскрывать credentials или пользовательское содержимое; вывод обрабатывают как чувствительную диагностику. [strace](https://man7.org/linux/man-pages/man1/strace.1.html).

# Как perf sampling, call graphs и flame graphs помогают искать CPU bottleneck?

**Perf sampling** периодически фиксирует execution context по выбранному событию, например CPU cycles. **Call graph** связывает samples с цепочками вызовов, а flame graph показывает накопленную ширину stacks по количеству соответствующих samples.

Ширина flame graph обычно не является временем одной конкретной операции, а горизонтальная ось — обычной временной шкалой. Сначала выбирают правильный event и scope, затем исследуют горячие stacks. Отсутствующие symbols, плохой unwinding и sampling bias способны исказить вывод. Гипотезу проверяют на исходниках и метриках нагрузки. [Perf tutorial](https://perfwiki.github.io/main/tutorial/).

# Как on-CPU и off-CPU profiling различают вычисления и ожидание?

**On-CPU profiling** показывает, где task выполняется на процессоре. **Off-CPU profiling** исследует интервалы, когда она не выполняется, например ждёт lock, I/O или scheduling. Для общей latency часто нужны оба вида данных.

Низкая CPU utilization при медленном запросе не исключает CPU quota или длинную очередь runnable tasks. Off-CPU stack показывает место блокировки, но не всегда её первопричину: lock может удерживать другой thread, занятый удалённым API. Различают ожидание ресурса, намеренный sleep и работу, выполняемую другим участником.

# Как vmstat, iostat, pidstat и pressure stall information дополняют друг друга?

`vmstat` даёт общую картину tasks, памяти и активности системы. `iostat` помогает исследовать block devices, queueing и latency, а `pidstat` — потребление отдельных tasks и их I/O или switches.

**PSI** показывает время pressure stalls из-за CPU, memory или I/O и помогает связать нехватку ресурса с остановкой полезной работы. Интерпретируют scope и значения `some`/`full` по поддержке kernel. Показатели разных layers не складывают механически: высокий device utilization на современном storage не всегда означает одну и ту же степень saturation. [Pressure Stall Information](https://docs.kernel.org/accounting/psi.html).

# Как tcpdump и packet capture помогают отличить DNS, TCP и TLS-проблемы?

**Packet capture** позволяет проверить наличие DNS requests и answers, TCP handshake, retransmissions, resets и timing обмена. Выбирают interface, capture filter и достаточную длину пакета, ограничивая объём и время.

Для TLS видны транспорт и доступные handshake metadata, но encrypted application data обычно не раскрываются; причину отказа дополняют logs клиента и сервера. Offloading и место capture могут создавать необычные размеры packets или ложные checksum warnings. Capture сам может терять packets. Не считают отсутствие packet доказательством отсутствия отправки, пока не проверили точку наблюдения.

# Как ss, socket states и retransmissions помогают диагностировать сетевые соединения?

`ss` показывает sockets, states, очереди и при доступных правах связь с processes. Много `SYN-SENT` может указывать на незавершённое установление связи, а устойчивый `CLOSE-WAIT` — на приложение, не закрывающее свою сторону после peer close.

`TIME-WAIT` может быть нормальным следствием активных соединений, а не leak. Retransmissions рассматривают вместе с RTT, loss, congestion и counters интерфейса. Рост send queue не доказывает локальную CPU-проблему: другой endpoint может медленно читать. Проверяют временной тренд и затронутые направления, а не один снимок числа sockets.

# Как eBPF tracing использует kernel hooks и чем отличается от произвольного kernel module?

**eBPF** загружает проверяемые программы, привязанные к поддерживаемым hooks: tracepoints, kprobes, uprobes и другим механизмам. Verifier и runtime ограничивают допустимые действия по модели конкретного типа программы; maps и buffers передают результаты userspace.

Это отличается от обычного kernel module с произвольным kernel-кодом, но не означает нулевой overhead или отсутствие риска. Доступ зависит от kernel configuration, permissions и capabilities. Для диагностики выбирают минимальные hooks и aggregation, а не копирование всех events. Изменение internal kernel functions может ломать нестабильные probes. [BPF design](https://docs.kernel.org/bpf/bpf_design_QA.html).

# Как symbols, stack unwinding, BTF и CO-RE влияют на достоверность профиля?

**Symbols** связывают адреса с functions, а stack unwinding восстанавливает цепочку вызовов; stripped binaries, inlining, JIT и отсутствие подходящих frame metadata дают неполные или ошибочные stacks. Build IDs и matching debug info помогают сопоставить правильную сборку.

**BTF** описывает типы для BPF, а **CO-RE** позволяет адаптировать обращения к данным kernel между подходящими сборками. CO-RE не гарантирует наличие любого hook, helper или нужного BTF на каждой системе. Неразрешённые frames учитывают как ограничение результата, а не автоматически относят к неизвестной библиотеке. [BTF](https://docs.kernel.org/bpf/btf.html).

# Как ограничить overhead и доступ к чувствительным данным при production profiling?

Определяют минимальную цель, scope и длительность, выбирают sampling вместо полного event stream, когда это достаточно. Следят за overhead самого collector, lost events и размером buffers, сохраняя возможность остановить сбор.

Доступ выдаётся только на необходимые processes и interfaces в пределах поддерживаемых mechanisms. Не захватывают arguments, payloads и environment без нужды; raw artifacts защищают и удаляют по согласованной retention. Сравнивают поведение с collector и без него. Успешная загрузка profiler не доказывает, что измерение не изменило исследуемый workload.

# Как подтвердить найденную причину и измерить эффект исправления без ложных выводов?

Формулируют предсказание: если причина в lock contention, после изменения должен уменьшиться соответствующий wait при сравнимом трафике и сохраниться корректность. Сопоставляют baseline и новую версию по throughput, latency percentiles, errors и resource usage.

Контролируют объём данных, cache warmup, concurrency и влияние соседних workloads. Одновременная смена нескольких факторов мешает причинному выводу. Улучшение среднего не компенсирует рост tail latency или ошибок. Сохраняют артефакты и допущения, а при недостатке samples обозначают неопределённость вместо точного диагноза.
