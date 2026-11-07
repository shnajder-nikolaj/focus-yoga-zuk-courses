# Как логический порядок обработки SELECT влияет на WHERE, GROUP BY, HAVING и window functions?

Упрощённый логический порядок: `FROM/JOIN`, `WHERE`, группировка и aggregates, `HAVING`, window calculations, формирование `SELECT`, `DISTINCT`, `ORDER BY`, ограничение результата. Это модель смысла запроса, а не обязательный порядок физического выполнения planner.

`WHERE` фильтрует исходные строки, `HAVING` — результаты группировки, а window function видит строки после этих этапов. Поэтому результат `ROW_NUMBER()` в PostgreSQL фильтруют внешним запросом или CTE; некоторые другие СУБД имеют `QUALIFY`. Доступность aliases тоже зависит от clause и диалекта.

# Как INNER, LEFT, CROSS и SELF JOIN влияют на состав и кратность результата?

`INNER JOIN` оставляет совпавшие пары; `LEFT JOIN` дополнительно сохраняет строки слева без совпадения, дополняя правые поля `NULL`. `CROSS JOIN` формирует декартово произведение. `SELF JOIN` соединяет таблицу с собой под разными aliases и может использовать те же join types.

Результат имеет кратность совпадений. Один customer с тремя orders даёт три строки; два независимых one-to-many joins могут перемножить количество. До aggregation определяют требуемый уровень детализации и при необходимости предварительно группируют дочерние данные. `DISTINCT` не должен маскировать неверно построенную связь.

# Почему перенос условия между ON и WHERE меняет смысл LEFT JOIN?

`ON` определяет, какие правые строки подходят до дополнения отсутствующих совпадений. `WHERE` отбирает строки уже после join. Если условие правой таблицы отвергает `NULL`, оно может удалить customers без подходящего order.

```sql
SELECT c.id, o.id
FROM customers c
LEFT JOIN orders o
  ON o.customer_id = c.id AND o.status = 'open';
```

Так сохраняются все customers. При переносе `o.status = 'open'` в `WHERE` останутся только строки с открытым order. Это полезно различать при отчётах «все клиенты и их подходящие заказы». [PostgreSQL: Table Expressions](https://www.postgresql.org/docs/current/queries-table-expressions.html).

# Как NULL влияет на NOT IN, NOT EXISTS и поиск отсутствующих связанных строк?

SQL использует трёхзначную логику: сравнение с `NULL` обычно даёт `UNKNOWN`, а `WHERE` оставляет только `TRUE`. Если множество для `NOT IN` содержит `NULL`, отсутствие равного значения может дать `UNKNOWN` вместо ожидаемого `TRUE`.

Для поиска клиентов без заказов удобно выразить отсутствие через `NOT EXISTS`:

```sql
SELECT c.id
FROM customers c
WHERE NOT EXISTS (
  SELECT 1 FROM orders o WHERE o.customer_id = c.id
);
```

Если сама связь допускает `NULL`, её бизнес-смысл определяют явно. Механическая замена операторов не решает неопределённость данных. [Subquery Expressions](https://www.postgresql.org/docs/current/functions-subquery.html).

# Чем COUNT(*), COUNT(column), DISTINCT и условные агрегаты отличаются при группировке?

`COUNT(*)` считает строки группы, а `COUNT(column)` — только строки с ненулевым значением column. `COUNT(DISTINCT column)` считает различные non-NULL значения. После `LEFT JOIN` это различие важно: строка без дочернего объекта всё равно участвует в `COUNT(*)`.

Условный aggregate считает или суммирует только подходящие значения через `CASE`, а в поддерживающих СУБД — через `FILTER`. `WHERE` уменьшает исходный набор, `HAVING` проверяет результат группы. На пустом входе `COUNT` возвращает ноль, а многие другие aggregates, включая `SUM`, — `NULL`; при необходимости применяют `COALESCE`.

# Когда использовать correlated subquery, EXISTS или JOIN без случайного дублирования строк?

`EXISTS` отвечает на вопрос о наличии совпадения и не размножает строку внешнего набора, даже если совпадений много. `JOIN` нужен, когда требуются данные связанных строк и их кратность. Correlated subquery ссылается на текущие значения внешнего запроса и удобен для per-row условий или вычислений.

Нельзя автоматически считать correlated subquery медленным, а join быстрым: planner может преобразовать их в похожие планы. Проверяют cardinality и реальный plan. Scalar subquery обычно должен вернуть не более одной строки; случайное множество совпадений является ошибкой, а не способом выбрать любую строку. [Subquery Expressions](https://www.postgresql.org/docs/current/functions-subquery.html).

# Как CTE и recursive CTE организуют запрос и почему материализация зависит от СУБД?

**CTE** именует промежуточное выражение через `WITH`, помогая разделить сложную логику. Recursive CTE содержит исходную часть и шаг, использующий предыдущий результат; нужны корректное условие завершения и обработка возможных циклов.

CTE не означает обязательную временную таблицу или гарантированное ускорение. В современных PostgreSQL подходящий non-recursive, side-effect-free CTE может быть встроен в основной запрос, а материализацию можно регулировать в поддерживаемых случаях. В других СУБД правила и hints отличаются. Решение принимают по plan и повторному использованию результата, а не по одному синтаксису `WITH`. [PostgreSQL: WITH Queries](https://www.postgresql.org/docs/current/queries-with.html).

# Как ROW_NUMBER, RANK и DENSE_RANK решают задачи top-N и обработки равных значений?

`ROW_NUMBER` присваивает каждой строке отдельный номер. `RANK` присваивает равным значениям общий ранг с пропусками далее, а `DENSE_RANK` — общий ранг без пропусков. Для scores `100, 100, 90` получатся соответственно номера `1, 2, 3`, ранги `1, 1, 3` и dense ranks `1, 1, 2`.

Top-N строк и top-N уровней результата — разные задачи. Для детерминированного `ROW_NUMBER` добавляют tie-breaker. Если добавить уникальный ID в порядок `RANK`, равенство строк по score перестанет определять peers, что может изменить требуемый результат. [Window Functions](https://www.postgresql.org/docs/current/functions-window.html).

# Как PARTITION BY, ORDER BY и window frame меняют SUM и LAST_VALUE?

`PARTITION BY` делит строки на независимые группы, не сворачивая их как `GROUP BY`. Оконный `ORDER BY` задаёт порядок внутри partition, а **frame** — часть partition, используемую конкретным вычислением. `ROWS` работает с позициями строк; `RANGE` учитывает значения сортировки и peers.

При `ORDER BY` default frame в PostgreSQL заканчивается на последнем peer текущей строки, поэтому `SUM` часто даёт накопление, а `LAST_VALUE` — не последний результат всей partition. Для последнего значения всей группы явно задают `ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING`. Итоговый порядок выдачи задаётся внешним `ORDER BY`. [Window Functions](https://www.postgresql.org/docs/current/functions-window.html).

# Как написать keyset pagination с устойчивым ORDER BY и составным cursor?

Cursor хранит все значения устойчивого порядка, включая уникальный tie-breaker. Для PostgreSQL, non-NULL `created_at` и уникального `id` следующая страница при убывающем порядке выглядит так:

```sql
SELECT id, created_at
FROM orders
WHERE (created_at, id) < ($1, $2)
ORDER BY created_at DESC, id DESC
LIMIT $3;
```

Нужен подходящий composite index. Для смешанных направлений и `NULL` predicate строят отдельно по правилам диалекта. Cursor связывают с filters и scope доступа. Изменение sort key между страницами всё ещё может менять состав результата; keyset pagination не создаёт snapshot автоматически.

