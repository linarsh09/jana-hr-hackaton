
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
        start_date: date | None,
        end_date: date | None,
        comment: str | None = None,
        request_type: str = "vacation",
    ):
        employee = EmployeeRepository.get_by_id(employee_id)

        if employee is None:
            raise ValueError("Employee not found")

        allowed_types = (
            "vacation",
            "sick_leave",
            "certificate",
            "other",
        )

        if request_type not in allowed_types:
            raise ValueError("Unknown request type")

        if request_type in ("vacation", "sick_leave"):
            if start_date is None or end_date is None:
                raise ValueError("Select both start and end dates")

        if (start_date is None) != (end_date is None):
            raise ValueError("Select both start and end dates")

        if start_date is not None and end_date is not None:
            if start_date > end_date:
                raise ValueError("Start date cannot be after end date")

        if request_type in ("certificate", "other") and not comment:
            raise ValueError("Describe what you need in the comment")

        if request_type == "vacation":
            if VacationRepository.has_date_overlap(
                employee_id, start_date, end_date
            ):
                raise ValueError(
                    "A pending or approved vacation already covers these dates"
                )

            days = (end_date - start_date).days + 1
            available_days = VacationService.get_available_days(employee_id)

            if days > available_days:
                raise ValueError(
                    f"Not enough vacation days. Available: {available_days}"
                )

        vacation_request = VacationRequest(
            employee_id=employee_id,
            start_date=start_date,
            end_date=end_date,
            request_type=request_type,
            status="pending",
            comment=comment,
        )

        return VacationRepository.create(vacation_request)
