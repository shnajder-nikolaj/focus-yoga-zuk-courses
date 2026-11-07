# Какие гарантии TCP даёт байтовому потоку и почему приложение должно задавать границы сообщений?

**TCP** предоставляет упорядоченный надёжный поток bytes в пределах соединения, выполняя retransmission и flow/congestion control. Он не сохраняет границы application writes: один `write` может читаться частями, а несколько writes — одним чтением.

Протокол задаёт framing: length prefix, delimiter с escaping или другую однозначную модель. Ограничивают размер и время сборки сообщения. TCP acknowledgment подтверждает transport progress, а не commit бизнес-операции. После разрыва часть уже переданных данных могла быть обработана peer, поэтому повтор запроса требует отдельной семантики.

# Как UDP, packet loss и congestion control влияют на проектирование серверного протокола?

**UDP** передаёт datagrams с границами, но не обеспечивает универсальные гарантии доставки, порядка и отсутствия duplicates. Большая datagram может столкнуться с fragmentation, MTU и buffer limits; receive buffer тоже способен терять данные.

Если application требует retries, ordering или congestion control, это реализует выбранный protocol поверх UDP, а не один flag socket. QUIC является примером такой более сложной системы. Неограниченная отправка при потерях способна ухудшить сеть. Выбор UDP оправдывают требуемой семантикой, а не только отсутствием TCP handshake.

# Как TCP backlog, accept queue, keepalive и half-close связаны с жизненным циклом соединения?

На сервере очереди незавершённых handshakes и соединений, ожидающих `accept`, имеют свои limits и зависят от ОС. **Backlog** приложения — часть configuration, а не единственный глобальный предел.

**TCP keepalive** помогает обнаруживать некоторые потерянные peer connections при configured timings, но не измеряет application health. **Half-close** закрывает одно направление: получение EOF не обязательно запрещает отправку в другом. FIN и reset имеют разный смысл. Connection lifecycle проверяют вместе с accept rate, descriptors и graceful shutdown, а не только числом sockets.

# Как TLS handshake, certificate chain и hostname verification устанавливают доверие к серверу?

TLS handshake согласует параметры и key material и проверяет предусмотренную identity peer. **Certificate chain** связывает предъявленный certificate с trusted root, а **hostname verification** проверяет соответствие ожидаемому имени сервиса.

Одна валидная цепочка без проверки нужного имени недостаточна. Учитывают validity period, local clock и policy доверия или отзыва. Подключение по IP при ожидаемом DNS name требует правильной configuration, а не отключения validation. TLS защищает канал в своей модели, но не подтверждает права пользователя на операцию продукта. [TLS 1.3](https://www.rfc-editor.org/rfc/rfc8446).

# Чем SNI, ALPN и HTTP Host различаются при выборе виртуального сервера и протокола?

**SNI** передаёт имя для выбора TLS virtual server и certificate по поддерживаемой handshake-модели. **ALPN** согласует application protocol, например HTTP/2. **HTTP Host** или соответствующее `:authority` HTTP/2 относятся уже к HTTP-запросу.

Эти значения не взаимозаменяемы и могут обрабатываться разными layers. Неверный Host при правильном SNI способен попасть в другой route, а неправильное certificate name — прервать TLS до HTTP. Доступность SNI наблюдателю зависит и от поддерживаемых механизмов защиты handshake. Проверяют каждое значение отдельно, особенно при proxy к upstream по IP.

# Как TLS termination, mTLS и повторное шифрование до upstream задают разные проверки identity?

При **TLS termination** proxy становится endpoint внешнего шифрования и видит plaintext. Соединение до upstream может быть отдельным TLS-сеансом с собственной проверкой server identity. Просто включить encryption без certificate verification недостаточно для нужного доверия.

**mTLS** добавляет authentication клиента certificate-механизмом на конкретном участке, но application authorization остаётся отдельной. Если proxy передаёт сведения о client certificate в headers, backend должен доверять источнику этих headers, а не принимать их от любого клиента. End-to-end identity не следует автоматически из наличия нескольких зашифрованных участков.

# Как HTTP/2 multiplexing и flow control взаимодействуют с TCP head-of-line blocking?

**HTTP/2** передаёт несколько streams по одному соединению и использует stream-level и connection-level flow control для предусмотренных DATA. Это уменьшает application-level сериализацию HTTP/1.1, но все streams всё ещё используют TCP byte stream.

Потеря TCP segment может задержать доставку последующих bytes, затронув несколько HTTP/2 streams: это transport **head-of-line blocking**. Кроме того, общий congestion budget и server concurrency limits влияют на latency. Multiplexing не делает один connection неограниченной ёмкости и не отменяет backpressure. [HTTP/2](https://www.rfc-editor.org/rfc/rfc9113).

# Как QUIC и HTTP/3 переносят multiplexing на UDP и меняют поведение при потере пакетов?

**QUIC** реализует защищённый transport поверх UDP с independently ordered streams, loss recovery и congestion control. **HTTP/3** использует его для HTTP, поэтому потеря данных одного stream не требует во всех случаях задерживать доставку bytes другого, как в общем TCP-потоке.

При этом остаются общий network bottleneck, congestion и зависимости protocol, поэтому «потери больше не влияют на другие запросы» слишком сильное утверждение. Учитывают UDP reachability, MTU, connection IDs и поддержку server/proxy/client. QUIC не равен ненадёжной отправке обычных UDP datagrams без протокола. [QUIC](https://www.rfc-editor.org/rfc/rfc9000).

# Почему TLS 1.3 и QUIC 0-RTT требуют учитывать replay для изменяющих запросов?

**0-RTT early data** позволяет отправить часть application data до полного завершения нового handshake с использованием ранее полученного context. Эти данные имеют ограничения replay protection: attacker может попытаться повторить допустимый early request.

Сервер принимает 0-RTT только для операций и deployment, где это соответствует policy, либо отклоняет его и требует обычного пути. Одного названия HTTP method недостаточно, если endpoint фактически меняет состояние. Для важных изменяющих действий нужны безопасная идемпотентность и корректные ограничения; encryption early data не гарантирует единственность эффекта. [TLS early data](https://www.rfc-editor.org/rfc/rfc8446#section-8).

# Как WebSocket handshake и framing отличаются от обычного HTTP request/response?

При обычном HTTP/1.1 **WebSocket handshake** согласует upgrade, после чего connection передаёт WebSocket frames, а не независимые request/response для каждого сообщения. Для HTTP/2 и HTTP/3 существуют отдельные предусмотренные механизмы, поддержку которых проверяют у всей цепочки.

Frames имеют собственные правила types, fragmentation, masking и control messages. Граница frame не обязана совпадать с одним полным бизнес-сообщением. Authentication и разрешённый origin проверяют отдельно: handshake key не является пользовательским credential. Proxy должен поддерживать нужный tunnel lifecycle, timeouts и limits.

# Как WebSocket backpressure, heartbeat и connection limits защищают долгоживущий сервер?

Медленный клиент может заставить сервер бесконечно накапливать outbound data. **Backpressure** требует ограниченной очереди, policy замедления или отключения и контроля message size; нельзя считать успешный локальный `send` доказательством немедленного получения peer.

**Heartbeat** проверяет живость по выбранному protocol и помогает пережить idle timeouts промежуточных proxies. Различают transport ping/pong и готовность бизнес-функции. Задают connection limits, authentication lifetime и cleanup подписок. Большое число почти idle connections всё равно расходует descriptors, memory и scheduler resources.

# Как согласовать application deadlines, connection draining и отмену работы при обрыве клиента?

Общий **application deadline** ограничивает полезную работу запроса, а connection timeouts и idle timers решают отдельные задачи. При обрыве клиента работа не отменяется автоматически во всех downstream: нужно передать cancellation и корректно освободить ресурсы.

**Connection draining** прекращает приём новой работы и завершает допустимую текущую перед остановкой. Для multiplexed protocols используют соответствующую семантику закрытия, а долгоживущим connections задают понятный reconnect. Отмена ожидания не откатывает уже совершённый эффект, поэтому unknown outcome согласуют по operation ID и бизнес-протоколу.
