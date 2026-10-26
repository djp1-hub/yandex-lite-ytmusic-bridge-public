# Установка на Linux с systemd

Сервер должен находиться в одной локальной сети с Home Assistant и станцией. Нужны
Linux с systemd, Python 3.9+, `git`, `adb`, root ADB на станции и Music Assistant
2.11+ с настроенными YouTube Music и Yandex Station providers.

## 1. Установить системные пакеты

Для Debian/Ubuntu:

```sh
sudo apt-get update
sudo apt-get install -y adb git python3
```

Проверить доступ к станции:

```sh
adb connect STATION_IP:5555
adb -s STATION_IP:5555 shell getprop ro.product.model
```

## 2. Установить код

```sh
sudo useradd --system \
  --home /var/lib/yandex-lite-ytmusic-bridge \
  --shell /usr/sbin/nologin ytmusic-bridge

sudo git clone https://github.com/OWNER/yandex-lite-ytmusic-bridge.git \
  /opt/yandex-lite-ytmusic-bridge
sudo chown -R root:root /opt/yandex-lite-ytmusic-bridge
sudo chmod 755 /opt/yandex-lite-ytmusic-bridge/scripts/run_voice_bridge.sh
```

Если пользователь уже существует, сообщение `useradd: user ... already exists`
можно проигнорировать.

## 3. Настроить Home Assistant и Music Assistant

```sh
sudo install -d -o root -g ytmusic-bridge -m 750 \
  /etc/yandex-lite-ytmusic-bridge
sudo install -o root -g ytmusic-bridge -m 640 \
  /opt/yandex-lite-ytmusic-bridge/deploy/systemd/config.env.example \
  /etc/yandex-lite-ytmusic-bridge/config.env
sudo editor /etc/yandex-lite-ytmusic-bridge/config.env
```

Заполнить:

- `HA_URL` — адрес Home Assistant без завершающего пути;
- `STATION_ADB_SERIAL` — `IP:5555` станции;
- `MA_CONFIG_ENTRY_ID` — ID записи интеграции Music Assistant в HA;
- `MA_PLAYER_ENTITY` — сущность станции, созданная интеграцией MA;
- `STATION_NATIVE_ENTITY` — сущность AlexxIT/Yandex Station, если она установлена;
- `YT_PROVIDER` — точный регистрозависимый instance ID YouTube Music из URI
  результата MA, например `ytmusic--AbC123`.

Создать в профиле Home Assistant отдельный долгосрочный токен. Вставить его в
файл одной строкой, без `HA_TOKEN=`:

```sh
sudo install -o root -g ytmusic-bridge -m 640 /dev/null \
  /etc/yandex-lite-ytmusic-bridge/ha_token
sudo editor /etc/yandex-lite-ytmusic-bridge/ha_token
```

Токен нельзя добавлять в Git, аргументы команд или журналы.

## 4. Включить службу

```sh
sudo install -o root -g root -m 644 \
  /opt/yandex-lite-ytmusic-bridge/deploy/systemd/yandex-lite-ytmusic-bridge.service \
  /etc/systemd/system/yandex-lite-ytmusic-bridge.service
sudo systemctl daemon-reload
sudo systemctl enable --now yandex-lite-ytmusic-bridge.service
```

Проверка:

```sh
systemctl status yandex-lite-ytmusic-bridge.service
journalctl -u yandex-lite-ytmusic-bridge.service -f
```

Произнесите: «Алиса, включи Noize MC Страна дождей». После возврата Алисы в
`IDLE` служба найдёт трек в YouTube Music и заменит очередь MA.

## Обновление

```sh
cd /opt/yandex-lite-ytmusic-bridge
sudo git pull --ff-only
sudo systemctl restart yandex-lite-ytmusic-bridge.service
```

Для удаления остановить и отключить службу, удалить unit, код и конфигурацию.
Удаление `/etc/yandex-lite-ytmusic-bridge/ha_token` необратимо; при необходимости
сначала отозвать токен в профиле Home Assistant.
