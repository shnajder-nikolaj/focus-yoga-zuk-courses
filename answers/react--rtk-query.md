# Для чего нужен RTK Query?

RTK Query - инструмент из Redux Toolkit для получения, кэширования и синхронизации серверных данных.

Решает основные задачи:

- Автоматическая загрузка данных и управление состояниями `isLoading`, `isFetching`, `isError`
- Кэширование результатов и устранение дублирующихся запросов
- Автоматическое обновление данных после изменений на сервере
- Управление временем жизни кэша
- Поддержка polling, пагинации, optimistic updates и повторных запросов

RTK Query хранит кэш в Redux Store, избавляя от необходимости вручную создавать `thunk`, `slice` и `reducer` для большинства API-запросов.

# Что создаёт `createApi()`?

`createApi()` создаёт API slice - набор механизмов для управления серверными данными через Redux.

В результате создаются:

- Reducer - хранит кэш, результаты и состояния запросов
- Middleware - управляет запросами, подписками, инвалидацией и жизненным циклом кэша
- Endpoints - описания операций получения и изменения данных
- Actions и selectors - позволяют управлять запросами и читать кэш
- React hooks - автоматически генерируются при импорте `createApi` из `@reduxjs/toolkit/query/react`

Пример:

```
const api = createApi({
  reducerPath: 'api',
  baseQuery: fetchBaseQuery({ baseUrl: '/api' }),
  endpoints: (builder) => ({
    getUsers: builder.query({
      query: () => '/users',
    }),
  }),
});

export const { useGetUsersQuery } = api;
```

Для работы API slice необходимо зарегистрировать `api.reducer` и `api.middleware` в Redux Store.

`createApi()` только определяет инфраструктуру. Сам HTTP-запрос выполняется при запуске соответствующего endpoint.

# Чем `query` отличается от `mutation`?

`query` используется для получения и кэширования данных, а `mutation` - для операций, изменяющих состояние на сервере.

- `query` - обычно `GET`, автоматически выполняется при подписке компонента, использует общий кэш по аргументам.
- `mutation` - обычно `POST`, `PUT`, `PATCH`, `DELETE`, запускается через `trigger` и может инвалидировать связанные запросы.

Пример:

```
endpoints: (builder) => ({
  getUsers: builder.query({
    query: () => '/users',
  }),

  addUser: builder.mutation({
    query: (user) => ({
      url: '/users',
      method: 'POST',
      body: user,
    }),
  }),
});
```

Важно: различие определяется назначением операции, а не HTTP-методом. RTK Query не запрещает использовать `POST` внутри `query`.

# Как RTK Query определяет ключ кэша запроса?

RTK Query формирует `queryCacheKey` из имени endpoint и сериализованных аргументов запроса.

Например:

```
useGetUserQuery(1);
useGetUserQuery(2);
useGetUserQuery(1);
```

Здесь создаются две записи кэша:

- `getUser(1)`
- `getUser(2)`

Первый и третий вызовы используют одну запись кэша и разделяют результат запроса.

По умолчанию аргументы сериализуются с учётом стабильного порядка ключей обычных объектов:

```
useGetUsersQuery({ page: 1, limit: 10 });
useGetUsersQuery({ limit: 10, page: 1 });
```

Оба вызова используют одинаковый ключ.

Через `serializeQueryArgs` можно изменить стратегию формирования ключей.

Важно: ключ определяется аргументами endpoint, а не автоматически вычисляется из конечного URL.

# Что такое `providesTags` и `invalidatesTags`?

Это механизм автоматической инвалидации кэша.

- `providesTags` - указывает, какие теги предоставляет результат запроса.
- `invalidatesTags` - указывает, какие теги становятся неактуальными после операции.

Пример:

```
const api = createApi({
  baseQuery: fetchBaseQuery({ baseUrl: '/api' }),
  tagTypes: ['User'],

  endpoints: (builder) => ({
    getUsers: builder.query({
      query: () => '/users',
      providesTags: ['User'],
    }),

    addUser: builder.mutation({
      query: (user) => ({
        url: '/users',
        method: 'POST',
        body: user,
      }),
      invalidatesTags: ['User'],
    }),
  }),
});
```

После успешного `addUser` RTK Query инвалидирует кэш, предоставляющий тег `User`.

Если у соответствующего запроса есть активные подписчики, данные автоматически загружаются заново. Если подписчиков нет, запись удаляется из кэша.

Для точечной инвалидации используются теги с идентификаторами:

```
providesTags: (result, error, id) => [
  { type: 'User', id },
];

invalidatesTags: (result, error, { id }) => [
  { type: 'User', id },
];
```

Так можно обновлять данные конкретного пользователя, не затрагивая все остальные запросы.

# Когда использовать `refetchOnFocus` и `refetchOnReconnect`?

Эти настройки автоматически обновляют данные при определённых событиях.

`refetchOnFocus` - повторяет активные запросы, когда пользователь возвращается к окну приложения.

`refetchOnReconnect` - повторяет активные запросы после восстановления сетевого соединения.

Пример:

```
useGetUsersQuery(undefined, {
  refetchOnFocus: true,
  refetchOnReconnect: true,
});
```

Полезны для данных, которые могут измениться, пока пользователь не взаимодействует с приложением: уведомлений, заказов, статусов задач.

Для корректной работы необходимо подключить обработчики событий:

```
setupListeners(store.dispatch);
```

По умолчанию обе настройки отключены. Их можно задать глобально через `createApi()` или для отдельных вызовов хуков.

# Как работает `keepUnusedDataFor`?

`keepUnusedDataFor` определяет, сколько секунд RTK Query хранит запись кэша после исчезновения последнего подписчика.

По умолчанию - 60 секунд.

```
const api = createApi({
  baseQuery: fetchBaseQuery({ baseUrl: '/api' }),
  keepUnusedDataFor: 120,
  endpoints: () => ({}),
});
```

Механизм:

1. Компонент подписывается на запрос и получает данные.
2. После размонтирования последнего подписчика запускается таймер.
3. Если в течение 120 секунд появится новый подписчик, кэш будет переиспользован, а удаление отменено.
4. Если подписчиков не появится, запись кэша удаляется.

Важно: `keepUnusedDataFor` не определяет актуальность данных и не вызывает автоматическую повторную загрузку после истечения срока. Он управляет исключительно временем хранения неиспользуемого кэша.

# Чем `isLoading` отличается от `isFetching` в логике запроса?

Оба состояния указывают на загрузку, но имеют разный смысл.

- `isLoading` - запрос выполняется, и у хука ещё нет данных для отображения.
- `isFetching` - запрос выполняется прямо сейчас, независимо от наличия ранее загруженных данных.

Пример:

```
const { data, isLoading, isFetching } =
  useGetUsersQuery();
```

Первичная загрузка без кэша:

```
isLoading = true;
isFetching = true;
```

Повторная загрузка при наличии данных:

```
isLoading = false;
isFetching = true;
```

`isLoading` обычно используют для skeleton или основного индикатора загрузки.

`isFetching` - для индикатора фонового обновления, когда старые данные продолжают отображаться.

Дополнительно существует `currentData`, содержащий данные только для текущего аргумента запроса, тогда как `data` может временно содержать результат для предыдущего аргумента.

# Как использовать `skip` и `skipToken`?

Оба механизма позволяют условно отключать выполнение запроса.

`skip` - булевый параметр хука:

```
useGetUserQuery(userId, {
  skip: userId == null,
});
```

Пока `skip: true`, запрос не выполняется автоматически.

`skipToken` - специальное значение, которое передаётся вместо аргумента:

```
import { skipToken } from '@reduxjs/toolkit/query';

useGetUserQuery(userId ?? skipToken);
```

Особенно полезен с TypeScript, когда endpoint ожидает обязательный аргумент, а значение пока отсутствует.

При отключении запроса не создаётся активная подписка на соответствующую запись кэша. Уже сохранённые данные при этом не обязательно удаляются.

# Когда нужен lazy query hook?

Lazy query используется, когда запрос должен запускаться вручную, а не автоматически при монтировании компонента.

Например, после нажатия кнопки, выбора фильтра или подтверждения действия.

```
const [getUser, { data, isFetching, error }] =
  useLazyGetUserQuery();

const handleClick = () => {
  getUser(123);
};
```

Хук возвращает:

- `trigger` - функцию запуска запроса
- `result` - результат и состояния запроса
- `lastPromiseInfo` - информацию об аргументе последнего запуска

По умолчанию вызов `trigger(arg)` инициирует запрос, даже если данные уже есть в кэше. Для предпочтительного использования кэшированного результата можно передать второй аргумент `true`:

```
getUser(123, true);
```

Отличие от `skip`: `skip` управляет выполнением декларативного запроса через состояние компонента, а lazy query предоставляет прямой императивный запуск.

# Как реализовать optimistic update через `onQueryStarted`?

Optimistic update - обновление интерфейса до получения подтверждения от сервера.

Это позволяет мгновенно показывать результат пользовательского действия.

Пример:

```
updateUser: builder.mutation({
  query: ({ id, ...data }) => ({
    url: `/users/${id}`,
    method: 'PATCH',
    body: data,
  }),

  async onQueryStarted(
    { id, ...data },
    { dispatch, queryFulfilled }
  ) {
    const patch = dispatch(
      api.util.updateQueryData(
        'getUser',
        id,
        (draft) => {
          Object.assign(draft, data);
        }
      )
    );

    try {
      await queryFulfilled;
    } catch {
      patch.undo();
    }
  },
});
```

Механизм:

1. `onQueryStarted` вызывается при запуске мутации.
2. `updateQueryData` немедленно изменяет кэш.
3. Подписанные компоненты отображают обновлённые данные.
4. `queryFulfilled` ожидает результат серверного запроса.
5. При ошибке `patch.undo()` откатывает изменения.

Подводный камень: при нескольких одновременно выполняющихся мутациях откат патчей может привести к конфликтам. В таких случаях безопаснее инвалидировать соответствующие теги и повторно загрузить данные с сервера.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://redux-toolkit.js.org\&sz=32)

Redux+1



# Что делают `updateQueryData` и `upsertQueryData`?

Оба метода позволяют вручную управлять кэшем RTK Query через `api.util`.

`updateQueryData` - изменяет существующую запись кэша.

```
dispatch(
  api.util.updateQueryData('getUser', 1, (draft) => {
    draft.name = 'Alex';
  })
);
```

Особенности:

- Работает только с существующей записью кэша.
- Использует Immer для удобного изменения данных.
- Возвращает патчи и метод `undo()` для отката.

`upsertQueryData` - создаёт новую запись кэша или полностью заменяет существующую.

```
dispatch(
  api.util.upsertQueryData('getUser', 1, {
    id: 1,
    name: 'Alex',
  })
);
```

Основное различие:

- `updateQueryData` - частичное изменение существующих данных.
- `upsertQueryData` - создание или полная замена данных.

Оба метода работают с конкретной записью, определяемой именем endpoint и его аргументами.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://redux-toolkit.js.org\&sz=32)

Redux+1



# Как работает polling?

Polling - периодическое выполнение запроса для получения актуальных данных.

В RTK Query настраивается через `pollingInterval` в миллисекундах.

```
useGetNotificationsQuery(undefined, {
  pollingInterval: 5000,
});
```

Запрос будет повторяться примерно каждые 5 секунд, пока polling активен.

Дополнительно можно приостанавливать опрос, когда окно приложения неактивно:

```
useGetNotificationsQuery(undefined, {
  pollingInterval: 5000,
  skipPollingIfUnfocused: true,
});
```

Для `skipPollingIfUnfocused` необходим `setupListeners(store.dispatch)`.

Polling работает через механизм подписок и прекращается, когда больше нет подписчиков, требующих периодического обновления.

Используется для статусов задач, уведомлений и мониторинга. В отличие от WebSocket или SSE, polling создаёт регулярные HTTP-запросы, даже если данные не изменились.

# Как настроить `fetchBaseQuery` и централизованную обработку ошибок?

`fetchBaseQuery` - стандартная обёртка над `fetch`, предоставляемая RTK Query.

Позволяет настроить базовый URL, заголовки, параметры запросов и обработку HTTP-ответов.

Пример:

```
const baseQuery = fetchBaseQuery({
  baseUrl: '/api',

  prepareHeaders: (headers, { getState }) => {
    const token = getState().auth.accessToken;

    if (token) {
      headers.set('authorization', `Bearer ${token}`);
    }

    return headers;
  },
});
```

Для централизованной обработки ошибок существует два основных подхода.

1\. Обёртка над `baseQuery`.

Позволяет анализировать ответ и выполнять общую логику:

```
const baseQueryWithErrors = async (
  args,
  api,
  extraOptions
) => {
  const result = await baseQuery(
    args,
    api,
    extraOptions
  );

  if (result.error?.status === 401) {
    api.dispatch(logout());
  }

  return result;
};
```

2\. Redux middleware.

Можно перехватывать отклонённые RTK Query actions через `isRejectedWithValue` и централизованно показывать уведомления или логировать ошибки.

Различие: обёртка `baseQuery` работает непосредственно с результатами запросов, а middleware обрабатывает Redux actions.

Важно возвращать исходный `result`, чтобы RTK Query корректно обновлял состояния запроса.

# Как реализовать повтор запроса после обновления access token?

Для этого создаётся кастомная обёртка над `fetchBaseQuery`, реализующая механизм refresh token.

Алгоритм:

1. Отправить исходный запрос с текущим access token.
2. Если сервер вернул `401 Unauthorized`, запросить новый access token.
3. При успешном обновлении сохранить новый токен.
4. Повторить исходный запрос с новым токеном.
5. Если refresh token недействителен, завершить авторизованную сессию.

Пример:

```
const rawBaseQuery = fetchBaseQuery({
  baseUrl: '/api',
  prepareHeaders: (headers, { getState }) => {
    const token = getState().auth.accessToken;

    if (token) {
      headers.set('authorization', `Bearer ${token}`);
    }

    return headers;
  },
});

const baseQueryWithReauth = async (
  args,
  api,
  extraOptions
) => {
  let result = await rawBaseQuery(args, api, extraOptions);

  if (result.error?.status === 401) {
    const refresh = await rawBaseQuery(
      { url: '/auth/refresh', method: 'POST' },
      api,
      extraOptions
    );

    if (refresh.data) {
      api.dispatch(setCredentials(refresh.data));

      result = await rawBaseQuery(
        args,
        api,
        extraOptions
      );
    } else {
      api.dispatch(logout());
    }
  }

  return result;
};
```

Пример предполагает, что endpoint обновления токена настроен на сервере, а функции `setCredentials` и `logout` определены в приложении.

Важный нюанс - параллельные запросы. Если несколько запросов одновременно возвращают `401`, каждый может попытаться обновить токен.

Для решения используют `Mutex` или единый Promise обновления токена: пока refresh выполняется, остальные запросы ожидают его результата.

Также нужно исключить бесконечные попытки обновления и очищать приватный кэш при выходе пользователя из системы.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://redux-toolkit.js.org\&sz=32)

Redux



# Как делать пагинацию и infinite loading в RTK Query?

Существует два основных подхода.

1\. Обычная пагинация через `query`.

Номер страницы передаётся в аргументах запроса:

```
getUsers: builder.query({
  query: (page) => `/users?page=${page}`,
});
```

Использование:

```
const [page, setPage] = useState(1);

const { data } = useGetUsersQuery(page);
```

Каждая страница получает отдельную запись кэша, поскольку имеет собственный `queryCacheKey`.

Подходит для интерфейсов с переключением между страницами.

2\. Infinite loading через `infiniteQuery`.

Начиная с RTK Query 2.6 появилась встроенная поддержка infinite queries.

```
getUsers: builder.infiniteQuery({
  query: ({ pageParam }) =>
    `/users?page=${pageParam}`,

  infiniteQueryOptions: {
    initialPageParam: 1,

    getNextPageParam: (
      lastPage,
      allPages,
      lastPageParam
    ) =>
      lastPage.hasMore
        ? lastPageParam + 1
        : undefined,
  },
});
```

Использование:

```
const {
  data,
  fetchNextPage,
  hasNextPage,
  isFetchingNextPage,
} = useGetUsersInfiniteQuery();

const users = data?.pages.flatMap(
  (page) => page.users
) ?? [];
```

Здесь предполагается, что сервер возвращает объект `{ users, hasMore }`.

Особенности:

- Все загруженные страницы хранятся в одной записи кэша.
- `fetchNextPage()` загружает следующую страницу.
- `hasNextPage` показывает, доступна ли следующая страница.
- `data.pages` содержит результаты отдельных страниц.
- `maxPages` позволяет ограничить число страниц, сохраняемых в кэше.

Infinite queries поддерживают как page-based, так и cursor-based пагинацию. По умолчанию при повторном обновлении последовательно перезапрашиваются все сохранённые страницы.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://redux-toolkit.js.org\&sz=32)

Redux



# Как устроена подписка компонентов на результаты запроса?

RTK Query использует подписки на записи кэша, определяемые комбинацией endpoint и аргументов.

Когда компонент вызывает:

```
const { data } = useGetUserQuery(1);
```

RTK Query:

1. Формирует `queryCacheKey` для `getUser(1)`.
2. Проверяет наличие данных в кэше.
3. При необходимости отправляет запрос.
4. Создаёт подписку компонента на соответствующую запись.
5. Уведомляет компонент об изменениях результата через Redux и React-Redux.

Если другой компонент вызывает тот же запрос:

```
useGetUserQuery(1);
```

Он получает данные из того же кэша. Второй сетевой запрос обычно не требуется.

RTK Query учитывает количество активных подписок:

- Пока есть хотя бы один подписчик, запись сохраняется в кэше.
- Когда исчезает последний подписчик, запускается таймер `keepUnusedDataFor`.
- Если новый подписчик появляется до истечения таймера, кэш переиспользуется.
- Когда таймер заканчивается, запись удаляется.

Для оптимизации перерисовок можно использовать `selectFromResult`, чтобы компонент реагировал только на изменения выбранной части результата.

# В чём различие RTK Query и TanStack Query?

Обе библиотеки решают похожие задачи: загрузка, кэширование, синхронизация и обновление серверных данных.

Главное различие - архитектура и интеграция с управлением состоянием.

RTK Query:

- Входит в Redux Toolkit и хранит кэш в Redux Store.
- Использует централизованное описание API через `createApi`.
- Автоматически генерирует типизированные React hooks.
- Поддерживает инвалидацию кэша через `providesTags` и `invalidatesTags`.
- По умолчанию не повторяет неудачные запросы автоматически, но поддерживает настраиваемый `retry`.

TanStack Query:

- Работает независимо от Redux, используя собственный `QueryClient` и кэш.
- Позволяет определять запросы непосредственно через `useQuery`, `queryKey` и `queryFn`.
- Использует `staleTime` для определения актуальности данных и `gcTime` для удаления неиспользуемого кэша.
- Поддерживает автоматические повторные запросы при ошибках.
- Имеет адаптеры для разных UI-фреймворков, не ограничиваясь React.

Ключевое различие в работе с кэшем:

RTK Query использует инвалидацию по тегам и преимущественно централизованное управление endpoints.

TanStack Query использует query keys, `invalidateQueries` и гибкие настройки актуальности данных.

При этом обе библиотеки поддерживают пагинацию, infinite queries, optimistic updates, polling и фоновую повторную загрузку.

Что выбирать:

- RTK Query - когда приложение уже использует Redux Toolkit и требуется тесная интеграция API с Redux.
- TanStack Query - когда нужен независимый от Redux инструмент для серверного состояния с гибким управлением запросами.

Обе библиотеки используют документный кэш для результатов отдельных запросов, а не автоматически нормализованный кэш сущностей.

[image](https://www.google.com/s2/favicons?domain=https://redux-toolkit.js.org\&sz=32)

Redux+2

Источники:

- [Redux Toolkit - RTK Query Overview](https://redux.js.org/toolkit/rtk-query/overview?utm_source=chatgpt.com)
- [Redux Toolkit - Queries](https://redux.js.org/toolkit/rtk-query/usage/queries?utm_source=chatgpt.com)
- [Redux Toolkit - Cache Behavior](https://redux.js.org/toolkit/rtk-query/usage/cache-behavior?utm_source=chatgpt.com)
- [Redux Toolkit - Infinite Queries](https://redux.js.org/toolkit/rtk-query/usage/infinite-queries?utm_source=chatgpt.com)
- [TanStack Query - Overview](https://tanstack.com/query/latest/docs/framework/react/overview?utm_source=chatgpt.com)