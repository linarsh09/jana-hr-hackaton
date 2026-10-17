from app import create_app
from app.extensions import db
from app.models import Role

ROLES = {
    'employee': 'Сотрудник',
    'manager': 'Руководитель',
    'hr': 'HR / Администратор',
}

app = create_app()
with app.app_context():
    for name, description in ROLES.items():
        role = Role.query.filter_by(name=name).first()
        if role is None:
            db.session.add(Role(name=name, description=description))
            print('Добавлена роль:', name)
        else:
            role.description = description
            print('Уже существует:', name)
    db.session.commit()
    print('Готово: три роли в базе.')
