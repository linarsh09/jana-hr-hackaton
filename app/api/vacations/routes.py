from datetime import date
from app.api.vacations.service import VacationService
from flask import Blueprint, jsonify, request, g
from app.core.permissions import can_access_employee


vacations_bp = Blueprint(
    "vacations",
    __name__,
    url_prefix="/api/v1/vacations",
)


@vacations_bp.post("")
def create_vacation_request():
    if getattr(g, "current_user", None) is None:
        return jsonify({"error": "Authentication required"}), 401
    data = request.get_json()

    if not data:
        return jsonify({
            "error": "Request body is required"
        }), 400

    required_fields = [
        "employee_id",
        "start_date",
        "end_date",
    ]

    missing_fields = [
        field
        for field in required_fields
        if field not in data
    ]

    if missing_fields:
        return jsonify({
            "error": "Missing required fields",
            "fields": missing_fields,
        }), 400

    try:
        if not can_access_employee(data["employee_id"]):
            return jsonify({"error": "Forbidden"}), 403
        start_date = date.fromisoformat(
            data["start_date"]
        )

        end_date = date.fromisoformat(
            data["end_date"]
        )

        vacation = VacationService.create_request(
            employee_id=data["employee_id"],
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
        }), 201

    except ValueError as error:
        return jsonify({
            "error": str(error)
        }), 400
