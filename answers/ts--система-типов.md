# Чем TypeScript отличается от JavaScript во время выполнения?

TypeScript - это JavaScript с системой статической типизации, которая проверяет код до выполнения.

Основные отличия:

- TypeScript проверяет совместимость типов на этапе разработки или компиляции.
- При обычной компиляции типы удаляются, а результатом становится JavaScript.
- Типы не существуют во время выполнения и не обеспечивают runtime-валидацию.
- TypeScript поддерживает дополнительные конструкции, некоторые из которых создают JavaScript-код, например `enum`.

Важно: TypeScript не предотвращает ошибки типов во время выполнения, если фактические данные не соответствуют ожидаемым.

Например, объявление `const age: number = 25` не создаёт runtime-проверку того, что `age` является числом.

# Что такое structural typing?

Structural typing (структурная типизация) - система, в которой совместимость типов определяется их структурой, а не именами.

Два типа совместимы, если один содержит необходимые свойства другого с совместимыми типами.

```
type User = {
  name: string;
};

type Admin = {
  name: string;
  permissions: string[];
};

const admin: Admin = {
  name: "Alex",
  permissions: ["read", "write"],
};

const user: User = admin; // OK
```

`Admin` совместим с `User`, поскольку содержит обязательное свойство `name`.

Особенности:

- Дополнительные свойства обычно не нарушают совместимость.
- Для свежих объектных литералов действуют дополнительные проверки неизвестных свойств (excess property checks).
- Совместимость проверяется рекурсивно, включая вложенные объекты и функции.
- TypeScript не требует явного наследования или реализации интерфейса.

Это отличается от nominal typing, где совместимость определяется объявленной принадлежностью к типу.

# Чем `type` отличается от `interface`?

Оба позволяют описывать типы объектов, но имеют разные возможности.

`interface`:

- Предназначен преимущественно для описания объектных структур и контрактов классов.
- Поддерживает наследование через `extends`.
- Поддерживает declaration merging - объявления с одинаковым именем могут объединяться.

`type`:

- Позволяет создавать псевдонимы любых типов: примитивов, объектов, функций, union, intersection, кортежей.
- Поддерживает композицию через `&` и `|`.
- Не поддерживает объединение повторных объявлений с одинаковым именем.

```
interface User {
  id: number;
}

interface User {
  name: string;
}

// User содержит id и name

type Status = "loading" | "success" | "error";

type Admin = User & {
  permissions: string[];
};
```

Практически: `interface` удобен для расширяемых объектных контрактов, `type` - для union, вычисляемых типов и сложных композиций. Для простых объектов оба варианта подходят.

# Что такое type inference и когда лучше явная аннотация?

Type inference (вывод типов) - способность TypeScript автоматически определять тип выражения на основании его значения, контекста использования и операций.

```
const age = 25; // тип 25
let count = 10; // тип number

const numbers = [1, 2, 3]; // number[]
```

TypeScript также выводит типы возвращаемых значений функций, generic-параметров и callback-аргументов.

Явная аннотация полезна, когда:

- Нужно зафиксировать публичный контракт функции или API.
- Требуется ограничить допустимые значения переменной.
- Тип невозможно корректно вывести из контекста.
- Нужно контролировать тип возвращаемого значения и обнаруживать случайное изменение контракта.

```
function getUser(id: number): Promise<User> {
  return fetchUser(id);
}
```

Для локальных переменных с очевидным типом аннотации обычно избыточны.

# Чем `any`, `unknown`, `never` и `void` отличаются?

- `any` - отключает большинство проверок типов для значения. Позволяет обращаться к любым свойствам и вызывать любые методы, но снижает безопасность типизации.
- `unknown` - может содержать любое значение, однако перед использованием требует проверки или уточнения типа.
- `never` - обозначает невозможное значение. Используется для недостижимых состояний и функций, которые никогда не завершаются обычным возвратом.
- `void` - обозначает отсутствие значимого возвращаемого результата. Обычно используется для функций, результат которых не предполагается использовать.

```
let a: any = 10;
a.foo.bar(); // Компилятор допускает

let b: unknown = 10;
// b.toFixed(); // Ошибка

if (typeof b === "number") {
  b.toFixed(); // OK
}

function fail(): never {
  throw new Error("Error");
}

function log(): void {
  console.log("Hello");
}
```

Ключевое различие: `unknown` сохраняет безопасность типов, `any` обходит её. `never` означает невозможность значения, а `void` - отсутствие значимого результата.

# Когда TypeScript выводит тип `never`?

TypeScript выводит `never`, когда определяет, что значение невозможно или выполнение не может продолжиться обычным образом.

Основные случаи:

- После исключения всех возможных вариантов union.
- Для недостижимых веток управления.
- Для функций, которые всегда выбрасывают исключение или гарантированно выполняются бесконечно.
- При пересечении несовместимых типов, когда допустимых значений не остаётся.
- В conditional types, когда результатом выбранной ветки является `never`.

```
function process(value: string | number) {
  if (typeof value === "string") {
    return value.toUpperCase();
  }

  if (typeof value === "number") {
    return value.toFixed();
  }

  const impossible: never = value;
}
```

После обеих проверок допустимых типов больше не осталось.

Это используется для exhaustive checking - проверки, что обработаны все возможные варианты union.

# Чем union отличается от intersection?

Union (`|`) означает, что значение может соответствовать одному из нескольких типов.

Intersection (`&`) требует одновременного соответствия всем объединённым ограничениям.

```
type Status = "success" | "error";

type User = {
  id: number;
};

type Admin = {
  permissions: string[];
};

type AdminUser = User & Admin;
```

`Status` допускает два значения.

`AdminUser` требует и `id`, и `permissions`.

Особенности:

- При работе с union напрямую доступны только операции, безопасные для всех его вариантов.
- Intersection объединяет требования типов, а не просто копирует свойства.
- Пересечение несовместимых типов может дать `never`, например `string & number`.

Union подходит для альтернативных состояний, intersection - для объединения совместимых контрактов.

# Что такое literal types?

Literal types (литеральные типы) - типы, ограниченные конкретными значениями, а не всеми значениями примитивного типа.

```
type Direction = "left" | "right";
type Answer = true;
type HttpCode = 200 | 404 | 500;
```

Например, переменная типа `"left"` может содержать только строку `"left"`.

Литеральные типы часто объединяют через union, чтобы описывать ограниченный набор допустимых значений.

```
function move(direction: Direction) {
  // ...
}

move("left"); // OK
move("up");   // Ошибка
```

TypeScript может расширять литеральные типы до базовых (`"hello"` до `string`). Это называется type widening.

`const`, `as const` и контекстная типизация влияют на сохранение литеральных типов.

# Как работают discriminated unions?

Discriminated union - объединение объектных типов, имеющих общее поле-дискриминатор с различными литеральными значениями.

По значению дискриминатора TypeScript определяет конкретный вариант объекта.

```
type Result =
  | { status: "success"; data: string }
  | { status: "error"; message: string };

function handle(result: Result) {
  if (result.status === "success") {
    console.log(result.data);
  } else {
    console.log(result.message);
  }
}
```

Когда `status === "success"`, TypeScript знает, что объект содержит `data`.

Преимущества:

- Безопасный доступ к свойствам конкретного варианта.
- Удобная обработка состояний через `switch`.
- Проверка полноты обработки вариантов через `never`.
- Невозможность представить некорректные комбинации свойств, если типы определены правильно.

Часто применяется для API-результатов, состояний интерфейса и событий.

# Что такое type narrowing и control-flow analysis?

Type narrowing (сужение типа) - уточнение типа значения на основании проверок и условий выполнения.

TypeScript поддерживает сужение через:

- `typeof` - проверка примитивных типов.
- `instanceof` - проверка принадлежности к классу через цепочку прототипов.
- `in` - проверка наличия свойства.
- `Array.isArray()` - проверка массива.
- Сравнение с конкретными значениями.
- Пользовательские type guards.

Control-flow analysis - анализ потока управления программой, позволяющий TypeScript учитывать условия, присваивания, возвраты и недостижимые ветки.

```
function print(value: string | null) {
  if (value === null) {
    return;
  }

  console.log(value.toUpperCase());
}
```

После `return` TypeScript понимает, что `value` уже не может быть `null`.

Сужение действует в зависимости от точки программы и может изменяться после присваивания. При работе с изменяемыми данными TypeScript также учитывает, где уточнение типа больше нельзя гарантировать.

# Как писать пользовательские type guards?

Пользовательский type guard - функция, которая проверяет значение во время выполнения и сообщает TypeScript, к какому типу его можно отнести.

Для этого используется предикат `value is Type`.

```
type User = {
  id: number;
  name: string;
};

function isUser(value: unknown): value is User {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  return (
    "id" in value &&
    typeof value.id === "number" &&
    "name" in value &&
    typeof value.name === "string"
  );
}

const data: unknown = JSON.parse('{"id":1,"name":"Alex"}');

if (isUser(data)) {
  console.log(data.name);
}
```

После успешной проверки TypeScript воспринимает `data` как `User`.

Важно: компилятор не доказывает, что реализация type guard действительно проверяет весь контракт. Некорректный предикат создаёт ложное ощущение безопасности.

Также существуют assertion functions с синтаксисом `asserts value is Type`. Они уточняют тип после успешного завершения функции, а при нарушении условия обычно выбрасывают исключение.

# Что означает оператор `satisfies`?

`satisfies` проверяет, соответствует ли выражение указанному типу, не заменяя его результирующий тип на этот тип.

Оператор появился в TypeScript 4.9.

```
type Config = {
  mode: "development" | "production";
  port: number;
};

const config = {
  mode: "development",
  port: 3000,
} satisfies Config;
```

TypeScript проверит, что объект соответствует `Config`, и сохранит более конкретную информацию о его свойствах, полученную при выводе типов.

Различия:

- `: Config` - явно задаёт переменной тип `Config`.
- `as Config` - утверждает совместимость типа, потенциально обходя некоторые проверки.
- `satisfies Config` - проверяет совместимость, сохраняя выводимый тип выражения.

При этом `satisfies` участвует в контекстной типизации, поэтому тоже может влиять на вывод типов.

Полезен для конфигураций, словарей, таблиц маршрутов и объектов с фиксированным набором ключей.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.typescriptlang.org\&sz=32)

TypeScript 4.9



# В чём различие `as const` и `const` переменной?

`const` запрещает повторное присваивание переменной, но не делает содержимое объекта неизменяемым.

`as const` - const assertion, которая влияет на вывод типов:

- Сохраняет литеральные типы.
- Делает свойства объектных литералов `readonly`.
- Преобразует литералы массивов в `readonly`-кортежи.

```
const user = {
  role: "admin",
};

// user.role: string
user.role = "guest"; // OK

const admin = {
  role: "admin",
} as const;

// admin.role: "admin"
// admin.role = "guest"; // Ошибка
```

Для массивов:

```
const values = [1, 2] as const;
// readonly [1, 2]
```

Важно: `as const` действует только на уровне типов. Он не вызывает `Object.freeze()` и не обеспечивает реальную глубокую неизменяемость объектов во время выполнения.

# Как работают `keyof`, `typeof` в типах и indexed access types?

Эти операторы позволяют получать новые типы из существующих структур.

`keyof` возвращает union ключей объектного типа.

```
type User = {
  id: number;
  name: string;
};

type UserKey = keyof User;
// "id" | "name"
```

`typeof` в типовом контексте получает тип переменной или свойства, не выполняя runtime-проверку.

```
const config = {
  port: 3000,
  debug: true,
};

type Config = typeof config;
// { port: number; debug: boolean }
```

Indexed access types позволяют получить тип свойства по его ключу.

```
type UserId = User["id"]; // number

type UserValue = User[keyof User];
// string | number
```

Операторы можно комбинировать для создания типов, автоматически зависящих от исходных объектов.

# Что делают `Partial`, `Required`, `Readonly`, `Pick`, `Omit` и `Record`?

Это встроенные utility types, предназначенные для преобразования и создания типов.

- `Partial<T>` - делает все свойства `T` необязательными.
- `Required<T>` - делает все свойства обязательными.
- `Readonly<T>` - запрещает присваивание свойствам на уровне типизации.
- `Pick<T, K>` - выбирает указанные свойства из `T`.
- `Omit<T, K>` - исключает указанные свойства из `T`.
- `Record<K, V>` - создаёт объектный тип с ключами `K` и значениями `V`.

```
type User = {
  id: number;
  name: string;
  age?: number;
};

type UpdateUser = Partial<User>;

type FullUser = Required<User>;

type ImmutableUser = Readonly<User>;

type UserPreview = Pick<User, "id" | "name">;

type UserWithoutId = Omit<User, "id">;

type UserMap = Record<string, User>;
```

`Partial`, `Required` и `Readonly` преобразуют свойства на верхнем уровне. Например, `Readonly<T>` не делает автоматически неизменяемыми все вложенные объекты.

Все эти типы действуют только при статической проверке.

# Как работают `Exclude`, `Extract`, `NonNullable`, `ReturnType` и `Parameters`?

Это utility types для фильтрации union и извлечения информации из других типов.

- `Exclude<T, U>` - исключает из `T` варианты, совместимые с `U`.
- `Extract<T, U>` - оставляет из `T` варианты, совместимые с `U`.
- `NonNullable<T>` - исключает `null` и `undefined`.
- `ReturnType<F>` - получает тип возвращаемого значения функции.
- `Parameters<F>` - получает типы параметров функции в виде кортежа.

```
type A = Exclude<"a" | "b" | "c", "a">;
// "b" | "c"

type B = Extract<string | number | boolean, number | boolean>;
// number | boolean

type C = NonNullable<string | null | undefined>;
// string

function getUser(id: number): string {
  return String(id);
}

type D = ReturnType<typeof getUser>;
// string

type E = Parameters<typeof getUser>;
// [id: number]
```

`Exclude` и `Extract` основаны на распределяемых conditional types и проверяют совместимость типов, а не просто совпадение их названий.

Для перегруженных функций `ReturnType` и `Parameters` обычно используют последнюю сигнатуру перегрузки.

# Как типизировать объект с динамическими ключами?

Если имена свойств заранее неизвестны, применяют index signature или `Record`.

```
type Dictionary = {
  [key: string]: number;
};

const scores: Dictionary = {
  alice: 100,
  bob: 85,
};
```

Эквивалентный вариант:

```
type Dictionary = Record<string, number>;
```

Если набор ключей известен, лучше ограничить его union:

```
type Role = "admin" | "user";

type Permissions = Record<Role, boolean>;
```

В этом случае оба свойства обязательны.

Если значения могут отсутствовать:

```
type Permissions = Partial<Record<Role, boolean>>;
```

Особенности:

- Index signature допускает ключи `string`, `number` или `symbol`.
- `Record<string, T>` не гарантирует существование значения для произвольного строкового ключа.
- `noUncheckedIndexedAccess` позволяет учитывать возможное отсутствие значения при обращении по динамическому ключу.
- Для действительно динамических коллекций также подходит `Map<K, V>`, особенно когда ключи не ограничиваются строками и символами.

# Когда использовать `enum`, а когда union литералов?

Оба подхода позволяют ограничить набор допустимых значений, но отличаются поведением во время выполнения.

`enum` - конструкция TypeScript, которая обычно создаёт JavaScript-объект.

```
enum Status {
  Pending = "pending",
  Success = "success",
  Error = "error",
}
```

Union литералов существует только на уровне типов и полностью удаляется при компиляции.

```
type Status = "pending" | "success" | "error";
```

Основные различия:

- `enum` создаёт runtime-представление, обычный union - нет.
- `enum` позволяет обращаться к значениям через `Status.Pending`.
- Union проще объединять с другими типами и использовать в conditional types.
- Union строковых литералов удобен для JSON, API-контрактов и состояний приложения.
- Строковые `enum` имеют более строгие правила совместимости с обычными строковыми литералами.

Практически: для большинства frontend-сценариев удобнее union литералов.

`enum` имеет смысл, когда необходим именованный runtime-объект или библиотека уже использует перечисления.

`const enum` может встраивать значения непосредственно в код, но имеет ограничения совместимости с отдельной транспиляцией файлов и некоторыми сборщиками.

# Как работают `strictNullChecks`, `noUncheckedIndexedAccess` и `exactOptionalPropertyTypes`?

Эти настройки `tsconfig.json` усиливают проверки потенциально отсутствующих значений.

`strictNullChecks` делает `null` и `undefined` отдельными типами.

```
let name: string = "Alex";

// Ошибка при strictNullChecks
// name = null;

let value: string | null = null;
```

Без этой настройки `null` и `undefined` допускаются во многих местах, где это может привести к runtime-ошибкам.

`noUncheckedIndexedAccess` добавляет `undefined` к типам значений, получаемых через индекс, если существование элемента не гарантировано.

```
const users: string[] = ["Alex"];

const user = users[10];
// string | undefined
```

Это особенно полезно для массивов и словарей.

`exactOptionalPropertyTypes` различает отсутствие свойства и присутствие свойства со значением `undefined`.

```
type User = {
  name?: string;
};

const a: User = {}; // OK

// Ошибка при exactOptionalPropertyTypes
const b: User = { name: undefined };
```

Чтобы разрешить явный `undefined`, нужно указать:

```
type User = {
  name?: string | undefined;
};
```

При чтении `name` тип всё равно будет `string | undefined`.

`strictNullChecks` входит в набор `strict`, а остальные две настройки включаются отдельно.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.typescriptlang.org\&sz=32)

typescriptlang.org



# Чем `interface extends` отличается от пересечения типов?

Оба механизма позволяют комбинировать объектные типы, но отличаются обработкой конфликтов.

`interface extends` проверяет, что расширяемый интерфейс совместим с базовым.

```
interface Base {
  id: number;
}

interface User extends Base {
  name: string;
}
```

Если переопределить свойство несовместимым типом, TypeScript сообщит об ошибке непосредственно при объявлении интерфейса.

Intersection (`&`) объединяет требования типов.

```
type A = {
  id: string;
};

type B = {
  id: number;
};

type C = A & B;
// Свойство id имеет тип never
```

Пересечение не всегда сразу сообщает об ошибке: оно может создать тип с невозможными для заполнения свойствами.

Дополнительно:

- `interface extends` требует статически определяемую объектную структуру с известными свойствами.
- Intersection можно применять к объектам, union и другим типовым выражениям.
- Интерфейсы поддерживают declaration merging, псевдонимы типов - нет.

Практически: `extends` удобен для явного расширения контрактов с ранним обнаружением конфликтов. Intersection - для композиции типов, когда все ограничения должны выполняться одновременно.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.typescriptlang.org\&sz=32)

Object Types



# Как избежать небезопасных type assertions?

Type assertion (`as Type`) сообщает компилятору, как интерпретировать значение, но не проверяет его во время выполнения.

```
const user = data as User;
```

Если `data` не соответствует `User`, TypeScript не обнаружит проблему.

Безопасные подходы:

- Использовать type inference вместо принудительного указания типа.
- Применять type narrowing через `typeof`, `in`, `instanceof` и другие проверки.
- Использовать пользовательские type guards.
- Проверять внешние данные через runtime-валидацию.
- Применять `satisfies` вместо assertion, если нужно проверить соответствие выражения контракту.
- Использовать `unknown` вместо `any` для недоверенных данных.

```
function getName(value: unknown): string {
  if (
    typeof value === "object" &&
    value !== null &&
    "name" in value &&
    typeof value.name === "string"
  ) {
    return value.name;
  }

  throw new Error("Invalid value");
}
```

Также следует осторожно использовать:

- `as unknown as T` - двойное утверждение, позволяющее обойти проверки совместимости.
- `!` - non-null assertion, который убирает `null` и `undefined` из типа без runtime-проверки.

Главный принцип: утверждения типов допустимы, когда разработчик действительно располагает гарантией, которую компилятор не может вывести. Они не должны заменять проверку недоверенных данных.

# Что такое generic и как задавать ограничения `extends`?

Generic (обобщённый тип) - механизм параметризации типов, позволяющий создавать переиспользуемые функции, классы и структуры с сохранением информации о конкретных типах.

```
function identity<T>(value: T): T {
  return value;
}

const a = identity(10);      // number
const b = identity("hello"); // string
```

`T` - параметр типа, который TypeScript обычно выводит из переданных аргументов.

`extends` в generic задаёт ограничение: переданный тип должен соответствовать указанному контракту.

```
function getLength<T extends { length: number }>(
  value: T
): number {
  return value.length;
}

getLength("hello"); // OK
getLength([1, 2]);  // OK
getLength(123);     // Ошибка
```

Ограничение гарантирует наличие `length`, но сохраняет информацию о конкретном типе `T`.

Generics полезны, когда нужно выразить связь между типами аргументов, возвращаемых значений или свойств.

Если такая связь отсутствует, обычный конкретный тип или union часто проще.

# Как вывести тип свойства через `T[K]`?

`T[K]` - indexed access type, который получает тип свойства `K` из типа `T`.

В generic-функциях обычно используется ограничение `K extends keyof T`, гарантирующее, что ключ существует в описании типа.

```
function getProperty<
  T,
  K extends keyof T
>(obj: T, key: K): T[K] {
  return obj[key];
}
```

Пример:

```
const user = {
  id: 1,
  name: "Alex",
  active: true,
};

const id = getProperty(user, "id");
// number

const name = getProperty(user, "name");
// string

getProperty(user, "age"); // Ошибка
```

TypeScript сохраняет зависимость между выбранным ключом и возвращаемым значением.

Если `K` представляет union ключей, результат `T[K]` также может быть union соответствующих типов свойств.

Практическая ценность: типобезопасные функции чтения свойств, обновления объектов, работы с конфигурациями и создания универсальных утилит.

# Как работают conditional types?

Conditional types (условные типы) позволяют выбирать один из двух типов в зависимости от совместимости типов.

Синтаксис:

```
type Result<T> = T extends U ? X : Y;
```

Если `T` совместим с `U`, результатом будет `X`, иначе `Y`.

```
type IsString<T> =
  T extends string ? true : false;

type A = IsString<string>; // true
type B = IsString<number>; // false
```

Условные типы позволяют создавать типы, которые адаптируются к переданным параметрам.

```
type Unwrap<T> =
  T extends Promise<infer R> ? R : T;

type A = Unwrap<Promise<number>>;
// number

type B = Unwrap<string>;
// string
```

Особенности:

- Выполняются на уровне системы типов, а не во время работы JavaScript.
- Могут быть вложенными и рекурсивными.
- Поддерживают `infer` для извлечения частей типа.
- При определённых условиях распределяются по union.

Используются для utility types, преобразования API-контрактов и построения сложных generic-типов.

# Что означает `infer` в условных типах?

`infer` позволяет объявить переменную типа и вывести её из структуры другого типа внутри conditional type.

```
type GetReturnType<T> =
  T extends (...args: never[]) => infer R
    ? R
    : never;
```

Если `T` соответствует функции, TypeScript извлекает её возвращаемый тип в `R`.

```
type Fn = () => string;

type Result = GetReturnType<Fn>;
// string
```

Другой пример - извлечение типа элемента массива:

```
type ElementType<T> =
  T extends (infer U)[] ? U : T;

type A = ElementType<number[]>;
// number

type B = ElementType<string>;
// string
```

`infer` не извлекает реальные значения. Он работает исключительно со структурой типов.

Типичный сценарий - получение типов элементов массивов, параметров функций, возвращаемых значений и содержимого `Promise`.

# Что такое mapped types и modifiers `+/-readonly` и `+/-?`?

Mapped types (отображаемые типы) позволяют создавать новый объектный тип, перебирая ключи другого типа.

```
type Optional<T> = {
  [K in keyof T]?: T[K];
};
```

Для каждого свойства исходного типа создаётся соответствующее свойство нового типа.

Модификаторы управляют доступностью и обязательностью свойств:

- `+readonly` - добавляет `readonly`.
- `-readonly` - удаляет `readonly`.
- `+?` - делает свойство необязательным.
- `-?` - делает свойство обязательным.

Знак `+` можно опускать.

```
type Mutable<T> = {
  -readonly [K in keyof T]: T[K];
};

type RequiredProps<T> = {
  [K in keyof T]-?: T[K];
};
```

Пример:

```
type User = {
  readonly id: number;
  name?: string;
};

type EditableUser = Mutable<User>;
// id больше не readonly

type FullUser = RequiredProps<User>;
// name обязательно
```

Mapped types также поддерживают переименование и фильтрацию ключей через `as`.

```
type Getters<T> = {
  [K in keyof T as `get${Capitalize<string & K>}`]:
    () => T[K];
};
```

Это основа многих встроенных utility types, включая `Partial`, `Required`, `Readonly` и `Pick`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.typescriptlang.org\&sz=32)

Mapped Types



# Как устроены template literal types?

Template literal types позволяют создавать строковые типы из литералов и других типов, используя синтаксис шаблонных строк.

```
type Event = "click" | "focus";

type Handler = `on${Capitalize<Event>}`;
// "onClick" | "onFocus"
```

Если внутри шаблона используется union, TypeScript создаёт все допустимые комбинации.

```
type Size = "sm" | "lg";
type Color = "red" | "blue";

type ClassName = `${Size}-${Color}`;

// "sm-red" | "sm-blue"
// | "lg-red" | "lg-blue"
```

Встроенные операции со строковыми типами:

- `Uppercase<T>` - верхний регистр.
- `Lowercase<T>` - нижний регистр.
- `Capitalize<T>` - заглавная первая буква.
- `Uncapitalize<T>` - строчная первая буква.

Template literal types можно комбинировать с `infer` для разбора строковых шаблонов.

Основные применения - типизация событий, маршрутов, CSS-классов, именования методов и строковых API-контрактов.

Ограничение: большое количество комбинаций union может заметно усложнять типы и увеличивать нагрузку на компилятор.

# Что означает распределение conditional types по union?

Distributive conditional types - условные типы, которые автоматически применяются к каждому элементу union по отдельности.

Распределение происходит, когда проверяемая сторона `extends` представляет собой непосредственно параметр типа.

```
type ToArray<T> = T extends unknown ? T[] : never;

type Result = ToArray<string | number>;

// string[] | number[]
```

TypeScript фактически вычисляет:

```
ToArray<string> | ToArray<number>
```

Это поведение используется во встроенных `Exclude` и `Extract`.

Например:

```
type OnlyStrings<T> =
  T extends string ? T : never;

type Result = OnlyStrings<string | number | boolean>;
// string
```

`never` исчезает при объединении с другими типами через union.

Как отключить распределение: заключить проверяемые типы в кортежи.

```
type ToArray<T> =
  [T] extends [unknown] ? T[] : never;

type Result = ToArray<string | number>;
// (string | number)[]
```

Теперь условие проверяет union целиком, а не каждый вариант отдельно.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.typescriptlang.org\&sz=32)

Conditional Types



# Как типизировать перегруженную функцию?

Перегрузка функций (function overloads) позволяет объявить несколько вариантов вызова одной функции с разными типами параметров и возвращаемых значений.

Сначала объявляются публичные сигнатуры, затем одна реализация.

```
function format(value: string): string;
function format(value: number): string;

function format(value: string | number): string {
  if (typeof value === "number") {
    return value.toFixed(2);
  }

  return value.trim();
}
```

При вызове TypeScript выбирает подходящую сигнатуру перегрузки.

Особенности:

- Все overload signatures относятся к одной реализации.
- Сигнатура реализации должна быть совместима со всеми перегрузками.
- Внешний код видит только объявленные overload signatures.
- Сигнатура реализации сама по себе не добавляет допустимый вариант вызова.

Перегрузки особенно полезны, когда возвращаемый тип зависит от переданных аргументов.

# Чем overload signatures отличаются от union-аргумента?

Union-аргумент позволяет функции принимать несколько типов через одну сигнатуру.

```
function format(value: string | number): string {
  return String(value);
}
```

Этот подход проще, если все варианты аргументов обрабатываются с одинаковым типом результата.

Overload signatures позволяют выразить разные контракты вызова, особенно когда возвращаемый тип зависит от аргументов.

```
function parse(value: string): string[];
function parse(value: number): number[];

function parse(
  value: string | number
): string[] | number[] {
  return typeof value === "string"
    ? value.split(",")
    : [value];
}

const a = parse("a,b"); // string[]
const b = parse(10);    // number[]
```

При использовании union-аргумента возвращаемым типом обычно был бы `string[] | number[]`, даже если передан конкретный тип аргумента.

Важный нюанс: отдельные перегрузки для `string` и `number` не обязательно позволяют передать переменную типа `string | number`. Для этого может потребоваться дополнительная сигнатура.

Практически: когда возвращаемый тип не зависит от варианта аргумента, предпочтительнее union. Когда зависимость существует, подходят overloads или generics.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.typescriptlang.org\&sz=32)

More on Functions



# Как типизировать асинхронную функцию и её ошибки?

Асинхронная функция, объявленная с `async`, всегда возвращает `Promise`.

Тип возвращаемого значения описывается через `Promise<T>`.

```
async function getUser(id: number): Promise<User> {
  const response = await fetch(`/users/${id}`);

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  return response.json();
}
```

Здесь `Promise<User>` описывает успешное выполнение функции.

Важный нюанс: `response.json()` не гарантирует получение `User`. Его результат в стандартной DOM-типизации имеет тип `Promise<any>`, поэтому данные нужно отдельно валидировать.

Типизация ошибок:

TypeScript не поддерживает checked exceptions и не указывает тип отклонения `Promise` в `Promise<T>`.

```
try {
  await getUser(1);
} catch (error: unknown) {
  if (error instanceof Error) {
    console.error(error.message);
  }
}
```

При включённом `strict` переменная в `catch` по умолчанию имеет тип `unknown`.

Если ошибки должны быть частью явного контракта, можно использовать discriminated union:

```
type Result<T> =
  | { ok: true; data: T }
  | { ok: false; error: string };

async function loadUser(): Promise<Result<User>> {
  try {
    const user = await getValidatedUser();

    return { ok: true, data: user };
  } catch {
    return { ok: false, error: "Failed to load user" };
  }
}
```

Так вызывающий код может обрабатывать ожидаемые ошибки как обычные значения. При этом любые необработанные исключения по-прежнему могут отклонить `Promise`.

# Как описать типизированный EventEmitter?

Типизированный EventEmitter связывает имя события с типами аргументов, которые передаются его обработчикам.

Для этого удобно использовать объектную карту событий и generics.

```
type Events = {
  login: [userId: number];
  logout: [];
  message: [text: string, senderId: number];
};

class EventEmitter {
  private listeners: {
    [K in keyof Events]?: Array<(...args: Events[K]) => void>;
  } = {};

  on<K extends keyof Events>(
    event: K,
    callback: (...args: Events[K]) => void
  ): void {
    (this.listeners[event] ??= []).push(callback);
  }

  emit<K extends keyof Events>(
    event: K,
    ...args: Events[K]
  ): void {
    this.listeners[event]?.forEach(callback => callback(...args));
  }
}
```

Использование:

```
const emitter = new EventEmitter();

emitter.on("login", userId => {
  console.log(userId);
});

emitter.emit("login", 123);    // OK
emitter.emit("login", "123");  // Ошибка

emitter.emit("logout");       // OK
emitter.emit("logout", 123);  // Ошибка
```

Механизм основан на:

- `keyof Events` - ограничении допустимых названий событий.
- `Events[K]` - получении кортежа аргументов для конкретного события.
- Rest parameters - передаче этих аргументов в обработчик.
- Generics - сохранении связи между именем события и его payload.

В реальной реализации также обычно предусматривают `off`, `once`, очистку обработчиков и политику обработки исключений внутри listeners.

# Как типизировать API-ответы, если данные с сервера могут не соответствовать контракту?

Данные из API необходимо считать недоверенными, поскольку TypeScript не проверяет их фактическую структуру во время выполнения.

Недостаточно написать:

```
const user = await response.json() as User;
```

Это лишь утверждение типа. Если сервер вернёт некорректные данные, ошибка останется незамеченной.

Надёжный подход:

1. Получить ответ от сервера.
2. Проверить HTTP-статус.
3. Прочитать данные как `unknown`.
4. Проверить их структуру во время выполнения.
5. Использовать валидированный результат как типизированное значение.

Например, с Zod:

```
import { z } from "zod";

const UserSchema = z.object({
  id: z.number(),
  name: z.string(),
});

type User = z.infer<typeof UserSchema>;

async function getUser(): Promise<User> {
  const response = await fetch("/api/user");

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  const data: unknown = await response.json();

  return UserSchema.parse(data);
}
```

Если структура ответа не соответствует схеме, `parse()` выбросит ошибку валидации.

Ключевой принцип: типизация описывает ожидаемый контракт, а runtime-валидация подтверждает соответствие реальных данных этому контракту.

# Для чего нужны схемы runtime-валидации (Zod, Valibot) вместе с TypeScript?

TypeScript выполняет статическую проверку типов, но не проверяет значения, полученные во время выполнения.

Zod и Valibot позволяют описывать схемы и проверять реальные данные.

Пример с Zod:

```
import { z } from "zod";

const UserSchema = z.object({
  id: z.number(),
  email: z.email(),
});

type User = z.infer<typeof UserSchema>;
```

Здесь:

- `UserSchema` - runtime-схема.
- `z.infer<typeof UserSchema>` - TypeScript-тип, выведенный из схемы.
- `parse()` - проверяет данные и выбрасывает исключение при ошибке.
- `safeParse()` - возвращает результат с признаком успеха или ошибки.

```
const result = UserSchema.safeParse(data);

if (result.success) {
  console.log(result.data.email);
} else {
  console.error(result.error);
}
```

Valibot решает аналогичную задачу, используя другой API и модульный подход к построению схем.

Основные применения:

- Проверка ответов сервера.
- Валидация форм.
- Проверка переменных окружения.
- Обработка данных из `localStorage`.
- Проверка входящих сообщений и внешних интеграций.

Преимущество: схема может служить единым источником истины для runtime-проверок и статической типизации, уменьшая риск расхождения между ними.

Важно учитывать, что валидаторы проверяют только те ограничения, которые действительно описаны схемой.

# Как настроить `tsconfig`, `paths`, project references и `isolatedModules`?

`tsconfig.json` управляет проверкой типов, компиляцией, разрешением модулей и составом проекта.

Пример конфигурации для frontend-приложения, собираемого современным bundler:

```
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,
    "isolatedModules": true,
    "verbatimModuleSyntax": true,
    "noEmit": true,
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["src"]
}
```

Основные настройки:

- `target` - целевая версия JavaScript для генерируемого кода.
- `module` - формат модулей и связанные правила компиляции.
- `moduleResolution` - алгоритм поиска импортируемых модулей.
- `strict` - включает набор строгих проверок типов.
- `noEmit` - отключает генерацию файлов компилятором TypeScript.
- `verbatimModuleSyntax` - сохраняет импорты и экспорты значений и удаляет объявления, явно помеченные как типовые через `type`.

Для проектов, которые выполняются непосредственно в Node.js, обычно выбирают `module` и `moduleResolution` со значением `NodeNext`, а не `Bundler`.

`paths` задаёт псевдонимы путей для разрешения импортов.

```
import { getUser } from "@/api/users";
```

Важно: `paths` не переписывает пути в генерируемом JavaScript. Соответствующие псевдонимы должны поддерживаться сборщиком или runtime-окружением.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.typescriptlang.org\&sz=32)

typescriptlang.org



Project references позволяют разделять крупный TypeScript-проект на независимые подпроекты.

```
{
  "files": [],
  "references": [
    { "path": "./packages/core" },
    { "path": "./packages/ui" }
  ]
}
```

Обычно каждый используемый в качестве зависимости подпроект настраивается с `composite: true`.

Преимущества:

- Инкрементальная сборка.
- Разделение модулей и их зависимостей.
- Повторное использование сгенерированных деклараций типов.
- Уменьшение объёма повторных проверок при сборке.

Для сборки графа зависимостей применяется `tsc -b`.

`isolatedModules` предупреждает о конструкциях TypeScript, которые нельзя безопасно транспилировать по одному файлу без анализа всей программы.

Это важно при использовании Babel, SWC, esbuild и других инструментов, выполняющих пофайловую транспиляцию.

Сам `isolatedModules` не обеспечивает изолированную сборку и не заменяет полноценную проверку типов через `tsc`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.typescriptlang.org\&sz=32)

Project References+1



# Чем декларация `.d.ts` отличается от исполняемого кода?

`.d.ts` (declaration file) - файл, содержащий объявления типов и контрактов API без их реализации.

Он позволяет TypeScript понимать структуру JavaScript-кода, внешних библиотек и глобальных объектов.

```
// math.d.ts

export declare function sum(
  a: number,
  b: number
): number;
```

Реальная реализация может находиться в JavaScript:

```
// math.js

export function sum(a, b) {
  return a + b;
}
```

Основные различия:

- `.ts` может содержать исполняемый код и типы.
- `.d.ts` описывает типы и существующие API без исполняемой реализации.
- Декларации не создают функции и объекты во время выполнения.
- `.d.ts` используется компилятором, редакторами и инструментами анализа кода.
- TypeScript может генерировать декларации автоматически через `declaration: true`.

Важно: `declare` сообщает компилятору о существовании значения, но не создаёт его.

Если объявить функцию в `.d.ts`, не предоставив соответствующую runtime-реализацию, TypeScript может успешно проверить код, однако при выполнении произойдёт ошибка.

# Как типизировать стороннюю JavaScript-библиотеку без готовых типов?

Если JavaScript-библиотека не содержит собственных TypeScript-деклараций, для неё можно создать файл `.d.ts`.

Основные способы:

- Проверить наличие готового пакета `@types/...` в DefinitelyTyped.
- Создать собственную декларацию через `declare module`.
- Описать экспортируемые функции, объекты, классы и generic-контракты библиотеки.
- Для собственной JavaScript-библиотеки использовать JSDoc и `checkJs`, при необходимости генерируя декларации.

Пример для библиотеки `legacy-utils`:

```
// types/legacy-utils.d.ts

declare module "legacy-utils" {
  export function formatDate(
    date: Date,
    pattern: string
  ): string;

  export function generateId(): string;
}
```

После этого TypeScript сможет проверять вызовы:

```
import {
  formatDate,
  generateId
} from "legacy-utils";

const id = generateId();

const formatted = formatDate(
  new Date(),
  "YYYY-MM-DD"
);
```

Если декларация не обнаруживается, нужно проверить, входит ли `.d.ts` в проект, и соответствуют ли настройки поиска модулей структуре библиотеки.

Можно временно использовать:

```
declare module "legacy-utils";
```

Но такой вариант фактически превращает импорты библиотеки в `any` и отключает полноценную проверку их типов.

Практически: лучше описать хотя бы используемую часть API, чем полностью отказаться от типизации. При этом декларации должны соответствовать реальному поведению библиотеки, поскольку TypeScript не проверяет их достоверность во время выполнения.

Источники: [TypeScript Handbook](https://www.typescriptlang.org/docs/handbook/intro.html?utm_source=chatgpt.com), [TSConfig Reference](https://www.typescriptlang.org/tsconfig/?utm_source=chatgpt.com), [Declaration Files](https://www.typescriptlang.org/docs/handbook/declaration-files/introduction.html?utm_source=chatgpt.com).