from app.extensions import db
from app.models import Employee, VacationRequest


class VacationRepository:

    @staticmethod
    def create(vacation_request: VacationRequest) -> VacationRequest:
        db.session.add(vacation_request)
        db.session.commit()

        return vacation_request
