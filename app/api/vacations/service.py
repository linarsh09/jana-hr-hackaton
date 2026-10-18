
from datetime import date

from app.api.vacations.repository import VacationRepository
from app.api.employee.repository import EmployeeRepository
from app.models import VacationRequest


class VacationService:

    @staticmethod
    def get_available_days(employee_id: int) -> int:
        employee = EmployeeRepository.get_by_id(employee_id)

        if employee is None:
            raise ValueError("Employee not found")

        reserved_days = VacationRepository.get_reserved_days(employee_id)
        return max(employee.vacation_days - reserved_days, 0)

    @staticmethod
    def get_requests(employee_id: int):
        return VacationRepository.get_for_employee(employee_id)

    @staticmethod
    def create_request(
        employee_id: int,
        start_date: date,
        end_date: date,
        comment: str | None = None,
    ):
        employee = EmployeeRepository.get_by_id(employee_id)

        if employee is None:
            raise ValueError("Employee not found")

        if start_date is None or end_date is None:
            raise ValueError("Select both dates")

        if start_date > end_date:
            raise ValueError("Start date cannot be after end date")

        if VacationRepository.has_date_overlap(
            employee_id, start_date, end_date
        ):
            raise ValueError(
                "Вы уже выбрали эти даты для другой заявки на отпуск. "
                "Пожалуйста, выберите другой период."
            )

        days = (end_date - start_date).days + 1

        available_days = VacationService.get_available_days(
            employee_id
        )

        if days > available_days:
            raise ValueError(
                f"Not enough vacation days. Available: {available_days}"
            )

        vacation_request = VacationRequest(
            employee_id=employee_id,
            start_date=start_date,
            end_date=end_date,
            status="pending",
            comment=comment
        )

        return VacationRepository.create(vacation_request)