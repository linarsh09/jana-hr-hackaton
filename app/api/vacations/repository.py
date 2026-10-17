from app.extensions import db
from app.models import Employee, VacationRequest


class VacationRepository:

    @staticmethod
    def create(vacation_request: VacationRequest) -> VacationRequest:
        db.session.add(vacation_request)
        db.session.commit()

        return vacation_request
    
    @staticmethod
    def get_by_employee_id(employee_id: int) -> list[VacationRequest]:
        return VacationRequest.query.filter_by(
            employee_id=employee_id
        ).order_by(
            VacationRequest.created_at.desc()
        ).all()
