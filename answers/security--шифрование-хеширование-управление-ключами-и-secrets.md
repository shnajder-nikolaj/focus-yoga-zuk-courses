# Как выбирать между encryption, hashing, MAC и digital signature по требуемому свойству?

**Encryption** обеспечивает конфиденциальность при сохранности ключа; для защиты от подмены нужен authenticated режим или отдельный корректно построенный механизм integrity. **Hash** даёт digest без секрета и не подтверждает, кто создал сообщение. **MAC** проверяет целостность и подлинность между участниками с общим secret.

**Digital signature** позволяет проверять подпись public key без права создавать её. Сам факт успешной проверки не связывает ключ с нужной identity без доверенного механизма распределения. Например, обычный hash загруженного файла не защищает от атакующего, способного заменить и файл, и digest.

# Как salt, pepper и параметры password hashing влияют на хранение и обновление паролей?

Уникальный **salt** не является секретом и мешает переиспользованию предвычисленных таблиц между пользователями. Password hash должен быть дорогим для перебора: например, Argon2id использует настроенные time и memory costs. Значения параметров хранят рядом с hash и выбирают по действующим рекомендациям и допустимой стоимости проверки.

**Pepper** — дополнительный secret вне password database; его потеря или смена требует отдельного плана. После успешного login устаревший hash можно пересчитать с новыми параметрами. Обычный быстрый SHA-256 не заменяет password hashing, а высокая стоимость требует защиты login от перегрузки. [OWASP: Password Storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html).

# Как AEAD использует nonce, authentication tag и associated data для защиты записи?

**AEAD** одновременно шифрует plaintext и проверяет целостность ciphertext и associated data. `AAD` остаются открытыми, но защищены от незаметной подмены: в них можно включить trusted record ID или tenant context. Nonce и tag хранят вместе с записью согласно формату library.

Для AES-GCM и многих других AEAD nonce не должен повторяться с тем же ключом; его генерацию проектируют с учётом нескольких writers и восстановления из backup. Не используют plaintext до успешной проверки tag и не конструируют собственную криптосхему. Ошибка authentication означает отказ, а не частично успешное расшифрование. [OWASP: Cryptographic Storage](https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html).

# Как envelope encryption разделяет DEK и KEK и ограничивает доступ к plaintext?

**DEK** шифрует данные, а **KEK** защищает сам DEK. Хранят ciphertext и wrapped DEK; KEK обычно управляется через KMS или HSM. Для чтения разрешённый workload разворачивает DEK через нужную службу и использует его для данных.

Так можно разделить ключи по scope и менять wrapping key без обязательного повторного шифрования всего большого payload. Однако скомпрометированный процесс с правом unwrap может увидеть plaintext. Ограничивают IAM, audit, время хранения keys в memory и учитывают доступность KMS при восстановлении. [Google Cloud: Envelope encryption](https://docs.cloud.google.com/kms/docs/envelope-encryption).

# Как CSPRNG, длина токена и безопасное сравнение влияют на криптографические операции?

Security tokens и keys создают через **CSPRNG** операционной системы или проверенной crypto library. Timestamp, последовательный counter, UUID произвольного вида и обычный pseudo-random generator не являются универсальной заменой непредсказуемому secret.

Устойчивость зависит от случайных bits, а не количества символов после Base64 encoding. Ограничивают срок, число попыток и область применения token. Секретные значения и MAC сравнивают предусмотренной библиотекой constant-time операцией при соблюдении её требований; это уменьшает timing leakage сравнения, но не делает весь endpoint автоматически constant-time. [OWASP: Cryptographic Storage](https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html).

# Как организовать жизненный цикл ключа от генерации до ротации, отзыва и уничтожения?

Для ключа определяют назначение, algorithm, owner, version, срок использования и доступные операции. Keys разных назначений разделяют. Генерацию, хранение, выдачу, rotation и audit выполняют через контролируемые средства; backup keys защищают не слабее основных.

При плановой rotation новый ключ используется для новых данных, старый может временно оставаться для чтения. Компрометация требует отзыва, ограничения доступа и оценки данных, уже раскрытых атакующему: новое шифрование не отменяет утечку. Уничтожение согласуют с retention и восстановлением, чтобы не сделать нужные backups нечитаемыми. [OWASP: Key Management](https://cheatsheetseries.owasp.org/cheatsheets/Key_Management_Cheat_Sheet.html).

# Как TLS termination и mTLS определяют защищённый участок и identity соединения?

TLS защищает конкретное соединение между проверенными endpoints. Если TLS завершается на load balancer, участок до backend требует собственного защищённого канала согласно модели угроз. Headers о пользователе или исходном TLS принимают только от доверенного proxy и очищают от клиентской подмены.

В **mTLS** certificate предъявляют обе стороны, но приложение ещё должно сопоставить certificate identity с разрешённым workload и проверить права. Контролируют trust roots, hostname или service identity, expiry и rotation. Шифрование канала не защищает от скомпрометированного endpoint и не заменяет object authorization. [OWASP: TLS](https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Security_Cheat_Sheet.html).

# Как доставлять secrets приложению и предотвращать их утечку через логи и диагностику?

Приложение получает secrets через secret manager, workload identity или ограниченный runtime mount с минимальными правами. Env variables тоже являются способом доставки, но могут попасть в diagnostics и process dumps; сам способ хранения не отменяет lifecycle и rotation.

Запрещают запись credentials в repository, image layers, URL, traces и crash reports. Redaction применяют до отправки в logging pipeline, включая error objects и HTTP headers. Secret scanning помогает обнаружить утечку, после которой secret отзывают и заменяют, а не только удаляют строку из файла. [OWASP: Secrets Management](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html).

# Когда для fingerprint токена нужен обычный hash, а когда HMAC с отдельным ключом?

Если token имеет высокую случайную энтропию, его cryptographic hash позволяет искать и проверять значение без хранения самого bearer secret. Слабый или предсказуемый token остаётся подбираемым даже при таком хранении.

**HMAC** с отдельным secret key полезен, когда требуется ограничить возможность вычислять matching fingerprints после утечки одной базы. Он также разделяет доверие между storage и системой проверки. Key version и rotation нужно учитывать в lookup. HMAC не увеличивает энтропию исходного token и не заменяет password KDF для пользовательских паролей; выбор зависит от модели утечки.

# Как versioned ciphertext и crypto agility помогают безопасно менять алгоритмы и ключи?

Формат зашифрованной записи содержит однозначные version, algorithm suite и key reference вместе с необходимыми nonce, tag и metadata. Reader выбирает только поддерживаемую разрешённую схему; неизвестная версия не должна запускать небезопасный fallback.

Миграцию выполняют с совместимыми readers, новыми writers и проверяемым повторным шифрованием старых данных. Защищают metadata от подмены средствами выбранного формата, контролируют mixed versions и восстановление из backup. Crypto agility означает возможность управляемой замены, а не принятие algorithm, предложенного недоверенным input. Предпочитают проверенный формат и library. [OWASP: Key Management](https://cheatsheetseries.owasp.org/cheatsheets/Key_Management_Cheat_Sheet.html).

