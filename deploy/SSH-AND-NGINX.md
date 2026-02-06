# Подключение по SSH и настройка Nginx (подробно)

Пошаговая инструкция: как подключиться к VPS по SSH и как настроить Nginx с HTTPS и проксированием на приложение в Docker.

---

## Часть 1. Подключение по SSH

### Что понадобится

- **IP-адрес сервера** или домен (например `spontime.ru` или `123.45.67.89`)
- **Имя пользователя** (часто `root` или имя, которое вы задали при создании VPS)
- **Пароль** от сервера или **SSH-ключ** (если настроен)

Где взять данные на Timeweb: панель управления → ваш VPS → вкладка «Подключение» / «Доступ» (IP, логин, пароль или инструкция по ключу).

---

### Подключение с Windows

1. Откройте **командную строку** или **PowerShell**:
   - `Win + R` → введите `cmd` или `powershell` → Enter  
   - или в поиске Windows найдите «Командная строка» / «PowerShell»

2. Введите команду (подставьте свои данные):

   ```bash
   ssh имя_пользователя@IP_или_домен
   ```

   Примеры:
   - `ssh root@123.45.67.89`
   - `ssh root@spontime.ru`
   - `ssh ubuntu@spontime.ru`

3. При первом подключении появится вопрос про «authenticity of host» — введите **yes** и Enter.

4. Когда запросят пароль — введите пароль от сервера (при вводе символы не отображаются — это нормально) и нажмите Enter.

5. После входа вы увидите приглашение вроде `root@имя-сервера:~#` или `ubuntu@vps:~$`. Это значит, что вы **уже на VPS** — все дальнейшие команды выполняются на сервере.

**Выйти с сервера:** введите `exit` или нажмите Ctrl+D.

---

### Подключение с Mac или Linux

В терминале выполните ту же команду:

```bash
ssh имя_пользователя@IP_или_домен
```

Дальше — как в пунктах 3–5 выше.

---

## Часть 2. Настройка Nginx (HTTPS + прокси на Docker)

Считаем, что Docker уже установлен, проект клонирован, в корне проекта есть `.env`, контейнеры запущены и **фронт слушает порт 8080** (как в нашем проекте по умолчанию). Nginx на хосте будет принимать трафик на 80/443 и отдавать его на `127.0.0.1:8080`.

---

### Шаг 1. Установка Nginx и Certbot

Подключитесь по SSH и выполните:

```bash
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx
```

Проверка, что Nginx запущен:

```bash
sudo systemctl status nginx
```

Должно быть `active (running)`. Если нет — запустите:

```bash
sudo systemctl start nginx
sudo systemctl enable nginx
```

---

### Шаг 2. Домен должен указывать на сервер

В панели управления доменом (Timeweb или регистратор) должна быть **A-запись**:

- Имя: `@` (или пусто) для основного домена, при необходимости отдельно `www`
- Значение: **IP вашего VPS**
- TTL: по умолчанию или 300

Подождите 5–15 минут после сохранения. Проверить можно так (с вашего ПК):

```bash
ping ваш-домен.ru
```

Должен отвечать IP вашего VPS.

---

### Шаг 3. Конфиг Nginx: прокси на порт 8080

Сначала сделаем конфиг так, чтобы Nginx проксировал запросы на приложение в Docker (порт 8080). Потом выпустим сертификат.

Откройте конфиг по умолчанию:

```bash
sudo nano /etc/nginx/sites-available/default
```

**Замените весь содержимое файла** на конфиг ниже (подставьте свой домен вместо `spontime.ru`):

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name spontime.ru www.spontime.ru;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Сохраните: **Ctrl+O**, Enter, выход: **Ctrl+X**.

Проверка конфига:

```bash
sudo nginx -t
```

Должно быть: `syntax is ok` и `test is successful`. Затем перезагрузите Nginx:

```bash
sudo systemctl reload nginx
```

После этого по адресу **http://ваш-домен.ru** должна открываться ваша Mini App (через прокси на 8080).

---

### Шаг 4. Получение SSL-сертификата (HTTPS)

Выполните (подставьте свой домен):

```bash
sudo certbot --nginx -d spontime.ru -d www.spontime.ru
```

- Согласитесь с условиями (Y).
- Email можно указать или пропустить (Enter).
- Certbot сам изменит конфиг Nginx и добавит блок для порта 443 с сертификатами.

После успешного выполнения по адресу **https://ваш-домен.ru** будет открываться приложение по HTTPS.

---

### Шаг 5. Если Certbot уже был запущен раньше

Тогда у вас уже есть блок с `listen 443 ssl`. Нужно, чтобы **и в нём** запросы шли на 8080, а не на `root /var/www/...`.

Откройте конфиг:

```bash
sudo nano /etc/nginx/sites-available/default
```

Найдите **все** блоки `location / { ... }` (и для порта 80, и для 443). В каждом внутри `location /` должно быть только прокси, без `root` и `try_files`:

```nginx
location / {
    proxy_pass http://127.0.0.1:8080;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

Сохраните файл, затем:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

---

### Шаг 6. Проверка

1. В браузере откройте **https://ваш-домен.ru** — должна открываться Mini App.
2. В `.env` на сервере укажите `MINI_APP_URL=https://ваш-домен.ru` и `ADDITIONAL_CORS_ORIGINS=https://ваш-домен.ru`.
3. В BotFather укажите URL Mini App: **https://ваш-домен.ru**.

---

## Краткая шпаргалка

| Действие              | Команда |
|-----------------------|--------|
| Подключиться по SSH   | `ssh user@IP_или_домен` |
| Выйти с сервера       | `exit` |
| Редактировать конфиг  | `sudo nano /etc/nginx/sites-available/default` |
| Проверить Nginx       | `sudo nginx -t` |
| Перезагрузить Nginx   | `sudo systemctl reload nginx` |
| Выпустить/обновить SSL | `sudo certbot --nginx -d ваш-домен.ru` |

---

## Частые проблемы

- **502 Bad Gateway** — контейнер с приложением не запущен или не слушает 8080. Выполните на VPS: `cd ~/telegram-dating-app` и `docker compose ps`; при необходимости `docker compose up -d`.
- **Порт 80 занят** — контейнер фронта не должен занимать 80. В нашем проекте фронт по умолчанию на 8080; в `.env` не задавайте `FRONTEND_PORT=80`, если на хосте стоит Nginx.
- **Сертификат не выдаётся** — проверьте A-запись домена на IP сервера и что порт 80 открыт с интернета (файрвол на VPS и у хостера).
