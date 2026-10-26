# Исследованные проекты и API

Проверено 2026-10-26. Документация MA на момент проверки показывала 2.10.8. Ссылки на main/dev отражают исследованные контракты, а не закреплённую матрицу совместимости; версии пользовательской установки ещё неизвестны.

| Источник | Вывод для проекта |
|---|---|
| [MA Yandex Station](https://www.music-assistant.io/player-support/yandex-station/) | Есть локальный провайдер, Lite указан среди поддерживаемых устройств. Требуется доступность MA со станции. Используем его; экспериментальные режимы отключены. |
| [Код MA Yandex Station](https://github.com/music-assistant/server/tree/main/music_assistant/providers/yandex_station) | Провайдер работает через Glagol; реализация опирается на AlexxIT. Нет необходимости дублировать протокол в начальном проекте. |
| [AlexxIT/YandexStation](https://github.com/AlexxIT/YandexStation) | Альтернативная интеграция HA с локальным проигрыванием медиа. Не является доказанным источником произвольных ASR-текстов. |
| [Glagol client AlexxIT](https://github.com/AlexxIT/YandexStation/blob/master/custom_components/yandex_station/core/yandex_glagol.py) | Видны токен устройства, WebSocket и vinsResponse; ответ на команду нельзя приравнять к пассивному ASR-потоку. |
| [MA YouTube Music](https://www.music-assistant.io/music-providers/youtube-music/) | Неофициальный best-effort доступ; настройки авторизации принадлежат MA. |
| [MA search](https://www.music-assistant.io/faq/masssearch/) | Поиск глобальный, поэтому проверяем происхождение URI. |
| [MA server PR #5605](https://github.com/music-assistant/server/pull/5605) | Обновляет Yandex Station provider с 1.5.1 до 1.5.22 и добавляет `audio_play` для совместимости с новой прошивкой; milestone 2.11.0. |
| [HA service implementation](https://github.com/home-assistant/core/blob/dev/homeassistant/components/music_assistant/services.py) | Search принимает config_entry_id, name, media_type, limit, library_only и требует ответ. |
| [HA response schema](https://github.com/home-assistant/core/blob/dev/homeassistant/components/music_assistant/schemas.py) | Track содержит name/uri; provider mappings не передаются в обычном результате search. |
| [HA REST API](https://contributors.home-assistant.io/core/internals/rest-api/) | Bearer auth, services POST, return_response для search. |

Контракт реализации:

1. GET `/api/services`, GET `/api/states/{entity_id}` — предварительная проверка.
2. POST `/api/services/music_assistant/search?return_response` — извлечь `service_response.tracks`.
3. Оставить только URI выбранного YouTube Music provider и тип track.
4. Только при `--execute`: POST `/api/services/music_assistant/play_media`, поля `entity_id`, `media_id`, `media_type=track`, `enqueue=replace`.

Прямого документированного read-only API Quasar для ASR в исследованных источниках не найдено. Это не доказательство отсутствия такого источника; H1 проверяется на устройстве отдельно.
