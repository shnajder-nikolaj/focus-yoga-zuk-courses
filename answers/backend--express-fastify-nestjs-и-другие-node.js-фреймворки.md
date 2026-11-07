# Чем Express, Fastify и NestJS отличаются по уровню абстракции и организации приложения?

Express даёт небольшой HTTP/middleware каркас и оставляет организацию приложения команде. Fastify делает акцент на lifecycle hooks, plugin encapsulation и обработке схем. NestJS предлагает модули, DI, controllers и общие механизмы поверх HTTP adapter.

NestJS можно использовать с Express или Fastify, поэтому это не три полностью взаимоисключающих уровня транспорта. Выбирают по нужным интеграциям, дисциплине команды и стоимости сопровождения. Минимальный каркас требует собственных соглашений, а высокий уровень абстракции — понимания его lifecycle.

# Как HTTP-запрос проходит через маршрутизацию и middleware в Express?

Express проходит подходящие middleware и routes в порядке регистрации. Обработчик может завершить ответ, передать управление через `next()` или передать ошибку через `next(err)`. Router позволяет сгруппировать маршруты и локальные middleware.

Body parser должен сработать до кода, читающего разобранное тело, а authentication и ограничения — до защищённого действия. Error middleware регистрируют после обрабатываемых маршрутов. Если handler не отправил ответ и не передал управление, запрос зависнет до другого ограничения времени.

# Как Express 5 обрабатывает ошибки async handlers и какие ограничения остаются?

В **Express 5** rejection или throw в возвращённом Promise route handler/middleware автоматически передаётся в error pipeline. `async`-функция возвращает Promise, поэтому ошибка ожидаемой через `await` операции попадает туда.

Ошибки detached promises, timers, callback API и stream events требуют явной обработки: они не становятся частью возвращённой цепочки автоматически. Error middleware имеет сигнатуру `(err, req, res, next)`; после отправки headers нужен отдельный путь завершения. В Express 4 правила для Promise иные. [Обработка ошибок Express](https://expressjs.com/en/guide/error-handling/).

# Как hooks и encapsulation plugins организуют lifecycle запроса в Fastify?

Fastify предоставляет hooks на определённых этапах, например `onRequest`, `preParsing`, `preValidation`, `preHandler`, `preSerialization`, `onSend` и `onResponse`. На ранних этапах разобранного body ещё нет, поэтому проверку размещают там, где доступны необходимые данные.

Plugin encapsulation ограничивает область зарегистрированных hooks, decorators и других настроек дочерним контекстом. Это помогает создавать изолированные наборы routes; поведение специальных plugin-обёрток нужно учитывать отдельно. Нельзя одновременно завершать обработку и продолжать её другим способом. [Lifecycle Fastify](https://fastify.dev/docs/latest/Reference/Lifecycle/).

# Как schemas validation и response serialization работают в Fastify?

Fastify использует схемы для проверки входа и отдельные response schemas для сериализации ответа; стандартные механизмы используют Ajv и fast-json-stringify. Response schema помогает контролировать публичные поля, но не заменяет авторизацию и правильный DTO.

Преобразования и удаление полей зависят от настроек compiler. Схемы считаются кодом приложения: стандартные компиляторы генерируют функции, поэтому нельзя принимать произвольную схему от пользователя. Запросы к БД и долгие бизнес-проверки выносят из начальной структурной валидации. [Validation и serialization Fastify](https://fastify.dev/docs/latest/Reference/Validation-and-Serialization/).

# Как NestJS modules, imports, exports и providers задают границы зависимостей?

Модуль объявляет собственные controllers и providers; `exports` определяет доступные другим модулям providers, а `imports` подключает модули с нужными экспортами. Это задаёт область видимости и граф сборки DI, а не отдельную deployment-границу.

Если один и тот же service заново объявить в providers нескольких модулей, можно получить отдельные экземпляры вместо ожидаемого общего. Лучше импортировать модуль-владельца. Global modules и циклические ссылки используют осознанно: они могут скрывать зависимости и усложнять тестирование. [Modules NestJS](https://docs.nestjs.com/modules).

# Как HTTP adapter NestJS влияет на переносимость приложения между Express и Fastify?

NestJS абстрагирует часть HTTP-операций через adapter, но прямое использование platform-specific `Request`/`Response`, middleware и upload plugins связывает код с Express или Fastify. Смена adapter не гарантирует работоспособность таких интеграций.

Для переносимости опираются на поддерживаемые абстракции Nest и изолируют платформенные участки. Проверяют cookies, sessions, streaming, errors, uploads и тестовый HTTP-client. Нагрузочный benchmark полезен только после проверки функциональной совместимости. [HTTP adapters NestJS](https://docs.nestjs.com/techniques/performance).

# В каком порядке в NestJS выполняются guards, pipes, interceptors и exception filters?

В общем случае порядок такой: middleware → guards → interceptors до handler → pipes → controller/use case → interceptors на обратном пути → ответ. Guards решают доступ, pipes проверяют или преобразуют аргументы, interceptors оборачивают выполнение.

Exception filters подключаются при необработанной ошибке и не являются обязательным этапом успешного ответа. Порядок внутри global/controller/route уровней различается для механизмов; filters ищут от более локального уровня, а возврат через interceptors идёт в обратном порядке. [Request lifecycle NestJS](https://docs.nestjs.com/faq/request-lifecycle).

# Как request-scoped providers влияют на создание объектов и производительность NestJS?

Provider со `Scope.REQUEST` создаётся для контекста запроса. Request scope распространяется вверх по цепочке внедрения: controller, зависящий от request-scoped service, также становится request-scoped. Поэтому одна зависимость может расширить объём создаваемого на каждый запрос графа.

Используют такой scope для действительно request-specific состояния и измеряют стоимость на реальной нагрузке. Общие clients и connection pools обычно выгодно сохранять долгоживущими. Transient scope имеет другую семантику и не равен одному экземпляру на HTTP-запрос. [Injection scopes NestJS](https://docs.nestjs.com/fundamentals/injection-scopes).

# Как безопасно подключать сторонние плагины и middleware Node.js-фреймворка?

Проверяют назначение, поддержку версии framework/runtime, состав зависимостей и нужные полномочия. Плагин подключают в правильном порядке и области, ограничивают размеры, timeouts и доступные routes. Обновления зависимостей должны проходить обычный review и проверку поведения.

Особое внимание нужно parser, authentication, proxy и upload middleware: они влияют на границу доверия. Плагин не должен незаметно читать секреты или менять глобальное состояние. Для Fastify также проверяют совместимость plugin API и encapsulation, для Nest — выбранный HTTP adapter.

# Как учитывать streaming, uploads и backpressure при выборе Node.js-фреймворка?

Проверяют возможность работать с потоками без полного buffering, отменять передачу и соблюдать backpressure. Upload требует лимита размера, числа частей, памяти и диска; multipart parser может иметь собственные настройки и ошибки.

Streaming-ответ нельзя всегда обработать как обычный JSON DTO: после headers часть ошибок уже не преобразуется в новый HTTP-статус. В Nest учитывают поддержку конкретного adapter и plugins. Сравнивают память и p99 при медленных клиентах, а не только скорость небольшого ответа.

# Как сравнивать Node.js-фреймворки и планировать миграцию без опоры только на benchmark RPS?

Берут характерные endpoints с parsing, validation, auth, БД, serialization и telemetry. Измеряют задержки под конкурентной нагрузкой, память, startup и поведение при ошибках. Также оценивают экосистему, тестирование, обновления и знакомство команды.

Миграцию ведут через совместимый контракт и постепенное переключение routes или сервиса, проверяя cookies, статусы и форматы ошибок. Разница в чистом RPS на `hello world` может исчезнуть на реальной БД-нагрузке; сама по себе она не оправдывает стоимость переноса.
