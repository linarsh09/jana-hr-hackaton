from datetime import date
from app.api.vacations.repository import VacationRepository
from app.api.employees.repository import EmployeeRepository
from app.models import VacationRequest, VacationStatus


class VacationService:

    @staticmethod
    def create_request(
        employee_id: int,
        start_date: date,
        end_date: date,
        comment: str | None = None,
    ):
        # Проверяем сотрудника
        employee = EmployeeRepository.get_by_id(employee_id)

        if employee is None:
            raise ValueError("Employee not found")

        # Проверяем даты
        if start_date > end_date:
            raise ValueError(
                "Start date cannot be after end date"
            )

        # Количество дней
        days = (end_date - start_date).days + 1

        # Проверяем остаток отпуска
        if days > employee.vacation_days:
            raise ValueError(
                f"Not enough vacation days. "
                f"Available: {employee.vacation_days}"
            )

        vacation_request = VacationRequest(
            employee_id=employee_id,
            start_date=start_date,
            end_date=end_date,
            status=VacationStatus.PENDING,
            comment=comment,
        )

        return VacationRepository.create(vacation_request)
