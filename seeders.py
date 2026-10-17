"""Idempotent demo data for JanaMen. Run: python seeders.py
Set JANAMEN_SEED_PASSWORD in the environment to create demo accounts.
Existing users, including admin, are never modified.
"""
import os
from datetime import date, datetime, timezone
from decimal import Decimal

from app import create_app
from app.extensions import db
from app.models import (
    Role, User, Department, Position, Employee, VacationRequest,
    KnowledgeCategory, KnowledgeArticle, Course, CourseModule,
    CourseEnrollment, ModuleProgress,
)


def get_or_create(model, lookup, **values):
    instance = db.session.query(model).filter_by(**lookup).first()
    if instance is None:
        instance = model(**lookup, **values)
        db.session.add(instance)
        db.session.flush()
        print(f"+ {model.__tablename__}: {lookup}")
    return instance


def seed():
    # Roles: exactly three allowed role names.
    roles = {}
    for name, description in [
        ("employee", "Сотрудник"),
        ("manager", "Руководитель"),
        ("hr", "HR / Администратор"),
    ]:
        roles[name] = get_or_create(Role, {"name": name}, description=description)

    departments = {}
    for name, description in [
        ("IT", "Разработка и поддержка систем"),
        ("HR", "Управление персоналом"),
        ("Финансы", "Финансовый отдел"),
        ("Маркетинг", "Маркетинг и коммуникации"),
    ]:
        departments[name] = get_or_create(Department, {"name": name}, description=description)

    positions = {}
    for name, description in [
        ("Разработчик", "Разработка приложений"),
        ("Тимлид", "Руководитель команды разработки"),
        ("HR-специалист", "Управление кадрами"),
        ("Аналитик", "Анализ данных и отчётность"),
        ("Маркетолог", "Продвижение продуктов"),
    ]:
        positions[name] = get_or_create(Position, {"name": name}, description=description)

    employee_specs = [
        ("Айдана", "Нурланова", "aidana.demo@janamen.example", "HR", "HR-специалист", "2023-03-01", "420000", 24),
        ("Алибек", "Сериков", "alibek.demo@janamen.example", "IT", "Тимлид", "2022-09-12", "650000", 26),
        ("Дана", "Ахметова", "dana.demo@janamen.example", "IT", "Разработчик", "2024-01-15", "390000", 18),
        ("Мадина", "Касымова", "madina.demo@janamen.example", "Финансы", "Аналитик", "2024-06-03", "410000", 21),
        ("Ержан", "Омаров", "erzhan.demo@janamen.example", "Маркетинг", "Маркетолог", "2025-02-10", "350000", 20),
    ]
    employees = {}
    for first, last, email, dept, position, hire, salary, balance in employee_specs:
        employees[email] = get_or_create(
            Employee, {"email": email},
            first_name=first, last_name=last, hire_date=date.fromisoformat(hire),
            salary=Decimal(salary), vacation_balance=balance,
            department_id=departments[dept].id, position_id=positions[position].id,
        )

    # Assign the reporting line only for newly unassigned demo employees.
    lead = employees["alibek.demo@janamen.example"]
    for email in ("dana.demo@janamen.example", "madina.demo@janamen.example", "erzhan.demo@janamen.example"):
        person = employees[email]
        if person.manager_id is None and person.id != lead.id:
            person.manager_id = lead.id
    db.session.flush()

    demo_password = os.getenv("JANAMEN_SEED_PASSWORD")
    accounts = [
        ("demo_hr", "hr", "aidana.demo@janamen.example"),
        ("demo_manager", "manager", "alibek.demo@janamen.example"),
        ("demo_dana", "employee", "dana.demo@janamen.example"),
        ("demo_madina", "employee", "madina.demo@janamen.example"),
        ("demo_erzhan", "employee", "erzhan.demo@janamen.example"),
    ]
    if not demo_password or len(demo_password) < 8:
        raise ValueError("Установите JANAMEN_SEED_PASSWORD (не менее 8 символов) перед запуском. Данные ещё не сохранены.")
    for username, role_name, email in accounts:
        person = employees[email]
        existing = User.query.filter_by(username=username).first()
        linked = User.query.filter_by(employee_id=person.id).first()
        if existing:
            print(f"= users: {username} уже существует (не изменён)")
            continue
        if linked:
            print(f"! users: {email} уже связан с аккаунтом {linked.username}; пропуск")
            continue
        user = User(username=username, role_id=roles[role_name].id, employee_id=person.id, is_active=True)
        user.set_password(demo_password)
        db.session.add(user)
        db.session.flush()
        print(f"+ users: {username}")

    categories = {}
    for name in ("Отпуска", "Адаптация", "IT-поддержка", "Корпоративные правила"):
        categories[name] = get_or_create(KnowledgeCategory, {"name": name})

    articles = [
        ("Отпуска", "Как подать заявку на отпуск", "Откройте раздел заявок, выберите даты и отправьте запрос."),
        ("Отпуска", "Как проверить остаток отпуска", "Остаток доступных дней отображается в личном кабинете."),
        ("Адаптация", "Первый рабочий день", "Познакомьтесь с командой и получите доступы к рабочим системам."),
        ("IT-поддержка", "Как обратиться в IT", "Опишите проблему и приложите сообщение об ошибке."),
        ("Корпоративные правила", "Правила безопасности", "Не передавайте пароль и блокируйте рабочий компьютер."),
    ]
    author = employees["aidana.demo@janamen.example"]
    for category, title, content in articles:
        get_or_create(KnowledgeArticle, {"title": title, "category_id": categories[category].id}, author_id=author.id, content=content)

    courses = {}
    for title, description in [
        ("Адаптация новичка", "Знакомство с компанией и процессами"),
        ("Информационная безопасность", "Безопасная работа с данными"),
        ("Основы коммуникации", "Рабочее общение и обратная связь"),
        ("Работа с заявками", "Оформление и согласование заявок"),
    ]:
        courses[title] = get_or_create(Course, {"title": title}, description=description, created_by_id=author.id)

    module_specs = [
        ("Адаптация новичка", 1, "О компании", "Миссия и структура JanaMen."),
        ("Адаптация новичка", 2, "Первый день", "Рабочие инструменты и контакты."),
        ("Информационная безопасность", 1, "Надёжные пароли", "Используйте уникальные пароли и MFA."),
        ("Основы коммуникации", 1, "Обратная связь", "Как давать конструктивную обратную связь."),
        ("Работа с заявками", 1, "Заявка на отпуск", "Как отправить запрос руководителю."),
    ]
    modules = {}
    for course_title, order, title, content in module_specs:
        course = courses[course_title]
        modules[(course_title, order)] = get_or_create(
            CourseModule, {"course_id": course.id, "position": order}, title=title, content=content
        )

    request_specs = [
        ("dana.demo@janamen.example", "2026-11-02", "2026-11-06", "pending", "Плановый отпуск"),
        ("madina.demo@janamen.example", "2026-11-09", "2026-11-13", "approved", "Семейная поездка"),
        ("erzhan.demo@janamen.example", "2026-12-01", "2026-12-03", "rejected", "Личные дела"),
        ("alibek.demo@janamen.example", "2026-12-14", "2026-12-18", "pending", "Зимний отпуск"),
        ("aidana.demo@janamen.example", "2026-11-23", "2026-11-25", "approved", "Отдых"),
    ]
    for email, start, end, status, comment in request_specs:
        person = employees[email]
        start_date = date.fromisoformat(start)
        reviewer = lead if person.id != lead.id else author
        values = dict(end_date=date.fromisoformat(end), status=status, comment=comment)
        if status != "pending":
            values.update(reviewed_by_id=reviewer.id, reviewed_at=datetime(2026, 10, 16, 12, 0, tzinfo=timezone.utc))
        get_or_create(VacationRequest, {"employee_id": person.id, "start_date": start_date}, **values)

    enrollment_specs = [
        ("dana.demo@janamen.example", "Адаптация новичка", "in_progress"),
        ("madina.demo@janamen.example", "Информационная безопасность", "completed"),
        ("erzhan.demo@janamen.example", "Основы коммуникации", "enrolled"),
        ("alibek.demo@janamen.example", "Работа с заявками", "in_progress"),
        ("aidana.demo@janamen.example", "Информационная безопасность", "completed"),
    ]
    enrollments = {}
    for email, course_title, status in enrollment_specs:
        person, course = employees[email], courses[course_title]
        values = {"status": status}
        if status == "completed":
            values["completed_at"] = datetime(2026, 10, 16, 12, 0, tzinfo=timezone.utc)
        enrollments[(email, course_title)] = get_or_create(
            CourseEnrollment, {"employee_id": person.id, "course_id": course.id}, **values
        )

    progress_specs = [
        ("dana.demo@janamen.example", "Адаптация новичка", 1),
        ("madina.demo@janamen.example", "Информационная безопасность", 1),
        ("alibek.demo@janamen.example", "Работа с заявками", 1),
        ("aidana.demo@janamen.example", "Информационная безопасность", 1),
    ]
    for email, course_title, order in progress_specs:
        enrollment = enrollments[(email, course_title)]
        module = modules[(course_title, order)]
        get_or_create(
            ModuleProgress, {"enrollment_id": enrollment.id, "module_id": module.id},
            course_id=enrollment.course_id,
        )

    db.session.commit()
    print("\nГотово. Добавлены недостающие демоданные; существующие записи сохранены.")
    for model in (Role, User, Department, Position, Employee, VacationRequest,
                  KnowledgeCategory, KnowledgeArticle, Course, CourseModule,
                  CourseEnrollment, ModuleProgress):
        print(f"{model.__tablename__}: {db.session.query(model).count()}")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        try:
            seed()
        except Exception:
            db.session.rollback()
            raise
