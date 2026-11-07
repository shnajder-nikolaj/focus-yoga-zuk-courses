# Как Pod network и CNI обеспечивают адресацию и связь между Pods на разных узлах?

В обычной модели Kubernetes каждый Pod получает сетевую identity и IP в сети кластера; containers одного Pod разделяют network namespace, ports и loopback. **CNI plugin** настраивает интерфейсы, адреса и связь с остальной сетью совместно с используемым dataplane.

Реализация может применять routing или overlay; конкретные MTU, encapsulation и ограничения зависят от plugin и платформы. Связь между nodes требует корректной инфраструктурной сети. Kubernetes API сам по себе не прокладывает пакеты, а наличие IP у Pod не подтверждает доступность маршрута до него.

# Как Service selectors и EndpointSlices связывают стабильный адрес с backend Pods?

**Service** с selector выбирает Pods по labels, а controllers формируют соответствующие **EndpointSlices** с адресами, портами и условиями endpoints. Service даёт устойчивую точку доступа, хотя сами Pods и их IP меняются.

Неверный selector, несовпадение named port или неготовность Pods могут оставить Service без подходящего backend. Service без selector тоже возможен, но endpoints для него должны появиться предусмотренным способом. Проверяют состав EndpointSlices и readiness, а не только существование объекта Service: виртуальный адрес без доступного backend не обслужит приложение.

# Чем ClusterIP, NodePort, LoadBalancer и ExternalName различаются по маршруту запроса?

**ClusterIP** предоставляет обычный виртуальный адрес Service внутри кластера. **NodePort** дополнительно предоставляет port на nodes по правилам реализации и маршрутизирует к backends. **LoadBalancer** запрашивает внешнюю точку доступа у установленной cloud/controller-интеграции; без неё внешний адрес может не появиться.

**ExternalName** возвращает DNS alias на другое имя и не является обычным proxy с EndpointSlices. Из-за смены DNS-имени возможны особенности HTTP Host и TLS hostname. Ни один тип сам по себе не добавляет authentication приложения и не отменяет firewall или network policy. [Service types](https://kubernetes.io/docs/concepts/services-networking/service/#publishing-services-service-types).

# Как port, targetPort и nodePort соотносятся с портом контейнерного процесса?

`port` — порт Service для клиента. `targetPort` — порт backend Pod, числовой или разрешаемый по имени container port. `nodePort`, когда используется, — отдельный port доступа через node.

Например, Service `port: 80` может вести на процесс `targetPort: 8080`, а NodePort предоставлять внешний entry на другом номере. Объявление `containerPort` не запускает listener и само по себе не публикует его снаружи. Проверяют protocol и адрес, на котором слушает процесс: listener только на loopback Pod может быть недоступен по Pod IP.

# Как headless Service и cluster DNS помогают обнаруживать отдельные экземпляры?

У **headless Service** `clusterIP: None`, поэтому обычный виртуальный Service IP не создаётся. Для подходящих backends DNS может возвращать адреса отдельных Pods, позволяя клиенту самостоятельно выбирать экземпляр. Это удобно для discovery stateful-систем.

Готовность endpoints и `publishNotReadyAddresses` влияют на публикацию адресов. В StatefulSet отдельные Pods могут иметь стабильные DNS-имена при соответствующей конфигурации. DNS cache и connection pools должны переживать смену IP. Headless Service не делает client автоматически устойчивым к отказам и не предоставляет обычную серверную балансировку virtual IP.

# Как kube-proxy или альтернативный dataplane реализует маршрутизацию Service?

**Kube-proxy** наблюдает Services и endpoints и настраивает host dataplane для Service routing, например через поддерживаемые правила packet processing. Трафик может направляться к backend с использованием NAT и connection tracking.

Альтернативный dataplane, например eBPF-based, способен реализовать эту роль без обычного kube-proxy. Конкретные режимы и ограничения зависят от версии и plugin. Kube-proxy не является обязательным пользовательским HTTP reverse proxy на пути каждого запроса. Для диагностики различают правила маршрутизации, реальные endpoints, conntrack и инфраструктурную связность.

# Как Ingress resource, Ingress controller и IngressClass разделяют описание и реализацию L7 routing?

**Ingress resource** описывает HTTP(S) routing, например host и path к backend Service. **Ingress controller** реализует эти правила в proxy или load balancer; **IngressClass** связывает ресурс с нужной реализацией и её параметрами.

Один YAML Ingress без controller не создаёт работающую внешнюю точку доступа. Annotations и дополнительные функции зависят от реализации, поэтому переносимость ограничена. Проверяют class, listener, TLS Secret, правила host/path и фактический адрес. Обычный Ingress API не является универсальным описанием любого TCP/UDP routing. [Ingress](https://kubernetes.io/docs/concepts/services-networking/ingress/).

# Как GatewayClass, Gateway и HTTPRoute разделяют ответственность в Gateway API?

**GatewayClass** определяет класс инфраструктурной реализации controller. **Gateway** описывает конкретную точку приёма трафика и listeners. **HTTPRoute** задаёт правила приложения и привязку к разрешённому Gateway.

Так разделяются обязанности platform team и владельцев приложений. Межnamespace-связи регулируются отдельными механизмами: `allowedRoutes` управляет подключением routes к Gateway, а `ReferenceGrant` разрешает предусмотренные ссылки, например на backend другого namespace. Нужны установленные API resources и controller с поддержкой выбранных features; наличие CRD само по себе не обеспечивает routing. [Gateway API](https://kubernetes.io/docs/concepts/services-networking/gateway/).

# Как TLS termination, passthrough и шифрование до backend меняют границы доверия?

При **TLS termination** внешний TLS заканчивается на gateway или proxy, который видит HTTP. До backend может идти plaintext либо новое отдельное TLS-соединение. Для последнего проверяют certificate, доверенный CA и hostname, иначе шифрование не подтверждает identity нужного сервиса.

**Passthrough** передаёт TLS дальше без расшифрования на этой точке и ограничивает доступный там анализ HTTP; маршрутизация может опираться на поддерживаемые L4/SNI-механизмы. Возможности зависят от controller и route types. mTLS добавляет аутентификацию сторон, а NetworkPolicy решает другую задачу — сетевую доступность.

# Как NetworkPolicy ограничивает ingress и egress и от чего зависит её исполнение?

Обычная **NetworkPolicy** задаёт разрешённые ingress или egress связи для выбранных Pods на поддерживаемом plugin уровне. Без выбирающей Pod изолирующей policy направление обычно остаётся разрешённым; несколько policies складывают разрешения, а не задают порядок deny/allow.

Для соединения должны разрешать и исходящий доступ источника, и входящий доступ назначения, если соответствующие стороны изолированы. Policy object без поддерживающего enforcement не блокирует трафик. При default-deny учитывают DNS и служебные зависимости. Стандартная NetworkPolicy не является общей HTTP authorization policy и не предоставляет сама TLS. [Network policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/).

# Как externalTrafficPolicy, session affinity и длительные соединения влияют на балансировку?

`externalTrafficPolicy: Local` направляет соответствующий внешний трафик к локальным endpoints node и может сохранять исходный client IP, но создаёт требования к наличию backends и внешнему load balancer health checking. `Cluster` допускает routing к endpoints других nodes, с иными последствиями для пути и source address.

**Session affinity**, например ClientIP, закрепляет выбор по правилам Service, но не гарантирует вечную доступность выбранного Pod. Длительное соединение обычно сохраняет backend до закрытия: добавление replicas не перераспределяет уже открытые соединения автоматически. Оценивают баланс по соединениям, запросам и реальной работе.

# Как последовательно диагностировать DNS, Service, endpoints и сетевые политики при недоступности приложения?

Сначала проверяют, запущен ли процесс, правильный ли port и доступен ли backend по Pod IP. Затем — selector Service, targetPort, ready EndpointSlices и доступ по ClusterIP. Если IP работает, а имя нет, изучают DNS, namespace, search domains и policy для DNS-трафика.

Далее проверяют ingress/egress policies, CNI, node routing, MTU и firewall. Для внешнего доступа добавляют load balancer, Gateway/Ingress, TLS и host/path rules. Проверку выполняют из того же сетевого контекста, где возникает ошибка; успех с рабочего ноутбука не подтверждает связь между двумя Pods.
