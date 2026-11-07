# Как ownership, move, Copy и Drop управляют ресурсами Rust без tracing garbage collector?

У значения есть владелец; передача **ownership** определяет, кто отвечает за ресурс. Для типов вроде `String` присваивание обычно выполняет `move`: прежнее binding больше нельзя использовать как владельца того же значения. Это не означает глубокое копирование heap-данных.

Типы с `Copy`, например многие числовые значения, можно неявно копировать; `Clone` выполняет явно заданное дублирование. При нормальном освобождении владельца вызывается `Drop`, реализующий RAII для памяти, файлов и других ресурсов. Rust не требует tracing GC, но допускает reference counting; утечки и аварийное завершение всё ещё возможны. [Ownership](https://doc.rust-lang.org/book/ch04-01-what-is-ownership.html).

# Как правила borrowing для &T и &mut T предотвращают недопустимый доступ к памяти?

`&T` даёт shared borrow без передачи владения, а `&mut T` — exclusive borrow с возможностью изменения. Для пересекающихся активных обращений к одним данным допускаются несколько shared references либо эксклюзивная mutable reference. Владелец не может освободить данные, пока они нужны borrow.

Это предотвращает use-after-free и небезопасное сочетание чтения и изменения в safe Rust. Borrow может закончиться после последнего использования, раньше конца блока. Interior mutability через `Cell`, `RefCell` или locks сохраняет соответствующие гарантии иным способом; она не разрешает произвольную гонку. [References and Borrowing](https://doc.rust-lang.org/book/ch04-02-references-and-borrowing.html).

# Что описывают lifetimes в Rust и почему аннотация не продлевает жизнь значения?

**Lifetime** описывает область допустимого использования reference и связь между borrowed данными. Например, одинаковая `'a` у входных references и результата функции требует, чтобы возвращаемый borrow оставался корректным в выбранной общей области. Compiler часто выводит это без явных аннотаций.

Аннотация не продлевает хранение и не позволяет вернуть reference на уничтожаемую локальную переменную. Если результат должен жить независимо, возвращают owned value или меняют организацию владения. Ограничение `T: 'static` у task означает отсутствие краткоживущих borrowed данных внутри `T`, а не обязательную жизнь самого значения до завершения программы. [Lifetimes](https://doc.rust-lang.org/book/ch10-03-lifetime-syntax.html).

# Как String, str, Vec<T> и slices различаются по владению и размещению данных?

`String` владеет изменяемым UTF-8 buffer, а `str` представляет строковые данные переменной длины и обычно используется через `&str`. `Vec<T>` владеет динамическим массивом, `&[T]` и `&mut [T]` дают borrowed views без отдельного владения элементами.

Owned container хранит metadata о buffer, а сами элементы обычно находятся в heap; metadata может располагаться там, где хранится владелец. API, которому достаточно чтения, часто принимает `&str` или slice и не требует allocation. Индексация строки по номеру символа не равна индексации bytes: UTF-8 имеет переменную длину, а slicing требует корректных границ.

# Как Option, Result, оператор ? и panic разделяют обработку ошибок Rust-сервиса?

`Option<T>` описывает наличие или отсутствие значения, а `Result<T, E>` — успех либо ожидаемую ошибку. `match`, combinators и оператор `?` позволяют обрабатывать или передавать результат вверх; для `Result` может потребоваться преобразование типа ошибки.

В сервисе domain errors явно переводят в протокол ответа и наблюдаемый контекст, сохраняя внутренние детали вне публичного сообщения. `panic` предназначен для нарушенных предположений и невосстановимых ситуаций, а не обычного некорректного ввода. Его последствия зависят от unwind/abort strategy и границы task или thread; `unwrap()` в request path может превратить ожидаемую ошибку в аварийный путь.

# Как traits, generics и dyn Trait различаются по dispatch и стоимости абстракции?

`Trait` задаёт доступное поведение типа. С generics и trait bounds compiler обычно выполняет **static dispatch**, создавая специализированный код через monomorphization. Это позволяет inlining, но может увеличить размер binary и время compilation.

`dyn Trait` использует dynamic dispatch через vtable и позволяет работать с разными concrete types через общий interface. Сам dynamic dispatch не требует heap: возможен `&dyn Trait`; `Box<dyn Trait>` добавляет owned heap allocation. Не каждый trait совместим с `dyn`. Выбор зависит от необходимости heterogeneous collections, стабильных границ API и измеренной стоимости, а не от правила «generics всегда лучше».

# Как Send и Sync определяют возможность передачи и совместного доступа между потоками?

**`Send`** означает, что владение значением можно безопасно передать между threads. **`Sync`** означает, что shared reference `&T` можно безопасно передавать между threads: формально `T: Sync`, когда `&T: Send`.

Эти auto traits выводятся из состава типа с учётом специальных реализаций. Например, `Rc<T>` не подходит для такого межпоточного sharing, поскольку счётчик не атомарный. `Arc<T>` делает thread-safe управление ownership, но не превращает произвольный `T` в безопасное mutable state. Ручная реализация `Send` или `Sync` требует `unsafe` и доказательства инвариантов. [Send and Sync](https://doc.rust-lang.org/book/ch16-04-extensible-concurrency-sync-and-send.html).

# Как выбирать Arc, Mutex, RwLock, atomics и channels для разделяемого состояния Rust?

`Arc` даёт разделённое владение, а `Mutex` сериализует доступ к изменяемому состоянию. `RwLock` допускает несколько readers либо writer, но его преимущество зависит от contention. Atomics подходят для ограниченных независимых операций с явно выбранной memory ordering; несколько atomic fields не становятся одной транзакцией.

Channels позволяют передавать владение сообщениями и уменьшать shared mutable state; bounded channel дополнительно ограничивает backlog. В async-коде не удерживают обычный blocking lock через `.await`; для ожидания приостановки используют подходящие async primitives или меняют модель. Даже memory-safe программа может иметь deadlocks, starvation и бизнес-гонки.

# Как Future, async/await, Tokio tasks и spawn_blocking организуют серверную конкурентность?

`async fn` создаёт **Future**, которое продвигается при polling executor. `.await` позволяет отдать управление, когда операция не готова, но не превращает blocking I/O или длинный CPU loop в неблокирующую работу. Tokio планирует tasks на runtime; `tokio::spawn` требует подходящих `Send` и `'static` данных.

`spawn_blocking` переносит blocking closure в отдельный pool. Для CPU-heavy работы дополнительно ограничивают параллелизм: большой pool не означает подходящий CPU budget. Уже начатую blocking closure нельзя обычно остановить через abort её handle; ей нужен кооперативный протокол. API и детали runtime сверяют с версией. [Spawning](https://tokio.rs/tokio/tutorial/spawning), [spawn_blocking](https://docs.rs/tokio/latest/tokio/task/fn.spawn_blocking.html).

# Как строить Rust HTTP-сервис с ограничением конкурентности, отменой и graceful shutdown?

HTTP layer связывает routing, typed application state, input validation, domain errors и tracing. Ограничивают body size, concurrency, очередь и DB pool, а timeout/deadline распространяют на зависимости. Клонирование `Arc` для handlers не отменяет потребности в согласованном доступе к mutable state.

Cancellation требует явного протокола: прекращение polling future не откатывает уже отправленный платёж или commit. При shutdown прекращают принимать новую работу, уведомляют tasks, дожидаются завершения в пределах deadline и закрывают ресурсы. Отброшенный `JoinHandle` сам по себе не отменяет task. Проверяют также streams и background workers. [Tokio: Graceful Shutdown](https://tokio.rs/tokio/topics/shutdown).

