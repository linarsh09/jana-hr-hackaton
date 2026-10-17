# jana-hr-hackaton

для миграции в БД:
1. инициализация:
    flask --app "app:create_app" db init

2. создание миграции:
    flask --app "app:create_app" db migrate -m "initial HR models"

3. применение миграции:
    flask --app "app:create_app" db upgrade

flask --app app:create_app run --debug
