url - https://foodgram31.ddns.net

admin profile:
  - email - test@mail.com
  - password - Test77.


# Foodgram - сайт с рецептами на любой вкус

---

## В Foodgram'е можно:
- Добавить свой рецепт
- Просматривать рецепты других пользователей
- Собирать корзину из рецептов и скачивать все ингредиенты

### Опробовать → [тык](https://foodgram31.ddns.net)

---

## Как запустить проект

#### Установить docker:

```bash
sudo apt update
sudo apt install curl
curl -fSL https://get.docker.com -o get-docker.sh
sudo sh ./get-docker.sh
sudo apt install docker-compose-plugin 
```

> Проверить статус:
> ```bash
> sudo systemctl status docker
> ```

#### Установить nginx:
```bash
sudo apt install nginx -y
sudo systemctl start nginx
```

#### Включить firewall:

```bash
sudo ufw allow 'Nginx Full'
sudo ufw allow OpenSSH

sudo ufw enable
```

#### Открыть файл nginx с помощью nano и настроить:

```bash
sudo nano /etc/nginx/sites-enabled/default
```


```nginx configuration
server {
    server_name <ip> <domain>;

    location / {
        proxy_set_header Host $http_host;
        proxy_pass http://127.0.0.1:8000;
    }
}
```

#### Проверить и перезапустить файл nginx:

```bash
sudo nginx -t
sudo systemctl start nginx
```

#### Склонировать репозиторий и перейти в директорию проекта:

```bash
git clone https://github.com/germynic31/foodgram.git
cd foodgram
```

#### Скопировать docker-compose.production.yml и настроить .env

```bash
sudo nano .env
```

```dotenv
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=foodgram
DB_HOST=db
DB_PORT=5432
DB_NAME=foodgram
DEBUG=0
ALLOWED_HOSTS='<domen>, <ip>, 127.0.0.1, localhost'
SECRET_KEY='django-secret-key'
```


#### Загрузка и запуск контейнеров:

```bash
sudo docker compose -f docker-compose.production.yml pull
sudo docker compose -f docker-compose.production.yml down
sudo docker compose -f docker-compose.production.yml up -d
```

#### Выполнить миграции и собрать статику:

```bash
sudo docker compose -f docker-compose.production.yml exec backend python manage.py migrate
sudo docker compose -f docker-compose.production.yml exec backend python manage.py collectstatic
```

#### Заполнить базу данных ингредиентами:

```bash
sudo docker compose -f docker-compose.production.yml exec backend python import_data_from_csv.py
```
---

#### Авторы: [Герман Деев](https://github.com/germynic31) (backend, docker, CI/CD), [Yandex-Practicum](https://github.com/Yandex-Practicum) (frontend)

---

Проект создан в учебных целях на курсе Я.Практикума


