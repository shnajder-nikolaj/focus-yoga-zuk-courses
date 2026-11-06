# Как реализовать полифил `Array.prototype.map` без использования встроенного `map`?

Нужно пройти по элементам массива, вызвать callback для каждого существующего индекса и записать результаты в новый массив.

```
Array.prototype.myMap = function (callback, thisArg) {
  if (this == null) {
    throw new TypeError('Array is null or undefined');
  }

  if (typeof callback !== 'function') {
    throw new TypeError('Callback must be a function');
  }

  const source = Object(this);
  const result = new Array(source.length);

  for (let i = 0; i < source.length; i++) {
    if (i in source) {
      result[i] = callback.call(thisArg, source[i], i, source);
    }
  }

  return result;
};
```

Ключевые особенности:

- Исходный массив не изменяется.
- Callback получает `value`, `index`, `array`.
- `thisArg` задаёт контекст вызова callback.
- Разреженные массивы сохраняют пропущенные индексы благодаря проверке `i in source`.

Это упрощённый полифил: полноценный `map` дополнительно учитывает `ToLength`, наследование массивов через `Symbol.species` и другие требования спецификации.

# Как реализовать полифил `Array.prototype.reduce`?

`reduce` последовательно вычисляет аккумулятор, передавая результат предыдущей итерации в следующую.

```
Array.prototype.myReduce = function (callback, initialValue) {
  if (this == null) {
    throw new TypeError('Array is null or undefined');
  }

  if (typeof callback !== 'function') {
    throw new TypeError('Callback must be a function');
  }

  const source = Object(this);
  const length = source.length;
  let index = 0;
  let accumulator;

  if (arguments.length > 1) {
    accumulator = initialValue;
  } else {
    while (index < length && !(index in source)) {
      index++;
    }

    if (index === length) {
      throw new TypeError('Reduce of empty array');
    }

    accumulator = source[index++];
  }

  for (; index < length; index++) {
    if (index in source) {
      accumulator = callback(
        accumulator,
        source[index],
        index,
        source
      );
    }
  }

  return accumulator;
};
```

Важные нюансы:

- Если `initialValue` передан, аккумулятор начинается с него.
- Если не передан, используется первый существующий элемент.
- Если массив пустой или не содержит элементов и начальное значение отсутствует, выбрасывается `TypeError`.
- Пропущенные индексы разреженного массива игнорируются.
- Переданный явно `undefined` считается начальным значением.

# Как реализовать упрощённый `Promise.all`?

`Promise.all` принимает итерируемую коллекцию промисов или значений и возвращает промис с массивом результатов.

```
function promiseAll(iterable) {
  return new Promise((resolve, reject) => {
    const results = [];
    let remaining = 0;
    let index = 0;

    for (const item of iterable) {
      const currentIndex = index++;
      remaining++;

      Promise.resolve(item).then(
        value => {
          results[currentIndex] = value;

          if (--remaining === 0) {
            resolve(results);
          }
        },
        reject
      );
    }

    if (index === 0) {
      resolve([]);
    }
  });
}
```

Принцип работы:

- `Promise.resolve()` позволяет обрабатывать обычные значения и thenable-объекты.
- `currentIndex` сохраняет исходный порядок результатов независимо от времени завершения.
- `remaining` отслеживает количество незавершённых промисов.
- Если любой промис отклоняется, результирующий промис отклоняется с его причиной.
- Пустая коллекция возвращает промис, выполненный с `[]`.

Важно: отклонение `Promise.all` не отменяет остальные операции - они продолжают выполняться.

# Как реализовать очередь асинхронных задач с лимитом конкурентности?

Нужно запускать одновременно не более `limit` задач, а остальные выполнять по мере освобождения слотов.

```
async function runLimited(tasks, limit) {
  if (!Number.isInteger(limit) || limit < 1) {
    throw new RangeError('Invalid limit');
  }

  const results = new Array(tasks.length);
  let nextIndex = 0;
  let failed = false;

  async function worker() {
    while (!failed) {
      const index = nextIndex++;

      if (index >= tasks.length) return;

      try {
        results[index] = await tasks[index]();
      } catch (error) {
        failed = true;
        throw error;
      }
    }
  }

  const workers = Array.from(
    { length: Math.min(limit, tasks.length) },
    () => worker()
  );

  await Promise.all(workers);

  return results;
}
```

Пример:

```
const tasks = [
  () => fetch('/api/1'),
  () => fetch('/api/2'),
  () => fetch('/api/3'),
  () => fetch('/api/4')
];

await runLimited(tasks, 2);
```

Одновременно выполняются максимум два запроса.

Ключевой момент: задачи передаются как функции, возвращающие промисы, а не как уже запущенные промисы. Иначе ограничить конкурентность невозможно.

Результаты сохраняют порядок исходных задач. При ошибке новые задачи перестают запускаться, но уже запущенные автоматически не отменяются.

Сложность по времени - определяется длительностью задач. Дополнительная память - `O(n)` для результатов и рабочих промисов.

# Как реализовать `debounce`, поддерживающий отмену запланированного вызова?

Debounce откладывает выполнение функции до момента, когда после последнего вызова пройдёт заданное время.

```
function debounce(fn, delay) {
  let timer;

  function debounced(...args) {
    clearTimeout(timer);

    timer = setTimeout(() => {
      timer = undefined;
      fn.apply(this, args);
    }, delay);
  }

  debounced.cancel = () => {
    clearTimeout(timer);
    timer = undefined;
  };

  return debounced;
}
```

Пример:

```
const search = debounce(query => {
  console.log('Search:', query);
}, 300);

search('rea');
search('react');

// Отменить запланированный вызов
search.cancel();
```

Каждый новый вызов сбрасывает таймер. Функция выполняется только после периода без новых вызовов.

`cancel()` предотвращает запланированный вызов, но не останавливает функцию, если она уже начала выполняться.

Типичные применения - поиск при вводе текста, валидация форм и обработка `resize`.

# Как реализовать `throttle` с настройками leading и trailing?

Throttle ограничивает частоту выполнения функции: не чаще одного раза за заданный интервал.

- `leading: true` - выполнить сразу при первом вызове после периода бездействия.
- `trailing: true` - выполнить в конце интервала с последними полученными аргументами.

```
function throttle(
  fn,
  wait,
  { leading = true, trailing = true } = {}
) {
  let timer = null;
  let lastInvoke = 0;
  let pendingArgs;
  let pendingThis;

  function invoke() {
    lastInvoke = Date.now();

    const args = pendingArgs;
    const context = pendingThis;

    pendingArgs = undefined;
    pendingThis = undefined;

    fn.apply(context, args);
  }

  function schedule(delay) {
    timer = setTimeout(() => {
      timer = null;

      if (trailing && pendingArgs) {
        invoke();
      }
    }, delay);
  }

  function throttled(...args) {
    if (!leading && !trailing) return;

    const now = Date.now();

    pendingArgs = args;
    pendingThis = this;

    if (lastInvoke === 0 || now - lastInvoke >= wait) {
      if (timer) clearTimeout(timer);
      timer = null;

      if (leading) {
        invoke();
      } else {
        lastInvoke = now;
        schedule(wait);
      }
    } else if (trailing && !timer) {
      schedule(wait - (now - lastInvoke));
    }
  }

  throttled.cancel = () => {
    clearTimeout(timer);
    timer = null;
    lastInvoke = 0;
    pendingArgs = undefined;
    pendingThis = undefined;
  };

  return throttled;
}
```

Пример:

```
const onScroll = throttle(
  () => console.log('scroll'),
  200,
  { leading: true, trailing: true }
);

window.addEventListener('scroll', onScroll);
```

При частых событиях первый вызов выполняется сразу, а последний может выполниться в конце интервала.

Отличие от `debounce`: throttle обеспечивает периодическое выполнение при непрерывных событиях, а `debounce` ждёт паузу.

# Как реализовать глубокое сравнение двух JSON-подобных структур?

Нужно рекурсивно сравнивать значения, типы, количество свойств и вложенные структуры.

```
function deepEqual(a, b) {
  if (Object.is(a, b)) return true;

  if (
    a === null ||
    b === null ||
    typeof a !== 'object' ||
    typeof b !== 'object'
  ) {
    return false;
  }

  if (Array.isArray(a) !== Array.isArray(b)) {
    return false;
  }

  if (Array.isArray(a) && a.length !== b.length) {
    return false;
  }

  const keysA = Object.keys(a);
  const keysB = Object.keys(b);

  if (keysA.length !== keysB.length) {
    return false;
  }

  return keysA.every(key =>
    Object.prototype.hasOwnProperty.call(b, key) &&
    deepEqual(a[key], b[key])
  );
}
```

Особенности:

- `Object.is()` сравнивает примитивы и одинаковые ссылки, отдельно различая `+0` и `-0`.
- Массивы отличаются от обычных объектов.
- Порядок свойств объектов не влияет на результат.
- Вложенные значения сравниваются рекурсивно.

Ограничения: реализация рассчитана на JSON-подобные данные без циклических ссылок. Она не учитывает прототипы, неперечисляемые свойства и специфику `Date`, `Map`, `Set` и других встроенных объектов.

Время работы - `O(n)` при обычных условиях, где `n` - общее количество сравниваемых элементов и свойств.

# Как реализовать глубокое клонирование объектов с обработкой циклических ссылок?

Для обработки циклических ссылок используется `WeakMap`, связывающий исходный объект с его копией.

```
function deepClone(value, seen = new WeakMap()) {
  if (value === null || typeof value !== 'object') {
    return value;
  }

  if (seen.has(value)) {
    return seen.get(value);
  }

  const copy = Array.isArray(value)
    ? []
    : Object.create(Object.getPrototypeOf(value));

  seen.set(value, copy);

  for (const key of Reflect.ownKeys(value)) {
    const descriptor = Object.getOwnPropertyDescriptor(
      value,
      key
    );

    if ('value' in descriptor) {
      descriptor.value = deepClone(
        descriptor.value,
        seen
      );
    }

    Object.defineProperty(copy, key, descriptor);
  }

  return copy;
}
```

Пример:

```
const original = { name: 'Alice' };
original.self = original;

const cloned = deepClone(original);

console.log(cloned !== original); // true
console.log(cloned.self === cloned); // true
```

Почему нужен `WeakMap`:

1. Перед рекурсивным обходом сохраняем соответствие исходного объекта и копии.
2. При повторном обнаружении того же объекта возвращаем существующую копию.
3. Это предотвращает бесконечную рекурсию и сохраняет общие ссылки.

Реализация сохраняет собственные дескрипторы свойств и прототипы обычных объектов, но не воспроизводит внутренние состояния `Date`, `Map`, `Set`, приватные поля классов и другие специальные механизмы.

Для большинства поддерживаемых встроенных типов в современном JavaScript существует `structuredClone()`, который также обрабатывает циклические ссылки, но не поддерживает, например, функции.

# Как реализовать функцию `groupBy` для массива объектов?

`groupBy` объединяет элементы в группы по значению выбранного свойства или результату функции.

```
function groupBy(items, keyFn) {
  const groups = new Map();

  for (const item of items) {
    const key = keyFn(item);

    if (!groups.has(key)) {
      groups.set(key, []);
    }

    groups.get(key).push(item);
  }

  return groups;
}
```

Пример:

```
const users = [
  { name: 'Alice', role: 'admin' },
  { name: 'Bob', role: 'user' },
  { name: 'Charlie', role: 'admin' }
];

const groups = groupBy(users, user => user.role);

console.log(groups.get('admin'));
// Alice и Charlie
```

Почему `Map`, а не обычный объект:

- Поддерживает ключи любых типов, включая объекты.
- Не имеет конфликтов с ключами вроде `__proto__`.
- Сохраняет порядок первого появления ключей.

Сложность - `O(n)` по времени и `O(n)` по памяти.

# Как реализовать преобразование плоского списка категорий в дерево?

Используется двухпроходный алгоритм с `Map` для поиска родительских элементов.

```
function buildTree(items) {
  const nodes = new Map(
    items.map(item => [
      item.id,
      { ...item, children: [] }
    ])
  );

  const roots = [];

  for (const item of items) {
    const node = nodes.get(item.id);

    if (item.parentId == null) {
      roots.push(node);
    } else {
      const parent = nodes.get(item.parentId);

      if (!parent) {
        throw new Error('Parent not found');
      }

      parent.children.push(node);
    }
  }

  return roots;
}
```

Пример:

```
const categories = [
  { id: 1, parentId: null, name: 'Products' },
  { id: 2, parentId: 1, name: 'Electronics' },
  { id: 3, parentId: 2, name: 'Phones' }
];

const tree = buildTree(categories);
```

Принцип работы:

1. На первом проходе создаём копии всех узлов с массивами `children`.
2. На втором проходе привязываем узлы к родителям.
3. Элементы без родителя добавляем в массив корней.

Порядок элементов входного массива не влияет на корректность построения связей.

Сложность - `O(n)` по времени и памяти.

Реализация предполагает уникальные `id` и отсутствие циклов. Для произвольных входных данных необходима дополнительная валидация.

# Как реализовать `flatten` для вложенного массива?

`flatten` рекурсивно раскрывает вложенные массивы в один плоский массив.

```
function flatten(items) {
  const result = [];

  function visit(array) {
    array.forEach(item => {
      if (Array.isArray(item)) {
        visit(item);
      } else {
        result.push(item);
      }
    });
  }

  visit(items);

  return result;
}
```

Пример:

```
flatten([1, [2, [3, 4]], 5]);
// [1, 2, 3, 4, 5]
```

Рекурсивный обход продолжается, пока элемент является массивом. Остальные значения добавляются без изменений.

Метод `forEach` пропускает отсутствующие элементы разреженных массивов.

Сложность - `O(n)` по времени, где `n` - количество всех элементов, и `O(d)` дополнительной памяти для стека вызовов, где `d` - глубина вложенности, не считая выходного массива.

При очень большой глубине рекурсия может вызвать `RangeError: Maximum call stack size exceeded`. Для таких случаев подходит итеративная реализация с явным стеком.

# Как реализовать memoize с учётом аргументов и ограничением размера кэша?

Memoization сохраняет результаты предыдущих вызовов функции и повторно использует их при одинаковых аргументах.

```
function memoize(fn, capacity = 100) {
  if (!Number.isInteger(capacity) || capacity < 1) {
    throw new RangeError('Invalid capacity');
  }

  const cache = new Map();

  return function (...args) {
    const key = JSON.stringify(args);

    if (cache.has(key)) {
      const value = cache.get(key);

      cache.delete(key);
      cache.set(key, value);

      return value;
    }

    const result = fn.apply(this, args);

    cache.set(key, result);

    if (cache.size > capacity) {
      const oldestKey = cache.keys().next().value;
      cache.delete(oldestKey);
    }

    return result;
  };
}
```

Пример:

```
const sum = memoize((a, b) => {
  console.log('Calculating...');
  return a + b;
});

sum(2, 3); // Вычисление
sum(2, 3); // Из кэша
```

Используется стратегия LRU (Least Recently Used): при переполнении удаляется запись, к которой дольше всего не обращались.

Ограничения:

- `JSON.stringify()` подходит только для ограниченного набора аргументов. Например, `undefined`, `NaN` и `null` могут приводить к коллизиям ключей, а циклические ссылки вызывают ошибку.
- Контекст `this` не учитывается при формировании ключа.
- Функция должна быть детерминированной относительно ключа кэша. Кэширование побочных эффектов обычно некорректно.
- Если функция возвращает промис, он тоже кэшируется, включая возможное отклонение.

Для произвольных аргументов нужен другой механизм построения ключей, например вложенные `Map` и `WeakMap`.

# Как реализовать упрощённый EventEmitter с `on`, `off` и `emit`?

`EventEmitter` хранит обработчики по именам событий и вызывает их при генерации события.

```
class EventEmitter {
  #events = new Map();

  on(event, callback) {
    if (!this.#events.has(event)) {
      this.#events.set(event, new Set());
    }

    this.#events.get(event).add(callback);

    return () => this.off(event, callback);
  }

  off(event, callback) {
    const listeners = this.#events.get(event);

    if (!listeners) return;

    listeners.delete(callback);

    if (listeners.size === 0) {
      this.#events.delete(event);
    }
  }

  emit(event, ...args) {
    const listeners = this.#events.get(event);

    if (!listeners) return;

    for (const callback of [...listeners]) {
      callback(...args);
    }
  }
}
```

Пример:

```
const emitter = new EventEmitter();

const unsubscribe = emitter.on('message', data => {
  console.log(data);
});

emitter.emit('message', 'Hello');

unsubscribe();

emitter.emit('message', 'World');
// Обработчик уже не вызывается
```

Особенности:

- `Map` связывает события с наборами обработчиков.
- `Set` предотвращает повторную регистрацию одного обработчика.
- `emit` синхронно вызывает подписчиков.
- Копирование массива обработчиков позволяет безопасно изменять подписки во время обхода.
- `on` возвращает функцию отписки.

Если обработчик выбрасывает исключение, текущий `emit` прерывается. Для изоляции обработчиков нужна отдельная обработка ошибок.

# Как реализовать Pub/Sub с поддержкой одноразовой подписки?

Publish/Subscribe позволяет подписчикам получать сообщения по определённым темам, не зная непосредственного отправителя.

```
function createPubSub() {
  const topics = new Map();

  function subscribe(topic, handler, { once = false } = {}) {
    if (!topics.has(topic)) {
      topics.set(topic, new Set());
    }

    const listeners = topics.get(topic);

    const callback = once
      ? (...args) => {
          unsubscribe();
          handler(...args);
        }
      : handler;

    listeners.add(callback);

    function unsubscribe() {
      listeners.delete(callback);

      if (listeners.size === 0) {
        topics.delete(topic);
      }
    }

    return unsubscribe;
  }

  function publish(topic, data) {
    const listeners = topics.get(topic);

    if (!listeners) return;

    for (const callback of [...listeners]) {
      callback(data);
    }
  }

  return {
    subscribe,
    publish,
    once: (topic, handler) =>
      subscribe(topic, handler, { once: true })
  };
}
```

Пример:

```
const bus = createPubSub();

bus.once('connected', () => {
  console.log('Connected');
});

bus.publish('connected'); // Выведет сообщение
bus.publish('connected'); // Ничего не произойдёт
```

Механизм `once`: обработчик оборачивается функцией, которая сначала удаляет подписку, а затем вызывает исходный обработчик.

Удаление происходит до вызова, поэтому даже рекурсивная публикация того же события не приведёт к повторному выполнению.

Отличие от обычного `EventEmitter` преимущественно архитектурное: Pub/Sub часто использует отдельный посредник (message bus), который развязывает отправителей и получателей.

# Как реализовать retry асинхронного запроса с exponential backoff?

Exponential backoff увеличивает задержку между повторными попытками по экспоненте.

```
async function retry(
  task,
  { retries = 3, baseDelay = 200, maxDelay = 5000 } = {}
) {
  for (let attempt = 0; ; attempt++) {
    try {
      return await task();
    } catch (error) {
      if (attempt >= retries) {
        throw error;
      }

      const delay = Math.min(
        maxDelay,
        baseDelay * 2 ** attempt
      );

      const jitter = 0.5 + Math.random() / 2;

      await new Promise(resolve =>
        setTimeout(resolve, delay * jitter)
      );
    }
  }
}
```

Пример:

```
const response = await retry(
  () => fetch('/api/data').then(res => {
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }),
  { retries: 3 }
);
```

При `baseDelay = 200` задержки до применения `jitter` составляют 200, 400 и 800 мс.

Важные моменты:

- `retries` - количество повторов после первой попытки.
- `jitter` добавляет случайность, чтобы множество клиентов не повторяли запросы одновременно.
- `maxDelay` ограничивает максимальную задержку до применения `jitter`.
- Повторять следует преимущественно временные ошибки: сетевые сбои, HTTP `429`, `502`, `503`, `504`.
- Для неидемпотентных операций нужны дополнительные гарантии, например idempotency key.

`fetch` не отклоняет промис на обычные HTTP-ошибки. Для retry по статусу необходимо самостоятельно проверить `response.ok`.

# Как реализовать `fetchWithTimeout` с отменой через AbortController?

`AbortController` позволяет прервать запрос через передачу `signal` в `fetch`.

```
function fetchWithTimeout(url, ms, options = {}) {
  const controller = new AbortController();

  const abortFromOutside = () => {
    controller.abort(options.signal?.reason);
  };

  if (options.signal?.aborted) {
    abortFromOutside();
  } else {
    options.signal?.addEventListener(
      'abort',
      abortFromOutside,
      { once: true }
    );
  }

  const timer = setTimeout(() => {
    controller.abort(
      new DOMException('Timeout', 'TimeoutError')
    );
  }, ms);

  return fetch(url, {
    ...options,
    signal: controller.signal
  }).finally(() => {
    clearTimeout(timer);

    options.signal?.removeEventListener(
      'abort',
      abortFromOutside
    );
  });
}
```

Пример:

```
try {
  const response = await fetchWithTimeout(
    '/api/data',
    3000
  );
} catch (error) {
  if (error.name === 'TimeoutError') {
    console.log('Request timed out');
  }
}
```

Принцип работы:

1. Создаётся `AbortController`.
2. Его `signal` передаётся в `fetch`.
3. Через заданное время вызывается `controller.abort()`.
4. После завершения запроса таймер и обработчик внешнего сигнала удаляются.

Реализация также поддерживает отмену через `options.signal`.

Важно: `fetch` обычно выполняется после получения заголовков ответа. Поэтому такой таймаут ограничивает ожидание ответа `fetch`, но не обязательно полное чтение тела через `response.json()`.

В современных окружениях также доступны `AbortSignal.timeout()` и `AbortSignal.any()`.

# Как реализовать функцию ограничения количества запросов за интервал времени?

Rate limiting ограничивает количество запусков операций за определённое время.

Один из подходов - Sliding Window, или скользящее временное окно.

```
function rateLimit(fn, limit, interval) {
  if (!Number.isInteger(limit) || limit < 1 || interval <= 0) {
    throw new RangeError('Invalid rate limit');
  }

  const timestamps = [];

  return function (...args) {
    const now = Date.now();

    while (
      timestamps.length &&
      now - timestamps[0] >= interval
    ) {
      timestamps.shift();
    }

    if (timestamps.length >= limit) {
      return Promise.reject(
        new Error('Rate limit exceeded')
      );
    }

    timestamps.push(now);

    return Promise.resolve().then(() =>
      fn.apply(this, args)
    );
  };
}
```

Пример:

```
const limitedFetch = rateLimit(fetch, 5, 1000);

// Не более пяти запусков за любое окно в 1000 мс
limitedFetch('/api/data');
```

Алгоритм хранит временные метки разрешённых запросов. Перед новым запросом удаляются метки, вышедшие за временное окно.

Если количество оставшихся меток достигло лимита, запрос отклоняется.

Отличие от ограничения конкурентности: rate limiting ограничивает частоту запуска, а concurrency limiting - количество одновременно выполняемых задач.

Данная реализация работает в пределах одного экземпляра приложения. Для распределённой системы обычно используют общее хранилище, например Redis.

# Как реализовать `curry` для функции с фиксированной арностью?

Currying преобразует функцию с несколькими аргументами в последовательность функций, которые постепенно собирают аргументы.

```
function curry(fn, arity = fn.length) {
  function collect(collectedArgs) {
    return function (...newArgs) {
      const args = [...collectedArgs, ...newArgs];

      if (args.length >= arity) {
        return fn(...args);
      }

      return collect(args);
    };
  }

  return collect([]);
}
```

Пример:

```
const sum = (a, b, c) => a + b + c;

const curriedSum = curry(sum);

curriedSum(1)(2)(3);   // 6
curriedSum(1, 2)(3);   // 6
curriedSum(1)(2, 3);   // 6
```

Каждый вызов сохраняет накопленные аргументы в замыкании.

Когда их количество достигает `arity`, вызывается исходная функция.

Ограничения:

- `fn.length` не учитывает rest-параметры и параметры с дефолтными значениями начиная с первого такого параметра.
- Для таких функций лучше задавать `arity` явно.
- Реализация не поддерживает плейсхолдеры для пропуска аргументов.
- Контекст `this` исходной функции не сохраняется.

# Как реализовать `compose` и `pipe`?

Обе функции объединяют несколько функций в цепочку, передавая результат одной в следующую.

Разница заключается в порядке выполнения:

- `pipe` - слева направо.
- `compose` - справа налево.

```
function pipe(...fns) {
  return value =>
    fns.reduce((result, fn) => fn(result), value);
}

function compose(...fns) {
  return value =>
    fns.reduceRight((result, fn) => fn(result), value);
}
```

Пример:

```
const add2 = x => x + 2;
const multiply3 = x => x * 3;

pipe(add2, multiply3)(5);    // 21
compose(add2, multiply3)(5); // 17
```

`pipe` сначала прибавляет 2, затем умножает на 3. `compose` делает операции в обратном порядке.

Реализации предполагают, что каждая функция принимает один аргумент, и рассчитаны на синхронные функции.

Для асинхронных цепочек необходимо последовательно обрабатывать промисы через `Promise.resolve()` и `.then()`.

# Как реализовать функцию сравнения версий вида `1.12.3`?

Нужно разделить версии на числовые компоненты и сравнивать их последовательно слева направо.

```
function compareVersions(a, b) {
  const pattern = /^\d+(?:\.\d+)*$/;

  if (!pattern.test(a) || !pattern.test(b)) {
    throw new Error('Invalid version');
  }

  const left = a.split('.');
  const right = b.split('.');

  const length = Math.max(left.length, right.length);

  for (let i = 0; i < length; i++) {
    const x = BigInt(left[i] ?? '0');
    const y = BigInt(right[i] ?? '0');

    if (x > y) return 1;
    if (x < y) return -1;
  }

  return 0;
}
```

Пример:

```
compareVersions('1.12.3', '1.9.10'); // 1
compareVersions('2.0', '2.0.0');     // 0
compareVersions('1.2.3', '1.3.0');   // -1
```

Возвращаемые значения:

- `1` - первая версия больше.
- `-1` - первая версия меньше.
- `0` - версии эквивалентны.

Почему нельзя сравнивать строки напрямую: лексикографическое сравнение считает `'12' < '9'`, хотя численно `12 > 9`.

`BigInt` позволяет избежать потери точности для очень больших компонентов версии.

Алгоритм подходит для числовых версий, но не реализует полный SemVer с prerelease-идентификаторами вроде `1.2.3-beta.1`.

# Как реализовать парсер query string с повторяющимися ключами?

Можно использовать встроенный `URLSearchParams`, который корректно обрабатывает URL-кодирование и повторяющиеся параметры.

```
function parseQuery(query) {
  const params = new URLSearchParams(query);
  const result = Object.create(null);

  for (const [key, value] of params) {
    if (!Object.hasOwn(result, key)) {
      result[key] = value;
    } else if (Array.isArray(result[key])) {
      result[key].push(value);
    } else {
      result[key] = [result[key], value];
    }
  }

  return result;
}
```

Пример:

```
parseQuery('?tag=js&tag=ts&page=2');

// {
//   tag: ['js', 'ts'],
//   page: '2'
// }
```

Особенности:

- Повторяющиеся ключи превращаются в массив.
- Одиночные значения остаются строками.
- `%20` и `+` декодируются в пробелы.
- URL-кодированные символы декодируются автоматически.
- `Object.create(null)` исключает проблемы с унаследованными свойствами, включая `__proto__`.

Все значения остаются строками, поскольку query string не содержит информации об их типах.

# Как реализовать типизированную функцию доступа к вложенному полю объекта?

В TypeScript можно использовать рекурсивные условные типы для проверки пути и определения типа возвращаемого значения.

```
type ValidPath<T, P extends readonly PropertyKey[]> =
  P extends readonly [
    infer K extends PropertyKey,
    ...infer Rest extends PropertyKey[]
  ]
    ? K extends keyof NonNullable<T>
      ? readonly [K, ...ValidPath<NonNullable<T>[K], Rest>]
      : never
    : readonly [];

type ValueAt<T, P extends readonly PropertyKey[]> =
  P extends readonly [
    infer K extends PropertyKey,
    ...infer Rest extends PropertyKey[]
  ]
    ? K extends keyof NonNullable<T>
      ? ValueAt<NonNullable<T>[K], Rest> |
          (Extract<T, null | undefined> extends never
            ? never
            : undefined)
      : never
    : T;

function get<T, const P extends readonly PropertyKey[]>(
  obj: T,
  ...path: P & ValidPath<T, P>
): ValueAt<T, P> {
  let value: unknown = obj;

  for (const key of path) {
    value = (
      value as Record<PropertyKey, unknown> | null | undefined
    )?.[key];
  }

  return value as ValueAt<T, P>;
}
```

Пример:

```
interface User {
  profile?: {
    name: string;
    age: number;
  };
}

const user: User = {
  profile: {
    name: 'Alice',
    age: 25
  }
};

const name = get(user, 'profile', 'name');
// string | undefined

const age = get(user, 'profile', 'age');
// number | undefined

get(user, 'profile', 'invalid');
// Ошибка TypeScript
```

Как работает типизация:

- `ValidPath` проверяет существование каждого ключа на соответствующем уровне объекта.
- `ValueAt` рекурсивно вычисляет тип поля.
- `NonNullable` позволяет обращаться к свойствам потенциально отсутствующих вложенных объектов.
- Если промежуточное значение может быть `null` или `undefined`, итоговый тип включает `undefined`.
- Оператор `?.` предотвращает ошибку при обращении через отсутствующее промежуточное значение.

`const` type parameters доступны начиная с TypeScript 5.0.

Ограничения: сложные рекурсивные структуры и очень глубокие пути могут создавать большую нагрузку на систему типов. Проверка типов действует только при компиляции, а не во время выполнения.

# Как реализовать LRU cache с заданной ёмкостью?

LRU (Least Recently Used) - кэш, который при переполнении удаляет элемент, использовавшийся наиболее давно.

В JavaScript его удобно реализовать через `Map`, сохраняющий порядок вставки ключей.

```
class LRUCache {
  constructor(capacity) {
    if (!Number.isInteger(capacity) || capacity < 1) {
      throw new RangeError('Invalid capacity');
    }

    this.capacity = capacity;
    this.cache = new Map();
  }

  get(key) {
    if (!this.cache.has(key)) {
      return undefined;
    }

    const value = this.cache.get(key);

    this.cache.delete(key);
    this.cache.set(key, value);

    return value;
  }

  set(key, value) {
    if (this.cache.has(key)) {
      this.cache.delete(key);
    }

    this.cache.set(key, value);

    if (this.cache.size > this.capacity) {
      const oldestKey = this.cache.keys().next().value;
      this.cache.delete(oldestKey);
    }

    return this;
  }
}
```

Пример:

```
const cache = new LRUCache(2);

cache.set('a', 1);
cache.set('b', 2);

cache.get('a'); // 1 - обновили использование

cache.set('c', 3);

cache.get('b'); // undefined - удалён
cache.get('a'); // 1
```

Принцип работы:

- Новые элементы добавляются в конец `Map`.
- При чтении элемент удаляется и вставляется заново, становясь самым недавно использованным.
- При переполнении удаляется первый элемент `Map`.

Средняя сложность `get` и `set` - `O(1)`.

Ограничение: `get()` возвращает `undefined` как для отсутствующего ключа, так и для сохранённого значения `undefined`. При необходимости их различают через `has()`.

# Как реализовать функцию поиска первого неповторяющегося символа?

Нужно подсчитать частоту каждого символа, затем найти первый символ с частотой `1`.

```
function firstUniqueChar(str) {
  const counts = new Map();

  for (const char of str) {
    counts.set(char, (counts.get(char) ?? 0) + 1);
  }

  for (const char of str) {
    if (counts.get(char) === 1) {
      return char;
    }
  }

  return null;
}
```

Пример:

```
firstUniqueChar('aabbcde'); // 'c'
firstUniqueChar('aabb');    // null
```

Почему два прохода:

1. Первый определяет количество повторений каждого символа.
2. Второй сохраняет исходный порядок и возвращает первый уникальный.

Сложность - `O(n)` по времени и `O(k)` по памяти, где `k` - количество различных символов.

`for...of` перебирает Unicode code points, поэтому корректно обрабатывает символы за пределами BMP, представленные двумя UTF-16 code units. Однако один визуальный символ может состоять из нескольких code points. Для сравнения графем потребуется `Intl.Segmenter`.

# Как реализовать сортировку массива объектов по нескольким полям?

Нужно написать компаратор, который последовательно сравнивает поля по приоритету.

```
function sortBy(items, rules) {
  function compare(a, b) {
    if (a == null) return b == null ? 0 : 1;
    if (b == null) return -1;

    if (typeof a === 'string' && typeof b === 'string') {
      return a.localeCompare(b, 'ru');
    }

    return a < b ? -1 : a > b ? 1 : 0;
  }

  return [...items].sort((a, b) => {
    for (const { key, order = 'asc' } of rules) {
      const result = compare(a[key], b[key]);

      if (result !== 0) {
        return order === 'desc' ? -result : result;
      }
    }

    return 0;
  });
}
```

Пример:

```
const users = [
  { name: 'Bob', age: 25 },
  { name: 'Alice', age: 20 },
  { name: 'Charlie', age: 25 }
];

const sorted = sortBy(users, [
  { key: 'age', order: 'asc' },
  { key: 'name', order: 'asc' }
]);

// Alice (20), Bob (25), Charlie (25)
```

Механизм:

1. Сравнивается первое поле.
2. Если значения различаются, результат сразу возвращается.
3. Если равны, сравнивается следующее поле.
4. Если все поля равны, возвращается `0`.

`localeCompare` обеспечивает локализованное сравнение строк. Для чисел используются операторы сравнения.

Начиная с ECMAScript 2019, `Array.prototype.sort()` гарантирует стабильную сортировку.

Копирование через `[...items]` позволяет не изменять исходный массив.

Реализация предполагает сопоставимые типы значений. Для `NaN`, смешанных типов и сложных правил обработки `null` нужна дополнительная политика сравнения.

# Как реализовать подсчёт количества одновременно выполняющихся промисов?

Нужно отслеживать жизненный цикл асинхронных операций: увеличивать счётчик перед запуском и уменьшать после завершения.

```
function createPromiseTracker() {
  let active = 0;
  let peak = 0;

  async function run(task) {
    active++;
    peak = Math.max(peak, active);

    try {
      return await task();
    } finally {
      active--;
    }
  }

  return {
    run,

    get active() {
      return active;
    },

    get peak() {
      return peak;
    }
  };
}
```

Пример:

```
const tracker = createPromiseTracker();

const requests = [
  tracker.run(() => fetch('/api/1')),
  tracker.run(() => fetch('/api/2')),
  tracker.run(() => fetch('/api/3'))
];

console.log(tracker.active); // 3

await Promise.allSettled(requests);

console.log(tracker.active); // 0
console.log(tracker.peak);   // 3
```

Зачем нужен `finally`: счётчик должен уменьшаться независимо от того, выполнился промис успешно или завершился ошибкой.

`active` показывает текущее количество отслеживаемых незавершённых операций, а `peak` - максимальное количество за всё время.

Важно: у произвольного промиса нет публичного API для получения его состояния. Поэтому отслеживать нужно операции, которые запускаются через собственную обёртку.

# Как реализовать отменяемую задержку `sleep(ms, signal)`?

Нужно создать промис, разрешающийся через `setTimeout`, и подписаться на событие `abort` переданного `AbortSignal`.

```
function sleep(ms, signal) {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(
        signal.reason ??
        new DOMException('Aborted', 'AbortError')
      );
      return;
    }

    const timer = setTimeout(() => {
      signal?.removeEventListener('abort', onAbort);
      resolve();
    }, ms);

    function onAbort() {
      clearTimeout(timer);

      signal?.removeEventListener('abort', onAbort);

      reject(
        signal.reason ??
        new DOMException('Aborted', 'AbortError')
      );
    }

    signal?.addEventListener('abort', onAbort, {
      once: true
    });
  });
}
```

Пример:

```
const controller = new AbortController();

const delay = sleep(5000, controller.signal);

controller.abort();

try {
  await delay;
} catch (error) {
  console.log(error.name); // AbortError
}
```

Принцип работы:

- Если сигнал уже отменён, промис сразу отклоняется.
- Иначе создаётся таймер.
- Если таймер срабатывает первым, промис разрешается.
- Если раньше поступает `abort`, таймер удаляется, а промис отклоняется.
- Обработчик события очищается после завершения.

Удаление таймера позволяет избежать лишнего запланированного вызова. Удаление обработчика предотвращает ненужное удержание ссылок.

Отмена задержки не может автоматически отменить другие асинхронные операции, если они самостоятельно не поддерживают `AbortSignal`.

# Как реализовать поиск минимального пути по простому графу?

Для невзвешенного графа минимальный путь по количеству рёбер находится алгоритмом BFS (Breadth-First Search) - поиском в ширину.

```
function shortestPath(graph, start, end) {
  const queue = [start];
  const parent = new Map([[start, null]]);

  for (let head = 0; head < queue.length; head++) {
    const node = queue[head];

    if (node === end) {
      const path = [];

      for (
        let current = end;
        current !== null;
        current = parent.get(current)
      ) {
        path.push(current);
      }

      return path.reverse();
    }

    for (const neighbor of graph.get(node) ?? []) {
      if (!parent.has(neighbor)) {
        parent.set(neighbor, node);
        queue.push(neighbor);
      }
    }
  }

  return null;
}
```

Пример:

```
const graph = new Map([
  ['A', ['B', 'C']],
  ['B', ['A', 'D']],
  ['C', ['A', 'D']],
  ['D', ['B', 'C', 'E']],
  ['E', ['D']]
]);

shortestPath(graph, 'A', 'E');
// ['A', 'B', 'D', 'E']
```

Как работает BFS:

1. Начальная вершина помещается в очередь.
2. Из очереди извлекается очередная вершина.
3. Все ещё не посещённые соседи добавляются в очередь.
4. Для каждого соседа запоминается вершина, из которой он был достигнут.
5. Когда находится целевая вершина, путь восстанавливается по `parent` в обратном порядке.

BFS обходит вершины по возрастанию расстояния от начальной вершины, поэтому первый найденный путь до цели будет кратчайшим по количеству рёбер.

`Map` одновременно хранит родителей и позволяет определять посещённые вершины. Индекс `head` используется вместо `queue.shift()`, чтобы избежать затрат на сдвиг элементов массива.

Сложность:

- Время - `O(V + E)`.
- Память - `O(V)`.

Где `V` - количество вершин, `E` - количество рёбер.

Важно: BFS подходит для невзвешенных графов или графов с одинаковым весом всех рёбер. Если рёбра имеют разные неотрицательные веса, обычно используют алгоритм Дейкстры. Для графов с отрицательными весами может понадобиться алгоритм Беллмана - Форда.