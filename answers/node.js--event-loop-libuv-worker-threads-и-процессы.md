# Как V8, libuv и bindings разделяют выполнение JavaScript и системного I/O в Node.js?

**V8** выполняет JavaScript и управляет его heap, **libuv** предоставляет event loop и системные I/O mechanisms, а **bindings** связывают JavaScript API с native implementation. Main JavaScript thread не выполняет всё системное ожидание сам.

Это не означает отдельный thread на каждый запрос. Network readiness обычно использует ОС, а часть операций обслуживается worker pool или native components. После готовности result callback снова требует времени на JS execution. Большой CPU callback способен задержать другие завершившиеся операции, даже если их I/O был асинхронным.

# Как timers, poll и check phases влияют на порядок callbacks в современных Node.js?

**Timers** обслуживают callbacks, чьё минимальное ожидание прошло, **poll** связан с обработкой I/O, **check** — с `setImmediate`. Между предусмотренными точками выполняются дополнительные очереди и mechanics Node.js, поэтому простая круговая схема неполна.

Начиная с libuv 1.45/Node.js 20 поведение timers относительно poll изменилось по сравнению со старыми версиями. Timer не гарантирует запуск точно в назначенную миллисекунду: занятый JS и другие callbacks добавляют задержку. Для вывода о порядке фиксируют версию и execution context. [Node.js Event Loop](https://nodejs.org/en/learn/asynchronous-work/event-loop-timers-and-nexttick).

# Как process.nextTick и Promise microtasks могут задержать I/O и timers?

`process.nextTick` использует специальную очередь Node.js, а Promise reactions и `queueMicrotask` — microtask-механизм. Их выполнение в предусмотренных точках может происходить до продолжения обычных I/O callbacks.

Рекурсивное добавление nextTick или бесконечная цепочка microtasks способны вызвать **starvation** event loop. Для длительной работы нужен контролируемый yield или перенос вычислений, а не только Promise. Относительный порядок нельзя описать без контекста: top-level ESM уже исполняется через другую scheduling-модель, чем обычный CommonJS script. [process.nextTick](https://nodejs.org/en/learn/asynchronous-work/understanding-processnexttick).

# Почему порядок setTimeout и setImmediate нельзя объявить одинаковым для любого контекста?

`setTimeout` становится доступен после предусмотренного минимального интервала, а **setImmediate** выполняется в check phase. На верхнем уровне порядок зависит от timings и контекста, поэтому результат одного запуска не задаёт общее правило.

В типичном I/O callback setImmediate и timer попадают в разные этапы, что позволяет описать более определённый сценарий при зафиксированной версии. Вложенные callbacks, microtasks и изменения libuv тоже важны. Если приложению нужна строгая последовательность, её задают явно через зависимости, а не выбирают timer на основании случайного порядка console output.

# Какие операции используют libuv thread pool и как его насыщение влияет на несвязанные запросы?

**Libuv thread pool** обслуживает часть filesystem operations, `dns.lookup`, некоторые crypto и compression APIs. Большинство обычных network socket operations не требуют выделять pool thread для каждого соединения; `dns.resolve` имеет иной путь, чем lookup.

Общий pool может быть занят дорогими password hashes и задержать seemingly unrelated file operations. Размер и конкуренцию оценивают по измерениям, а не увеличивают без ограничения: больше threads расходует ресурсы и может конкурировать за CPU. Pool связан с process и разделяется соответствующими участниками, включая worker threads по documented model.

# Чем асинхронный API отличается от CPU-работы, реально вынесенной из main thread?

**Async API** позволяет не ждать результат синхронно в вызывающем коде, но не обещает перенос всех вычислений в другой thread. Код внутри `async function` исполняется на текущем JS thread до и после подходящих async boundaries.

Большой `JSON.parse`, цикл или тяжёлый regex могут блокировать main thread независимо от наличия Promise. Для CPU-bound работы используют worker pool, другой process или подходящий внешний service, учитывая стоимость передачи данных. Для обычного async I/O дополнительный worker часто не нужен. Сначала подтверждают, где именно расходуется CPU и ожидание.

# Как worker_threads изолируют JavaScript execution и когда нужен worker pool?

**Worker thread** имеет собственный JS execution context и V8 isolate, позволяя параллельные CPU-вычисления в одном process. Main thread обменивается сообщениями и не должен создавать новый worker для каждой крошечной операции без оценки overhead.

**Worker pool** ограничивает concurrency, очередь и стоимость startup. У задач определяют deadline, cancellation, failure policy и передачу context для диагностики. Native process-level resources остаются общими в предусмотренных пределах, поэтому worker не является полной process isolation boundary. Под нагрузкой проверяют копирование payloads и общий CPU budget. [Worker threads](https://nodejs.org/api/worker_threads.html).

# Как structured clone, transferable objects и SharedArrayBuffer различаются при обмене между workers?

**Structured clone** создаёт поддерживаемую копию данных и не сохраняет произвольную функцию или всю prototype-семантику исходного объекта. **Transfer** передаёт ownership подходящего buffer без обычной полной копии и может сделать прежние views недействительными у sender.

**SharedArrayBuffer** оставляет общую память, поэтому нужны protocol и синхронизация, например через Atomics; общность bytes не обеспечивает race-free application logic. Для Buffer учитывают underlying pool и допустимость transfer: несколько views могут ссылаться на одно storage. Выбор проверяют по размеру payload и жизненному циклу references. [Обмен workers](https://nodejs.org/api/worker_threads.html).

# Как child_process и cluster отличаются от worker_threads по памяти и отказам?

**Child process** имеет отдельное адресное пространство и lifecycle ОС. **Cluster** использует несколько Node.js processes для распределения соответствующей серверной работы и не делает JS heap общим. **Worker threads** дают отдельные isolates внутри одного process и допускают shared memory.

Выбор зависит от CPU, isolation, IPC и восстановления. Необработанный worker error и отказ native process имеют разную область воздействия; полную защиту от native crash нельзя обещать thread-границей. Для subprocess выбирают безопасный API передачи arguments, контролируют stdio, resource limits и остановку дочерних процессов. [Child processes](https://nodejs.org/api/child_process.html).

# Как event loop utilization и event loop delay помогают отличить CPU block от внешнего ожидания?

**Event loop utilization** оценивает занятость loop по модели Node.js, а **event loop delay** показывает задержку его обслуживания относительно наблюдаемого расписания. Это не прямые синонимы process CPU percentage.

Высокая utilization и delay могут указывать на blocking JS или синхронные операции, но cause уточняют profile. При ожидании БД или thread pool request latency способна расти при свободном loop. Сопоставляют одинаковые временные окна, CPU, GC и downstream timings. Измерения worker и main thread могут требовать отдельного scope. [perf_hooks](https://nodejs.org/api/perf_hooks.html).

# Как uncaughtException, unhandledRejection и отказ worker влияют на жизненный цикл Node.js сервиса?

**uncaughtException** означает, что ошибка вышла за предусмотренную обработку; продолжать обычную работу как после безвредного события опасно из-за неизвестного application state. Используют ограниченную диагностику и управляемое завершение с внешним механизмом восстановления.

Для **unhandledRejection** реакция зависит от версии, flags и установленных handlers; отсутствие видимого crash не делает потерянный rejection корректным. Worker failure обрабатывают через его lifecycle и policy незавершённых задач. Hooks не заменяют обычный error handling и idempotency. Проверяют завершение logs и ресурсов без бесконечного ожидания. [Process errors](https://nodejs.org/api/process.html).

# Как graceful shutdown координирует HTTP server, workers, очереди и открытые handles?

Сначала прекращают принимать новую работу, затем ограниченное время завершают inflight HTTP requests и tasks, останавливают subscriptions и workers, закрывают pools и telemetry. Для WebSockets и multiplexed connections нужен отдельный lifecycle, а не только ожидание обычных requests.

Все этапы укладывают в общий shutdown deadline, сохраняя корректную policy для неоконченных jobs. Открытые handles и timers способны удерживать process, тогда как один pending Promise не гарантирует его жизнь. Немедленный выход может обрезать записи и отправку logs. Shutdown проверяют сигналом и сбоями зависимостей, а не только штатным завершением теста.
