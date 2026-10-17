
from datetime import date

from flask import Blueprint, g, jsonify, request

from app.api.vacations.service import VacationService
from app.api.vacations.repository import VacationRepository
from app.core.permissions import login_required

vacations_bp = Blueprint(
    "vacations",
    __name__,
    url_prefix="/api/v1/vacations",
)


@vacations_bp.post("")
@login_required
def create_vacation_request():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request body is required"}), 400

    required_fields = ["start_date", "end_date"]
    missing_fields = [
        field for field in required_fields
        if not data.get(field)
    ]

    if missing_fields:
        return jsonify({
            "error": "Missing required fields",
            "fields": missing_fields,
        }), 400

    user = g.current_user

    if user.employee is None:
        return jsonify({
            "error": "Employee profile not found"
        }), 404

    try:
        start_date = date.fromisoformat(data["start_date"])
        end_date = date.fromisoformat(data["end_date"])

        vacation = VacationService.create_request(
            employee_id=user.employee.id,
            start_date=start_date,
            end_date=end_date,
            comment=data.get("comment"),
        )

        return jsonify({
            "id": vacation.id,
            "employee_id": vacation.employee_id,
            "start_date": vacation.start_date.isoformat(),
            "end_date": vacation.end_date.isoformat(),
            "days": vacation.days,
            "status": vacation.status,
            "comment": vacation.comment,
            "created_at": vacation.created_at.isoformat(),
        }), 201

    except ValueError as error:
        return jsonify({"error": str(error)}), 400


@vacations_bp.get("/my")
@login_required
def get_my_vacation_requests():
    user = g.current_user

    if user.employee is None:
        return jsonify({
            "error": "Employee profile not found"
        }), 404

    vacation_requests = VacationRepository.get_by_employee_id(
        user.employee.id
    )

    return jsonify([
        {
            "id": item.id,
            "start_date": item.start_date.isoformat(),
            "end_date": item.end_date.isoformat(),
            "days": item.days,
            "status": item.status,
            "comment": item.comment,
            "created_at": item.created_at.isoformat(),
        }
        for item in vacation_requests
    ]), 200
