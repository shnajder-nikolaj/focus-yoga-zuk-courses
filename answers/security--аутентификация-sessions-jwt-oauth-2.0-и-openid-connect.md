# Как backend управляет созданием, обновлением идентификатора и сроками серверной сессии?

Сервер создаёт непредсказуемый session identifier и хранит связанное состояние с subject, временем и уровнем аутентификации. После успешного login и повышения привилегий identifier обновляют, а прежний перестаёт давать тот же доступ: это защищает от session fixation.

Различают idle timeout и absolute lifetime; их проверяет сервер, а не только cookie expiration. Logout и security events отзывают соответствующее состояние. Cookie получает необходимые `Secure`, `HttpOnly`, `SameSite` и ограниченный scope; это дополняют CSRF-защитой. В распределённой системе определяют consistency и доступность session store. [OWASP: Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html).

# Как организовать проверку credentials с защитой от enumeration и credential stuffing?

Password проверяют специализированной password-hashing library с сохранёнными параметрами и salt. Ответы для неизвестного пользователя и неверного пароля не должны очевидно раскрывать существование account через текст, status или быстрый обход дорогой проверки.

Credential stuffing ограничивают сочетанием account-based и network-based rate limits, наблюдением за аномалиями и подходящим MFA. Жёсткая бессрочная блокировка по нескольким попыткам может стать отказом в обслуживании для владельца. Не записывают пароли в logs и не уменьшают стоимость hashing только ради пропускной способности login endpoint. [OWASP: Authentication](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html).

# Какие проверки JWT обязан выполнить resource server кроме проверки подписи?

Resource server использует заранее разрешённые algorithms и ключи доверенного issuer, проверяет ожидаемые `iss`, `aud`, назначение и тип токена. Временные claims, например `exp` и `nbf`, проверяют согласно принятому token profile с небольшим ограниченным clock skew; обязательные claims нельзя молча пропускать.

Не доверяют payload до validation и не принимают ID Token вместо access token. `kid` выбирает ключ только из допустимого набора, а не произвольный file или URL. После token validation всё ещё требуется authorization конкретного действия и объекта. [RFC 8725](https://www.rfc-editor.org/rfc/rfc8725.html).

# Как безопасно обновлять signing keys и JWKS cache при проверке токенов?

При плановой ротации новый public key сначала становится доступен validators, затем issuer начинает подписывать им новые токены. Прежний ключ сохраняют для проверки ещё допустимых старых токенов на согласованный срок. При компрометации нужен отдельный экстренный процесс, который может требовать немедленного отказа от старых токенов.

JWKS получают из доверенной конфигурации issuer, проверяя TLS и ограничивая refresh. Неизвестный `kid` может вызвать контролируемое обновление, но не бесконечные внешние запросы. Cache имеет срок и правила работы при ошибке; произвольные `jku` из токена не определяют trust anchor. [RFC 8725](https://www.rfc-editor.org/rfc/rfc8725.html).

# Как роли OAuth 2.0 определяют назначение access token, authorization code и client credentials?

В OAuth 2.0 **resource owner** предоставляет полномочия, **client** запрашивает их, **authorization server** выдаёт credentials, а **resource server** принимает access token для защищённого API. Authorization code — короткоживущий результат redirect flow, который client обменивает на token через token endpoint.

Access token представляет разрешённый доступ и может быть opaque или JWT. Client credentials grant представляет действия самого client, а не автоматически пользователя. ID Token относится к OIDC и сообщает client об аутентификации subject; его назначение отличается от права вызвать произвольный API. [OpenID Connect Core](https://openid.net/specs/openid-connect-core-1_0.html).

# Как backend связывает Authorization Code, PKCE, redirect URI и OAuth transaction?

Backend сохраняет контекст OAuth transaction: ожидаемый issuer, client, redirect URI, одноразовую привязку к начавшей login сессии и PKCE verifier. В authorization request передаётся соответствующий challenge; на callback проверяют связь ответа с этой transaction.

Code обменивают на token с исходным verifier и требуемой client authentication. Authorization server проверяет binding code к client, redirect URI и PKCE, а также одноразовость и срок code. PKCE не заменяет все проверки redirect и issuer. Для web backend предпочтителен проверенный protocol client с безопасной конфигурацией. [RFC 9700](https://www.rfc-editor.org/rfc/rfc9700.html).

# Как валидировать OIDC ID Token и связывать внешний subject с локальной учётной записью?

OIDC client проверяет issuer, signature по доверенным keys, audience, срок и остальные требования выбранного flow. Если `nonce` был отправлен, проверяют его совпадение и связь с transaction; при применимости проверяют `azp` и дополнительные claims по спецификации.

Внешнюю identity связывают с локальным account по паре **issuer + subject**, а не по отображаемому имени. Email и даже факт его верификации сами по себе не разрешают произвольное автоматическое объединение accounts. Linking требует контролируемого подтверждения владения обеими identities. Валидацию реализуют поддерживаемой OIDC library. [OIDC: ID Token Validation](https://openid.net/specs/openid-connect-core-1_0.html#IDTokenValidation).

# Как хранить refresh token families и атомарно обнаруживать повторное использование токена?

Для opaque refresh token хранят защищённый fingerprint, связь с grant или family, client, subject, срок и состояние использования. В одной атомарной операции действующий token помечают использованным и регистрируют successor. Повтор старого token сигнализирует о возможном replay и требует действий над связанной family.

Одновременный refresh и повтор после потерянного ответа могут выглядеть как кража: backend не умеет автоматически отличать их. Клиент сериализует refresh, а допустимые retry rules задают явно, сохраняя свойства защиты. Ротация не заменяет TLS, client binding и ограничение срока. [RFC 9700: Refresh Token Protection](https://www.rfc-editor.org/rfc/rfc9700.html#section-4.14).

# Как service-to-service authentication использует workload identity и audience-restricted tokens?

Workload получает identity через проверенную среду исполнения и использует её для краткоживущих credentials вместо общего постоянного пароля. В зависимости от системы это certificate, подписанное assertion или token от доверенного issuer. Получатель проверяет issuer, audience, срок и соответствие identity ожидаемому service.

Доступ ограничивают нужными resources и actions. Token для одного API не должен приниматься другим, а service authentication не означает право действовать от имени любого пользователя. Private network также не заменяет identity. Для особенно чувствительных сценариев рассматривают sender-constrained tokens по поддерживаемому протоколу.

# Как MFA, passkeys и account recovery меняют границы доверия backend-аутентификации?

MFA требует независимых факторов; два пароля не становятся двумя факторами. Passkeys используют public-key credentials, привязанные к relying party, и могут повышать phishing resistance. Backend проверяет challenge, origin, RP ID, signature и требуемые признаки user presence и user verification через WebAuthn library.

Recovery и добавление нового authenticator не должны становиться простым обходом сильного login. Для изменений credentials используют recent authentication, notifications и проверяемое recovery. Скомпрометированная session всё ещё опасна, поэтому passkey не заменяет session security и authorization. [OWASP: Passkey Security](https://cheatsheetseries.owasp.org/cheatsheets/Passkey_Security_Cheat_Sheet.html).

