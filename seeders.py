
from datetime import date

from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.models import (
    Department,
    Employee,
    VacationRequest,
    PerformanceReview,
    AIConversation,
    VacationStatus,
    ReviewStatus,
    User,
    UserRole,
)


app = create_app()


def seed():
    with app.app_context():
        # ==========================================
        # Очистка тестовых данных
        # ==========================================

        AIConversation.query.delete()
        PerformanceReview.query.delete()
        VacationRequest.query.delete()
        Employee.query.delete()
        Department.query.delete()

        db.session.commit()

        # ==========================================
        # Departments
        # ==========================================

        departments = [
            Department(
                name="IT",
                description="Information Technology",
            ),
            Department(
                name="Human Resources",
                description="HR and People Operations",
            ),
            Department(
                name="Finance",
                description="Finance and Accounting",
            ),
            Department(
                name="Marketing",
                description="Marketing and Communications",
            ),
            Department(
                name="Sales",
                description="Sales and Business Development",
            ),
        ]

        db.session.add_all(departments)
        db.session.flush()

        # ==========================================
        # Employees
        # ==========================================

        employees = [
            Employee(
                first_name="Ivan",
                last_name="Petrov",
                email="ivan.petrov@example.com",
                position="Backend Developer",
                salary=350000,
                hire_date=date(2023, 3, 15),
                vacation_days=24,
                department=departments[0],
            ),
            Employee(
                first_name="Anna",
                last_name="Smirnova",
                email="anna.smirnova@example.com",
                position="HR Manager",
                salary=320000,
                hire_date=date(2022, 7, 10),
                vacation_days=18,
                department=departments[1],
            ),
            Employee(
                first_name="Dmitry",
                last_name="Volkov",
                email="dmitry.volkov@example.com",
                position="Financial Analyst",
                salary=300000,
                hire_date=date(2024, 1, 20),
                vacation_days=21,
                department=departments[2],
            ),
            Employee(
                first_name="Maria",
                last_name="Sokolova",
                email="maria.sokolova@example.com",
                position="Marketing Manager",
                salary=330000,
                hire_date=date(2023, 9, 1),
                vacation_days=16,
                department=departments[3],
            ),
            Employee(
                first_name="Alexey",
                last_name="Morozov",
                email="alexey.morozov@example.com",
                position="Sales Manager",
                salary=310000,
                hire_date=date(2024, 5, 12),
                vacation_days=20,
                department=departments[4],
            ),
        ]

        db.session.add_all(employees)
        db.session.flush()

        # ==========================================
        # HR test user (the system has one elevated role: HR).
        # ==========================================

        hr_user = User.query.filter_by(username="hr").first()
        if hr_user is None:
            # Reuse the old seeded admin account if this database has one.
            hr_user = User.query.filter_by(username="admin").first()
            if hr_user is not None:
                hr_user.username = "hr"

        if hr_user is None:
            hr_user = User(
                username="hr",
                password_hash=generate_password_hash("hr"),
                role="hr",
                is_active=True,
            )

            db.session.add(hr_user)

        hr_user.role = "hr"
        hr_user.is_active = True
        print("HR user ready.")

        # ==========================================
        # Vacation Requests
        # ==========================================

        vacation_requests = [
            VacationRequest(
                employee=employees[0],
                start_date=date(2026, 10, 5),
                end_date=date(2026, 10, 9),
                status=VacationStatus.APPROVED,
                comment="Family vacation",
            ),
            VacationRequest(
                employee=employees[1],
                start_date=date(2026, 11, 2),
                end_date=date(2026, 11, 6),
                status=VacationStatus.PENDING,
                comment="Personal vacation",
            ),
            VacationRequest(
                employee=employees[2],
                start_date=date(2026, 10, 19),
                end_date=date(2026, 10, 21),
                status=VacationStatus.REJECTED,
                comment="Quarter-end workload",
            ),
            VacationRequest(
                employee=employees[3],
                start_date=date(2026, 12, 21),
                end_date=date(2026, 12, 25),
                status=VacationStatus.APPROVED,
                comment="Winter vacation",
            ),
            VacationRequest(
                employee=employees[4],
                start_date=date(2026, 10, 26),
                end_date=date(2026, 10, 30),
                status=VacationStatus.PENDING,
                comment="Trip",
            ),
        ]

        db.session.add_all(vacation_requests)
        db.session.flush()

        # ==========================================
        # Performance Reviews
        # ==========================================

        performance_reviews = [
            PerformanceReview(
                employee=employees[0],
                reviewer_name="Sergey Ivanov",
                period="2026 H1",
                score=5,
                strengths="Strong backend skills, ownership, system design.",
                weaknesses="Could improve documentation.",
                comment="Excellent performance during the first half of the year.",
                status=ReviewStatus.COMPLETED,
            ),
            PerformanceReview(
                employee=employees[1],
                reviewer_name="Elena Petrova",
                period="2026 H1",
                score=4,
                strengths="Strong communication and employee relations.",
                weaknesses="Could improve HR analytics.",
                comment="Consistent and reliable performance.",
                status=ReviewStatus.COMPLETED,
            ),
            PerformanceReview(
                employee=employees[2],
                reviewer_name="Michael Brown",
                period="2026 H1",
                score=4,
                strengths="Good analytical thinking and financial modelling.",
                weaknesses="Presentation skills can be improved.",
                comment="Solid results across the reporting period.",
                status=ReviewStatus.COMPLETED,
            ),
            PerformanceReview(
                employee=employees[3],
                reviewer_name="Olga Kuznetsova",
                period="2026 H1",
                score=3,
                strengths="Creative campaigns and strong execution.",
                weaknesses="Needs better planning and prioritization.",
                comment="Good progress with room for development.",
                status=ReviewStatus.COMPLETED,
            ),
            PerformanceReview(
                employee=employees[4],
                reviewer_name="Robert Wilson",
                period="2026 H1",
                score=5,
                strengths="Excellent sales results and client relationships.",
                weaknesses="Could share sales knowledge more with the team.",
                comment="Outstanding sales performance.",
                status=ReviewStatus.COMPLETED,
            ),
        ]

        db.session.add_all(performance_reviews)
        db.session.flush()

        # ==========================================
        # AI Conversations
        # ==========================================

        conversations = [
            AIConversation(
                employee=employees[0],
                title="Vacation balance",
                messages=[
                    {
                        "role": "user",
                        "content": "How many vacation days do I have left?",
                    },
                    {
                        "role": "assistant",
                        "content": "You currently have 24 vacation days available.",
                    },
                ],
            ),
            AIConversation(
                employee=employees[1],
                title="Employee onboarding",
                messages=[
                    {
                        "role": "user",
                        "content": "Show me employees who joined this month.",
                    },
                    {
                        "role": "assistant",
                        "content": "There are currently no employees who joined this month.",
                    },
                ],
            ),
            AIConversation(
                employee=employees[2],
                title="Performance review",
                messages=[
                    {
                        "role": "user",
                        "content": "Summarize my latest performance review.",
                    },
                    {
                        "role": "assistant",
                        "content": (
                            "Your latest review scored 4/5. "
                            "Your main strengths are analytical thinking "
                            "and financial modelling."
                        ),
                    },
                ],
            ),
            AIConversation(
                employee=employees[3],
                title="Career development",
                messages=[
                    {
                        "role": "user",
                        "content": "What skills should I improve?",
                    },
                    {
                        "role": "assistant",
                        "content": (
                            "Based on your latest review, "
                            "planning and prioritization are key areas "
                            "for development."
                        ),
                    },
                ],
            ),
            AIConversation(
                employee=employees[4],
                title="Vacation request",
                messages=[
                    {
                        "role": "user",
                        "content": "I want to take vacation next month.",
                    },
                    {
                        "role": "assistant",
                        "content": (
                            "Sure. Please provide the start and end dates "
                            "of your vacation."
                        ),
                    },
                ],
            ),
        ]

        db.session.add_all(conversations)

        # ==========================================
        # Commit
        # ==========================================

        db.session.commit()

        print("Database seeded successfully!")
        print("Departments: 5")
        print("Employees: 5")
        print("Vacation requests: 5")
        print("Performance reviews: 5")
        print("AI conversations: 5")
        print("HR username: hr")
        print("HR password: hr")


if __name__ == "__main__":
    seed()
