import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from accounts.permissions import (
    get_trainer_profile,
    staff_required,
    trainer_required,
)
from classes.models import SchoolClass, Subject
from timetable.models import Timetable
from trainers.models import TrainerProfile

from .forms import SessionForm
from .models import Session, get_next_session_number


@login_required
def session_list(request):
    """Trainers see their own sessions; staff see all sessions."""
    profile = get_trainer_profile(request.user)
    sessions = Session.objects.select_related(
        "trainer", "school_class", "subject"
    )
    if not request.user.is_staff:
        sessions = sessions.filter(trainer=profile)

    # Filters
    date_from = request.GET.get("from", "").strip()
    date_to = request.GET.get("to", "").strip()
    trainer_id = request.GET.get("trainer", "").strip()
    class_id = request.GET.get("class", "").strip()
    subject_id = request.GET.get("subject", "").strip()

    if date_from:
        try:
            sessions = sessions.filter(date__gte=datetime.date.fromisoformat(date_from))
        except ValueError:
            date_from = ""
    if date_to:
        try:
            sessions = sessions.filter(date__lte=datetime.date.fromisoformat(date_to))
        except ValueError:
            date_to = ""
    if request.user.is_staff and trainer_id:
        sessions = sessions.filter(trainer_id=trainer_id)
    if class_id:
        sessions = sessions.filter(school_class_id=class_id)
    if subject_id:
        sessions = sessions.filter(subject_id=subject_id)

    page_obj = Paginator(sessions, 20).get_page(request.GET.get("page"))

    context = {
        "sessions": page_obj,
        "date_from": date_from,
        "date_to": date_to,
        "trainer_id": trainer_id,
        "class_id": class_id,
        "subject_id": subject_id,
        "is_staff": request.user.is_staff,
        "trainers": TrainerProfile.objects.filter(is_active=True).order_by("full_name"),
        "classes": SchoolClass.objects.filter(is_active=True).order_by("name", "section"),
        "subjects": Subject.objects.filter(is_active=True).order_by("name"),
    }
    return render(request, "sessions/session_list.html", context)


@trainer_required
@require_http_methods(["GET", "POST"])
def session_complete(request, timetable_id):
    """The quick 'Complete Session' workflow.

    The trainer only enters students present, topic taught, activity and
    notes. Everything else is taken from the timetable and computed here.
    """
    profile = get_trainer_profile(request.user)
    timetable = get_object_or_404(
        Timetable, pk=timetable_id, trainer=profile, is_active=True
    )
    today = timezone.localdate()

    existing = (
        Session.objects.filter(trainer=profile, timetable=timetable, date=today)
        .order_by("-session_number")
        .first()
    )
    if existing:
        messages.info(
            request,
            f"Session {existing.session_number} is already recorded for this class today.",
        )
        return redirect("sessions:session_detail", pk=existing.pk)

    if request.method == "POST":
        form = SessionForm(request.POST)
        if form.is_valid():
            session = form.save(commit=False)
            session.trainer = profile
            session.timetable = timetable
            session.school_class = timetable.school_class
            session.subject = timetable.subject
            try:
                with transaction.atomic():
                    session.session_number = get_next_session_number(
                        timetable.school_class, timetable.subject
                    )
                    session.save()
            except Exception:
                messages.error(
                    request,
                    "Could not save the session. Please try again.",
                )
                return render(
                    request,
                    "sessions/session_form.html",
                    {"form": form, "timetable": timetable, "mode": "complete"},
                )
            messages.success(
                request,
                f"Session {session.session_number} recorded successfully for "
                f"{session.school_class} · {session.subject}.",
            )
            return redirect("sessions:session_detail", pk=session.pk)
    else:
        initial = {
            "date": today,
            "start_time": timetable.start_time,
            "end_time": timetable.end_time,
        }
        form = SessionForm(initial=initial)

    # Compute the number that will be assigned, for display before saving.
    next_number = get_next_session_number(timetable.school_class, timetable.subject)

    context = {
        "form": form,
        "timetable": timetable,
        "mode": "complete",
        "next_number": next_number,
    }
    return render(request, "sessions/session_form.html", context)


def _can_view_session(user, session):
    return user.is_staff or session.trainer.user_id == user.id


@login_required
def session_detail(request, pk):
    session = get_object_or_404(
        Session.objects.select_related("trainer", "school_class", "subject"),
        pk=pk,
    )
    if not _can_view_session(request.user, session):
        return render(request, "errors/403.html", status=403)
    context = {
        "session": session,
        "can_edit": _can_view_session(request.user, session),
        "can_delete": request.user.is_staff,
    }
    return render(request, "sessions/session_detail.html", context)


@login_required
@require_http_methods(["GET", "POST"])
def session_edit(request, pk):
    session = get_object_or_404(
        Session.objects.select_related("trainer", "school_class", "subject"),
        pk=pk,
    )
    if not _can_view_session(request.user, session):
        return render(request, "errors/403.html", status=403)

    if request.method == "POST":
        form = SessionForm(request.POST, instance=session)
        if form.is_valid():
            form.save()
            messages.success(request, "Session updated successfully.")
            return redirect("sessions:session_detail", pk=session.pk)
    else:
        form = SessionForm(instance=session)

    context = {"form": form, "session": session, "mode": "edit"}
    return render(request, "sessions/session_form.html", context)


@staff_required
@require_http_methods(["POST"])
def session_delete(request, pk):
    session = get_object_or_404(Session, pk=pk)
    session.delete()
    messages.success(request, "Session deleted successfully.")
    return redirect(request.POST.get("next") or "sessions:session_list")