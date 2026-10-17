"""Local demo launcher using a separate SQLite database."""
import os
import secrets
from datetime import date
from pathlib import Path

from werkzeug.security import generate_password_hash


def build_demo():
    demo_dir = Path(__file__).resolve().parent / "work" / "demo"
    demo_dir.mkdir(parents=True, exist_ok=True)
    database = demo_dir / "academy.sqlite"
    # Always override shared database settings for this local-only launcher.
    os.environ["DATABASE_URL"] = "sqlite:///" + database.as_posix()
    secret_file = demo_dir / "session.key"
    if not secret_file.exists():
        secret_file.write_text(secrets.token_hex(32), encoding="utf-8")
    os.environ["SECRET_KEY"] = secret_file.read_text(encoding="utf-8")

    from app import create_app
    from app.extensions import db
    from app.models import User, Employee, Department, UserRole
    from app.api.academy.models import Course, Lesson, CourseAssignment, QuizQuestion

    app = create_app()
    with app.app_context():
        db.create_all()
        user = db.session.scalar(db.select(User).filter_by(username="academy_demo"))
        if user is None:
            user = User(username="academy_demo", password_hash=generate_password_hash("DemoAcademy123!"))
            department = Department(name="Demo Academy")
            employee = Employee(first_name="Демо", last_name="Сотрудник",
                                email="academy@example.test", position="Стажёр",
                                hire_date=date(2026, 10, 17), department=department, user=user)
            db.session.add_all([user, employee])
        if db.session.scalar(db.select(Course.id).limit(1)) is None:
            course = Course(title="Знакомство с JanaMen", description="Демонстрационный курс Academy")
            course.lessons = [
                Lesson(title="Добро пожаловать", content="Знакомимся с компанией и платформой JanaMen.", position=1),
                Lesson(title="Работа с платформой", content="Профиль, обучение и кадровые заявки.", position=2),
            ]
            db.session.add(course)
        # Update only the synthetic course created by this demo launcher.
        demo_course = db.session.scalar(db.select(Course).filter_by(title="Знакомство с JanaMen"))
        if demo_course:
            for lesson in demo_course.lessons:
                if lesson.position == 1:
                    lesson.content = (
                        "Добро пожаловать в JanaMen!\n\n"
                        "Это демонстрационный вводный курс. Он поможет познакомиться с личным кабинетом "
                        "и попробовать обучение в Academy.\n\n"
                        "Что есть в личном кабинете\n"
                        "• Профиль — твои основные данные и информация о работе.\n"
                        "• Заявки — раздел для кадровых обращений.\n"
                        "• Моё обучение — курсы, материалы и сохранённый прогресс.\n\n"
                        "Как проходить курс\n"
                        "Прочитай материал и нажми «Урок пройден · Далее». "
                        "Academy сохранит отметку и откроет следующий урок. "
                        "К изученному можно вернуться в любой момент.\n\n"
                        "Готово? Отметь этот урок пройденным, чтобы попробовать следующий шаг."
                    )
                elif lesson.position == 2:
                    lesson.content = (
                        "Твоё обучение — в твоём темпе\n\n"
                        "Программа курса находится слева. Нажми на название любого урока, "
                        "чтобы открыть его. Галочка рядом с названием означает, что материал уже пройден.\n\n"
                        "Как считается прогресс\n"
                        "В этом курсе два урока. Один пройденный урок — 50%, оба — 100%. "
                        "Повторный просмотр или нажатие не увеличивают результат.\n\n"
                        "Можно ли сделать перерыв?\n"
                        "Да. Отметки сохраняются в локальной базе. При следующем входе "
                        "карточка курса предложит продолжить обучение.\n\n"
                        "Теперь ты знаешь, как пользоваться Academy. "
                        "Отметь последний урок — на странице курса откроется итоговый тест. "
                        "В нём пять вопросов по материалам курса. Для сдачи нужно ответить правильно "
                        "как минимум на четыре вопроса (80%). При необходимости можно пересдать."
                    )
        db.session.flush()
        demo_department = user.employee.department
        demo_accounts = {}
        for username, role, first_name in [
            ('academy_hr', UserRole.HR, 'HR'),
            ('academy_manager', UserRole.MANAGER, 'Руководитель'),
            ('academy_worker', UserRole.EMPLOYEE, 'Новый'),
        ]:
            account = db.session.scalar(db.select(User).filter_by(username=username))
            if account is None:
                account = User(username=username, role=role, password_hash=generate_password_hash('DemoAcademy123!'))
                db.session.add(Employee(first_name=first_name, last_name='Демо',
                    email=username + '@example.test', position=role.value,
                    hire_date=date(2026, 10, 17), department=demo_department, user=account))
                db.session.flush()
            demo_accounts[username] = account
        manager = demo_accounts['academy_manager'].employee
        user.employee.manager = manager
        demo_accounts['academy_worker'].employee.manager = manager
        if demo_course and db.session.get(CourseAssignment, (user.employee.id, demo_course.id)) is None:
            db.session.add(CourseAssignment(employee_id=user.employee.id, course_id=demo_course.id,
                                           assigned_by=demo_accounts['academy_hr'].id))
        if demo_course and db.session.scalar(db.select(QuizQuestion.id).filter_by(course_id=demo_course.id).limit(1)) is None:
            questions = [
                ('Где находятся основные данные сотрудника?', ['В профиле', 'В итоговом тесте', 'В программе курса'], 0),
                ('Для чего нужен раздел «Заявки»?', ['Для просмотра уроков', 'Для кадровых обращений', 'Для подсчёта баллов'], 1),
                ('Как сохранить прохождение урока?', ['Просто закрыть страницу', 'Выйти из профиля', 'Нажать «Урок пройден · Далее»'], 2),
                ('Какой прогресс дают один из двух пройденных уроков?', ['100%', '50%', '25%'], 1),
                ('Что происходит с прогрессом при повторном нажатии на завершение урока?', ['Не увеличивается повторно', 'Сбрасывается', 'Удваивается'], 0),
            ]
            for position, (text, options, correct) in enumerate(questions, 1):
                db.session.add(QuizQuestion(course_id=demo_course.id, position=position,
                                           text=text, options=options, correct_option=correct))
        db.session.commit()
    return app


if __name__ == "__main__":
    app = build_demo()
    print("Login: http://127.0.0.1:5000/account/login", flush=True)
    print("Demo user: academy_demo / DemoAcademy123!", flush=True)
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
