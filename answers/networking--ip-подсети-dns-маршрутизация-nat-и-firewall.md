# Как IP address, prefix и subnet задают принадлежность узла сети в IPv4 и IPv6?

**IP address** идентифицирует interface в сетевом контексте, **prefix length** задаёт общую сетевую часть, а subnet описывает диапазон. CIDR-запись вроде `/24` или `/64` не сообщает сама по себе, какой маршрут реально настроен.

IPv4 и IPv6 отличаются размером адреса и рядом правил, включая broadcast и link-local addressing. Возможность direct delivery определяется on-link configuration и route, а не только визуальным сходством адресов. Учитывают несколько addresses на interface, namespaces и специальные prefixes; универсальная формула «в любой subnet всегда минус два адреса» неверна.

# Как longest prefix match и default route выбирают маршрут пакета?

В выбранной routing table обычно побеждает маршрут с **самым длинным подходящим prefix**. **Default route** с нулевой длиной используется, если нет более специфичного подходящего route. При одинаковой специфичности участвуют metrics и другие правила реализации.

Policy routing, source address, marks и network namespace могут сначала выбрать другую table или путь. Поэтому проверяют route lookup для конкретного destination и контекста, а не только один общий список. Наличие default gateway не гарантирует обратный маршрут и разрешение firewall. [Linux routing](https://man7.org/linux/man-pages/man8/ip-route.8.html).

# Как next hop, ARP и Neighbor Discovery связывают IP-маршрут с локальной доставкой?

Route указывает выходной interface и при необходимости **next hop**. В Ethernet для локальной передачи нужно получить link-layer address этого next hop: IPv4 обычно использует **ARP**, IPv6 — **Neighbor Discovery** через ICMPv6.

Если destination находится вне local link, frame адресуют gateway, а destination IP обычно остаётся адресом конечного получателя, пока его не изменит специальный механизм вроде NAT. Неудачное neighbor resolution может блокировать связь при правильной routing table. Link-local IPv6 address дополнительно требует корректной interface scope.

# Как private, public, loopback и link-local addresses различаются по области использования?

**Public address** предназначен для глобальной маршрутизации при наличии соответствующих routes и policies. **Private IPv4** и IPv6 unique-local используются в иных областях и сами по себе не означают полную изоляцию от внешнего доступа.

**Loopback** возвращает трафик в локальный network context. **Link-local** ограничен локальным link и не заменяет обычный маршрутизируемый адрес сервиса. Приложение, слушающее только loopback контейнера, может быть недоступно соседнему контейнеру. Scope, listener binding и firewall проверяют отдельно; «private» не является механизмом authentication.

# Как SNAT, DNAT и port mapping меняют адреса и влияют на обратный путь?

**SNAT** меняет source address, **DNAT** — destination, а port mapping может также преобразовывать transport port. Stateful NAT сохраняет соответствие для обратных packets, чтобы соединение выглядело ожидаемым для участников.

Из-за NAT backend может видеть gateway вместо исходного client IP, а logs разных layers — разные tuples. Асимметричный return path, истечение mapping и нехватка ports способны нарушать связь. NAT не является полноценной authorization policy: отдельно проверяют firewall и доступные routes. Hairpin и несколько NAT stages добавляют зависимости, которые учитывают при диагностике.

# Как stateful firewall и connection tracking отличаются от простого фильтра packets?

**Stateless filter** проверяет отдельный packet по полям и правилам, а **stateful firewall** использует connection tracking для сопоставления с известным обменом. Для TCP это связано с состоянием соединения, для UDP — с более условной моделью activity и timeouts.

Это позволяет разрешать предусмотренные responses без открытия любого входящего packet. Но переполнение conntrack, асимметричные routes и ошибочные assumptions о state могут давать drops. Состояние `established` в firewall не подтверждает успешную application authentication. Анализируют порядок hooks, NAT и policies в фактическом dataplane.

# Как DNS recursion, authoritative servers и caching участвуют в разрешении серверного имени?

Клиент обращается к configured resolver; **recursive resolver** получает нужный ответ, при необходимости проходя делегирование к authoritative servers, и кеширует его по правилам. **Authoritative server** отвечает за свою зону, а не обязан выполнять всю recursion за клиента.

Запрос может завершиться локальным или промежуточным cache, поэтому каждый lookup не проходит всю иерархию. Наличие DNS answer подтверждает разрешение имени, но не listener, route или TLS identity. Для сервера важны используемый resolver, record type и фактическое место запроса. [DNS concepts](https://www.rfc-editor.org/rfc/rfc1034).

# Как TTL, negative caching и split-horizon DNS влияют на переключение сервиса?

**TTL** ограничивает обычное кеширование record по DNS semantics, а **negative caching** сохраняет определённые отрицательные ответы. Смена записи не очищает мгновенно уже существующие caches и открытые client connections.

**Split-horizon DNS** намеренно даёт разные ответы разным сетевым контекстам, например private origin внутри VPC и public load balancer снаружи. Это полезно, но усложняет перенос и диагностику. Для cutover заранее учитывают прежний TTL, client caching и connection lifetime. Одна проверка через public resolver не доказывает, что backend использует тот же answer.

# Как DNS search domains, hosts file и resolver configuration создают неожиданные адреса?

ОС может искать имя через **hosts file**, DNS и другие configured name-service механизмы. **Search domains** дополняют короткое имя, а настройки resolver и namespace влияют на порядок и конкретные queries.

Поэтому `db` и полное имя не обязаны разрешаться одинаково на laptop, VM и Pod. Один диагностический tool может выполнять DNS напрямую, а приложение — использовать системный resolver с другой логикой. Проверяют effective configuration процесса, record family и итоговый IP. Устаревшая локальная hosts entry способна скрыть правильное изменение authoritative DNS.

# Как IPv4/IPv6 dual stack и выбор адреса клиентом влияют на доступность?

При **dual stack** имя может иметь A и AAAA records, а клиент выбирает порядок или конкурирующие попытки подключения. Рабочий IPv4 не подтверждает доступность IPv6, и наоборот: routing и firewall могут различаться.

**Happy Eyeballs** уменьшает задержку выбора в поддерживающих его clients, но не исправляет неисправную семью адресов и не действует одинаково во всех библиотеках. Проверяют обе families, source address и фактический destination. Простое удаление AAAA может скрыть причину вместо восстановления ожидаемой dual-stack конфигурации. [Happy Eyeballs](https://www.rfc-editor.org/rfc/rfc8305).

# Как MTU, fragmentation и Path MTU Discovery объясняют частично работающую сеть?

**MTU** ограничивает размер packet на link, а **Path MTU Discovery** помогает sender учитывать меньшую границу на пути. Fragmentation и сообщения о слишком большом packet имеют разные правила в IPv4 и IPv6; IPv6 routers не выполняют обычную промежуточную fragmentation.

Если необходимые ICMP-сигналы блокируются, маленький запрос может работать, а большой upload или TLS exchange — зависать. Overlays и tunnels уменьшают полезную MTU. Проблему подтверждают sizes, counters и captures с правильных точек; одинаковый симптом может также возникать из-за потерь, proxy limits и application buffering.

# Как проверить путь от DNS и route до NAT и firewall без вывода по одному ping?

Проверяют имя и итоговый IP, source interface, route и neighbor resolution, затем listener, transport handshake и reverse path. Сопоставляют NAT mapping, firewall counters и capture по обе стороны предполагаемой границы.

**Ping** использует отдельный протокол и не подтверждает доступность нужного TCP/UDP port, TLS или application endpoint; его запрет тоже не доказывает отсутствие нужной связи. Диагностика должна повторять relevant protocol и network context клиента. Изменяют только подтверждённый участок configuration, сохраняя evidence о том, где packet перестал проходить.
