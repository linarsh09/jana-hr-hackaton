
from app.extensions import db
from app.models import VacationRequest


class VacationRepository:

    @staticmethod
    def get_for_employee(employee_id: int) -> list[VacationRequest]:
        return VacationRequest.query.filter_by(
            employee_id=employee_id
        ).order_by(
            VacationRequest.created_at.desc(),
            VacationRequest.id.desc()
        ).all()

    @staticmethod
    def get_reserved_days(employee_id: int) -> int:
        requests = VacationRequest.query.filter(
            VacationRequest.employee_id == employee_id,
            VacationRequest.status.in_(("pending", "approved"))
        ).all()

        return sum((item.end_date - item.start_date).days + 1 for item in requests)

    @staticmethod
    def has_date_overlap(
        employee_id: int,
        start_date,
        end_date
    ) -> bool:
        return VacationRequest.query.filter(
            VacationRequest.employee_id == employee_id,
            VacationRequest.status.in_(("pending", "approved")),
            VacationRequest.start_date <= end_date,
            VacationRequest.end_date >= start_date
        ).first() is not None

    @staticmethod
    def create(
        vacation_request: VacationRequest
    ) -> VacationRequest:
        db.session.add(vacation_request)
        db.session.commit()
        return vacation_request

    @staticmethod
    def get_by_employee_id(
        employee_id: int
    ) -> list[VacationRequest]:
        return VacationRepository.get_for_employee(employee_id)
