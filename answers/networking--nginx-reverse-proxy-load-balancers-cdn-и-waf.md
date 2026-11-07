# Как reverse proxy отличается от forward proxy и L4 load balancer?

**Reverse proxy** принимает запросы от имени серверов и передаёт их backend, часто управляя HTTP, TLS, routing и caching. **Forward proxy** представляет клиента при обращении к внешним ресурсам.

**L4 load balancer** выбирает backend на уровне transport connection или потока, не обязательно понимая HTTP path и headers. L7 proxy может принимать решения по этим полям, но имеет собственные limits и lifecycle connections. TLS passthrough и termination дают разные возможности анализа. Выбор слоя определяет, какие client attributes и ошибки видны backend.

# Как Nginx выбирает server block и location для входящего запроса?

Nginx сначала учитывает **listen address/port**, затем подходящее server name для соответствующего этапа обработки; default server относится к listen context, а не магическому hostname. Для HTTPS сертификат выбирается раньше HTTP-запроса с учётом доступного SNI.

В обычной структуре locations важны exact match, наиболее длинный prefix, `^~` и порядок подходящих regex. Rewrite и internal redirects могут вызвать повторный выбор location. Поэтому правило «всегда первый блок» неверно. Проверяют полный config, включая includes и defaults, а не один видимый фрагмент. [Request processing Nginx](https://nginx.org/en/docs/http/request_processing.html).

# Как proxy_pass, URI rewrite и trailing slash влияют на путь backend-запроса?

В обычном prefix location `proxy_pass` с URI заменяет соответствующую часть нормализованного пути. Например, `location /api/` с `proxy_pass http://app/` обычно передаст `/api/users` как `/users`. Вариант без URI имеет другое предусмотренное поведение передачи пути.

Regex locations, variables, rewrite и internal redirects добавляют условия, поэтому один trailing slash нельзя оценивать отдельно от всей configuration. Проверяют query string, encoded characters и фактический upstream URI по тестам и logs. Случайное двойное удаление prefix часто выглядит как backend 404. [proxy_pass](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_pass).

# Как upstream balancing, keepalive и connection pools влияют на распределение нагрузки?

**Upstream balancing** выбирает backend по доступному алгоритму и configuration: round-robin, least connections или другой поддерживаемый вариант решают разные задачи. Keepalive переиспользует соединения, уменьшая handshake overhead, но требует согласования с upstream protocol и timeouts.

Pool size не является универсальным ограничением всех одновременно открытых connections. Длительные streams и WebSockets меняют баланс: один connection может представлять большую работу. Health, backend capacity и shared state приложения влияют на выбор. Sticky routing не заменяет устойчивое хранение session. [Nginx upstream](https://nginx.org/en/docs/http/ngx_http_upstream_module.html).

# Как connect, read и send timeouts proxy соотносятся с общим deadline запроса?

**Connect timeout** ограничивает установление upstream connection, а read/send timeouts часто относятся к интервалу между операциями I/O, а не полной длительности ответа. Клиентский deadline может закончиться раньше, оставив backend выполнять ненужную работу.

Согласуют общий budget через client, proxy и приложение, а также cancellation. Медленно поступающие bytes способны поддерживать активность при большой общей длительности, если есть только inactivity timeout. Учитывают TLS handshake и retries как часть budget. Значения выбирают для workload, а не одинаково увеличивают все таймауты при 504. [Proxy timeouts](https://nginx.org/en/docs/http/ngx_http_proxy_module.html).

# Как request и response buffering влияют на streaming, память и временные файлы?

**Request buffering** может сначала принять body, используя memory и temporary files, а затем передать upstream; это меняет latency начала обработки и возможность повторной отправки. **Response buffering** позволяет proxy читать backend независимо от темпа downstream client в доступных пределах.

Для streaming часто требуется другая policy, но отключение buffering связывает ресурсы backend с медленным клиентом и не отменяет все buffers на пути. Ограничивают body size, disk usage, connections и время. Проверяют flushing, compression и CDN, поскольку каждый промежуточный слой может снова накопить данные.

# Когда proxy retry безопасен и как он может повторить уже выполненную операцию?

Proxy может повторить запрос после connection failure или другого configured события. Но timeout ответа не доказывает, что backend ничего не выполнил: он мог уже зафиксировать заказ и потерять connection до ответа.

Для изменяющих операций нужна **idempotency** или другой способ согласования исхода, а retry должен учитывать метод, возможность повторить body и уже переданные клиенту данные. Несколько retry layers способны перемножить нагрузку. Ограничивают attempts и общий deadline. Автоматический retry без соответствующего бизнес-протокола может скрыть инфраструктурный сбой ценой duplicate effect.

# Как trusted proxy chain и forwarded headers защищают определение client IP и исходной схемы?

`Forwarded`, `X-Forwarded-For` и сведения о исходной scheme можно подделать, если приложение безусловно доверяет headers клиента. Edge proxy задаёт или корректно дополняет их, а backend доверяет только известной **proxy chain**.

В Nginx real IP configuration определяет trusted senders и правила выбора address. Ошибочная глубина chain меняет rate limits, audit и secure redirects. Если origin доступен напрямую, обход edge может позволить передать непроверенные значения. Учитывают IPv6, несколько hops и фактический адрес соединения. [Real IP module](https://nginx.org/en/docs/http/ngx_http_realip_module.html).

# Как CDN cache key, Vary, cookies и authorization влияют на корректность кэширования?

**Cache key** должен различать ответы, которые нельзя смешивать: host, relevant path/query и предусмотренные variants. **Vary** описывает variation по request headers в рамках HTTP caching rules, но CDN configuration должна реализовать нужное поведение.

Cookies и authorization требуют явной policy: персональный response не должен случайно стать общим из-за неучтённого identity. `private`, `no-store` и другие directives имеют разную семантику. Высокий hit rate не является достаточной целью, если возвращается чужое состояние. Проверяют multi-tenant, authenticated и anonymous сценарии. [HTTP caching](https://www.rfc-editor.org/rfc/rfc9111).

# Как invalidation, versioned assets и stale serving помогают обновлять CDN без несогласованных версий?

**Versioned assets**, например content-hashed filenames, позволяют длительное кеширование без подмены содержимого того же URL. Изменяемые entry documents получают согласованную более короткую policy, а старые assets сохраняют на период возможных references.

**Invalidation** распространяется не обязательно мгновенно на все caches. **Stale serving** поддерживает доступность по разрешённой policy, но может временно отдавать прежнюю версию. Для deployment проверяют совместимость HTML, scripts, API и service worker. Массовый purge способен вызвать cache stampede на origin, поэтому учитывают rate и reserve capacity.

# Как WAF, rate limiting и origin protection дополняют безопасность приложения?

**WAF** распознаёт и ограничивает определённые request patterns, **rate limiting** сдерживает нагрузку, а **origin protection** мешает обходить edge controls напрямую. Эти меры уменьшают риск, но не подтверждают корректность authorization и бизнес-инвариантов приложения.

Правила настраивают с учётом false positives, protocols и доверенного client identity. Один IP может представлять много пользователей за NAT, а attacker может распределить трафик. Доступ к origin ограничивают предусмотренными network и identity mechanisms. Наблюдают blocked requests и обходные пути, не записывая без нужды чувствительные payloads.

# Как access logs, upstream timings и health checks помогают диагностировать 502, 503 и 504?

**Access logs** связывают request, upstream address, response status и timings. Отдельные connect/header/response times помогают определить, ждали ли соединение, первый byte или передачу body; несколько attempts требуют учитывать все relevant values.

**502** часто отражает проблему получения корректного upstream response, **504** — timeout gateway, а **503** может возникать на разных layers из-за недоступности или ограничения. Сам status не даёт окончательной причины. Сопоставляют error logs, backend health и traces. Passive и active checks имеют разные implementation и availability, которые проверяют в используемой версии.
