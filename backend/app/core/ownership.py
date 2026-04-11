from fastapi import HTTPException, status


def validate_hr_ownership_for_interview(interview, current_user, *, resource_name: str = "interview") -> None:
    """Ensure the HR (or super_admin) owns the application attached to this interview."""
    if interview is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
    application = getattr(interview, "application", None)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
    validate_hr_ownership(application, current_user, resource_name=resource_name)


def validate_hr_ownership(resource, current_user, *, resource_name: str = "resource") -> None:
    """
    Centralized HR ownership guard.
    Super admins and HR users can access everything.
    """
    if current_user.role in ("super_admin", "hr"):
        return

    owner_id = getattr(resource, "hr_id", None)
    if owner_id is None or owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Unauthorized access to {resource_name}",
        )

