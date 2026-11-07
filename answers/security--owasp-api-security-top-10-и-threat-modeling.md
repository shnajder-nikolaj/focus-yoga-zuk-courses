# Какие риски выделяет OWASP API Security Top 10 2023 и как использовать этот список?

Редакция **2023** выделяет десять категорий: Broken Object Level Authorization; Broken Authentication; Broken Object Property Level Authorization; Unrestricted Resource Consumption; Broken Function Level Authorization; Unrestricted Access to Sensitive Business Flows; Server Side Request Forgery; Security Misconfiguration; Improper Inventory Management; Unsafe Consumption of APIs.

Это ориентир для обсуждения рисков и поиска пропущенных классов защиты. Он не заменяет threat model конкретной системы, verification requirements и проверку бизнес-инвариантов. В документации указывают редакцию: названия и группировка категорий меняются. [OWASP API Security Top 10 2023](https://api-security.owasp.org/editions/2023/en/0x11-t10/).

# Чем BOLA, BFLA и Broken Object Property Level Authorization различаются на уровне API?

**BOLA** возникает, когда субъект может обращаться к недоступному ему объекту, например чужому заказу. **BFLA** означает доступ к запрещённой функции, например административному подтверждению возврата. **Broken Object Property Level Authorization** касается конкретных полей: чтения закрытой цены или изменения владельца через общий update endpoint.

Проверка роли на маршруте не заменяет проверку объекта и полей. Ограничения применяют при поиске данных, выполнении действия и формировании ответа; DTO не должен автоматически принимать все поля модели. [OWASP: API authorization risks](https://api-security.owasp.org/editions/2023/en/0x11-t10/).

# Как Broken Authentication проявляется в API с корректно работающей проверкой токенов?

Корректная signature validation защищает только один этап. Identity может быть скомпрометирована через слабый login, восстановление аккаунта, утечку session identifier, неверное связывание внешней identity или небезопасную выдачу новых credentials.

Проверяют весь жизненный цикл: регистрацию, вход, MFA, token issuance, refresh, recovery и завершение сессии. На каждом этапе нужны подходящие ограничения попыток, привязка к правильному subject и защита от replay. Валидный токен доказывает выполнение заданных проверок issuer, но не исправляет ошибку, допущенную до его выпуска.

# Как ограничивать Unrestricted Resource Consumption в API с batch и GraphQL-запросами?

Лимит запросов в секунду недостаточен, если один запрос создаёт тысячи внутренних операций. Для batch ограничивают число элементов и общий объём работы. В GraphQL учитывают depth, aliases, pagination, сложность resolvers и фактический fan-out.

Дополнительно ограничивают body size, время выполнения, concurrency, uploads и платные downstream operations. Квоты задают по tenant или account и дополняют общим admission control. Ограничения должны действовать до исчерпания ресурса, а их эффективность проверяют на дорогих допустимых входах. [OWASP: Unrestricted Resource Consumption](https://api-security.owasp.org/editions/2023/en/0xa4-unrestricted-resource-consumption/).

# Как защищать sensitive business flows от автоматизированного злоупотребления?

Sensitive flow может быть технически корректным, но вредным при массовом повторении: резервирование всего доступного товара, автоматическое создание accounts или использование промоакции. Сначала определяют бизнес-ограничение, субъекта и признаки злоупотребления.

Применяют quotas, ограничения частоты и объёма, правила eligibility, проверку последовательности действий и при необходимости step-up challenge. Одних IP limits мало из-за распределённых клиентов и общих сетей обычных пользователей. Идемпотентность устраняет повтор одной операции, но не ограничивает поток новых допустимых операций. [OWASP: Sensitive Business Flows](https://api-security.owasp.org/editions/2023/en/0xa6-unrestricted-access-to-sensitive-business-flows/).

# Как Security Misconfiguration и Improper Inventory Management связаны с жизненным циклом API?

Misconfiguration включает опасные defaults, открытые diagnostics, лишние методы, permissive policies и несогласованные настройки компонентов. Inventory management отвечает за понимание, какие hosts, endpoints, версии и среды существуют, кто ими владеет и какие данные они обрабатывают.

Забытый старый API может сохранить уязвимость после исправления основной версии. Поэтому retirement включает отключение routing, credentials и доступов, а не только удаление ссылки из документации. Inventory сверяют с фактическими deployments и трафиком. Применимость защит проверяют на всех доступных версиях и альтернативных путях запроса.

# Почему Unsafe Consumption of APIs требует проверки данных даже от доверенного поставщика?

Внешний API пересекает trust boundary, даже если поставщик известен. Его ответ может содержать пользовательские данные, ошибочные поля или значения, прошедшие через скомпрометированную систему. Успешный TLS защищает канал, но не бизнес-смысл payload.

Проверяют schema, размер, типы, допустимые значения и связь идентификаторов с локальными объектами. Ограничивают timeouts, redirects и downstream work, не передают чужие данные напрямую в SQL, template или shell. Ошибки и неожиданные статусы обрабатывают явно, исключая небезопасные fallback. [OWASP: Unsafe Consumption of APIs](https://api-security.owasp.org/editions/2023/en/0xaa-unsafe-consumption-of-apis/).

# Как описать assets, data flows и trust boundaries для threat model backend-сервиса?

Assets описывают то, что нужно защитить: данные, полномочия, деньги, доступность и доверие к результату. На data flow diagram показывают actors, процессы, stores и внешние зависимости с направлениями данных. **Trust boundary** обозначает смену доверия или полномочий, а не просто сетевую линию.

Для backend важны ingress, identity provider, очередь, workers, data stores и административные пути. Указывают assumptions: кто контролирует вход, как передаётся identity, где выполняется authorization. Слишком подробная схема мешает анализу, слишком общая скрывает существенный переход доверия. [OWASP: Threat Modeling](https://cheatsheetseries.owasp.org/cheatsheets/Threat_Modeling_Cheat_Sheet.html).

# Как STRIDE и attack trees помогают приоритизировать угрозы конкретному API?

**STRIDE** помогает систематически искать spoofing, tampering, repudiation, information disclosure, denial of service и elevation of privilege. Это категории вопросов к элементам модели, а не готовая оценка риска. **Attack tree** раскладывает цель на необходимые или альтернативные предпосылки.

Приоритет определяют по доступности пути, требуемым правам, вероятности и ущербу для конкретного asset. Например, чтение чужих документов оценивают через возможность выбора ID и отсутствие object check, а не только через название категории. Отдельно записывают неизвестные предположения и способ их проверить.

# Как превратить threat model в проверяемые меры защиты и поддерживать её при изменениях?

Для угрозы фиксируют сценарий, предпосылки, affected assets и меру, которая прерывает конкретный путь. Затем задают проверку: например, запрос к объекту другого tenant должен быть отклонён при любом поддерживаемом способе доступа.

Модель связывают с requirements, tests, monitoring и владельцами остаточного риска. Её пересматривают при появлении новой integration, роли, data flow или deployment topology. Review проверяет не только наличие меры в документе, но и её исполнение в выпущенной системе. Threat modeling становится частью изменения архитектуры и API. [OWASP: Threat Modeling](https://cheatsheetseries.owasp.org/cheatsheets/Threat_Modeling_Cheat_Sheet.html).

