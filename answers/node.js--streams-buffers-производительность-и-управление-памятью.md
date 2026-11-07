# Как Readable, Writable, Duplex и Transform задают разные роли Node.js streams?

**Readable** предоставляет данные, **Writable** принимает их, **Duplex** объединяет независимые читаемую и записываемую стороны, а **Transform** производит output из input. Socket — типичный duplex, compression — transform.

В byte mode передаются bytes или соответствующие chunks, в **object mode** — отдельные JavaScript objects по правилам API. Реализация transform должна сообщать завершение работы и errors корректно, иначе pipeline может зависнуть. Наличие stream interface не гарантирует ограниченную память, если внутри stage накапливается весь input или бесконечная очередь async tasks.

# Как write return value, drain и highWaterMark управляют потоком данных?

Если `write(chunk)` возвращает **false**, chunk обычно уже принят в локальную очередь, но producer должен прекратить добавление и дождаться подходящего `drain`. Это не самостоятельная ошибка записи и не причина отправить тот же chunk повторно.

**highWaterMark** — threshold управления buffering, а не строгий максимальный размер всей памяти pipeline. В object mode он считает objects, размер которых может сильно различаться. Продолжение writes без backpressure увеличивает buffering и GC pressure. Отдельно обрабатывают error и закрытие, поскольку drain может уже не наступить. [Backpressure Node.js](https://nodejs.org/en/learn/modules/backpressuring-in-streams).

# Как paused mode, flowing mode и async iteration меняют чтение Readable stream?

В **paused mode** consumer явно получает данные предусмотренным способом, а **flowing mode** испускает chunks через соответствующий механизм доставки. Подписка на `data`, piping и `resume` способны менять режим; переключения выполняют осознанно.

**Async iteration** позволяет последовательное потребление с `await`, что удобно для ограниченной обработки. Не смешивают несколько consumption APIs без понимания результата, иначе легко получить пропуски или неожиданное движение данных. Досрочный выход из iteration имеет lifecycle-семантику выбранного iterator, часто включая разрушение stream; сохранение его для дальнейшего чтения требует подходящего API и версии.

# Как pipeline и finished координируют ошибки, завершение и освобождение ресурсов streams?

`pipeline` связывает stages, передаёт errors и организует завершение или уничтожение участников по documented rules. Promise-вариант позволяет ждать общий result. `finished` наблюдает предусмотренное завершение конкретного stream, включая relevant ошибки и premature close.

Это надёжнее ручной цепочки `pipe` без общего lifecycle, но не заменяет cleanup внешнего DB cursor или temporary file, если он не привязан к stream. Для HTTP destination учитывают, что error cleanup может уже закрыть socket и не оставить возможность отправить новый error response. [Streams API](https://nodejs.org/api/stream.html).

# Как AbortSignal и преждевременное закрытие клиента влияют на streaming pipeline?

**AbortSignal** передаёт намерение отменить работу, но каждый stage и внешний API должны поддержать его или иметь явную cleanup-логику. Обрыв клиента должен остановить ненужное чтение и преобразование, а не оставить download в фоне.

В pipeline согласуют abort, errors и premature close с одной причиной завершения и освобождением resources. Cancellation не откатывает уже записанные bytes или внешний эффект. Проверяют поведение source, transform и sink при отмене в разных точках, включая отсутствие listeners leaks. Доступные overloads и helpers зависят от Node.js version. [AbortController](https://nodejs.org/api/globals.html#class-abortcontroller).

# Как Buffer, Uint8Array, ArrayBuffer и encoding представляют бинарные данные?

**Buffer** — Node.js byte-oriented API, связанный с `Uint8Array`; **ArrayBuffer** представляет underlying memory, а typed array задаёт view. Один storage может иметь несколько views с разными offsets и lengths.

**Encoding** определяет преобразование между bytes и text, а не является свойством каждого произвольного byte buffer. UTF-8, hex и base64 задают разные интерпретации. Учитывают, копирует ли выбранный constructor данные или разделяет memory. Передача `buffer.buffer` без корректных byte offset и length может раскрыть лишний диапазон underlying allocation. [Buffer](https://nodejs.org/api/buffer.html).

# Чем Buffer.alloc, Buffer.allocUnsafe, slice и subarray отличаются по инициализации и совместному хранению?

`Buffer.alloc` инициализирует память по предусмотренному default, обычно нулями. **allocUnsafe** не следует читать или отправлять до полного заполнения нужных bytes: он выбирает другой путь allocation и не обещает обычную zero-initialization без дополнительных условий.

**Buffer slice/subarray** дают views с shared storage, поэтому изменение одной области может быть видно другой, а маленький view — удерживать большую allocation. Это отличается от copy-семантики некоторых одноимённых typed-array методов. Для независимой копии используют соответствующий явный API. Проверяют ownership, pooling и lifetime. [Buffer views](https://nodejs.org/api/buffer.html).

# Почему chunk boundary не совпадает с границей UTF-8 символа или сообщения протокола?

Stream chunk формируется buffering и transport, поэтому один UTF-8 символ может быть разделён между chunks, а несколько application messages — прийти вместе. Вызов `toString` независимо для каждого fragment способен повредить текст.

**StringDecoder** или подходящий streaming decoder сохраняет неполную последовательность до следующего chunk. Протоколу дополнительно нужен framing: decoder символов не выделяет автоматически JSON messages или lines. Ограничивают накопленный размер и обрабатывают незавершённый input в конце. Простое объединение всех chunks решает границы только ценой чтения целого body в memory. [StringDecoder](https://nodejs.org/api/string_decoder.html).

# Как heapUsed, external, arrayBuffers и RSS описывают разные области памяти Node.js?

**heapUsed** описывает занятую часть JS heap V8, **external** — соответствующую память native объектов, связанную с JS, а **arrayBuffers** — учёт backing stores, включая relevant Buffer allocations. ArrayBuffers входят в предусмотренный broader accounting, поэтому метрики нельзя бездумно складывать.

**RSS** отражает resident process memory и может расти иначе из-за native allocations, shared pages или fragmentation. При worker threads scope показателей различается. Низкий heapUsed не исключает memory pressure container. Сопоставляют process metrics с cgroup и workload во времени. [process.memoryUsage](https://nodejs.org/api/process.html#processmemoryusage).

# Как V8 garbage collection, allocation rate и удерживаемые references влияют на latency?

V8 GC освобождает недостижимые объекты, но не те, которые application продолжает удерживать через caches, listeners, closures или queues. Высокий **allocation rate** создаёт дополнительную работу collection и может влиять на latency, даже если после GC heap уменьшается.

Различают временные peaks, рост live set и удержание external buffers. Увеличение heap limit не исправляет утечку и может изменить паузы. Сначала измеряют GC и application behavior под реальной concurrency, затем корректируют ownership и размер буферов. [Memory diagnostics](https://nodejs.org/en/learn/diagnostics/memory/understanding-and-tuning-memory).

# Как расследовать рост памяти через heap snapshots, allocation profiles и native memory metrics?

Сравнивают **heap snapshots** при сопоставимой нагрузке, исследуют retained size и paths удержания, а allocation profiles показывают, где создаётся много объектов. Для native или external роста нужны дополнительные metrics: JS snapshot не описывает всю RSS.

Snapshot может остановить main thread, потребовать значительную дополнительную память и содержать secrets. Его собирают с ограниченной области и подходящей resource capacity, защищают artifact. Диагноз подтверждают изменением retained objects после исправления, а не наличием просто большого класса. Снимки разных phases без контроля нагрузки дают ложный leak. [Heap snapshot](https://nodejs.org/en/learn/diagnostics/memory/using-heap-snapshot).

# Как ограничить concurrency и buffering при streaming большого числа запросов?

Backpressure внутри одного pipeline ограничивает только его пути по своим thresholds. При тысячах connections суммарные buffers, transforms, queues и retained request context могут превысить budget, даже если каждый stream реализован корректно.

Ограничивают **concurrency**, input/body size, inflight work и очередь ожидания, задают deadline и cancellation. Не создают unbounded `Promise.all` поверх каждой chunk. Проверяют slow clients, slow downstream и errors с расчётом общей memory, а не только throughput одного transfer. Admission control и rate policy позволяют отказать раньше, чем process упадёт от исчерпания ресурсов.
