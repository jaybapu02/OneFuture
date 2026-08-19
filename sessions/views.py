import calendar
import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from accounts.permissions import (
    get_trainer_profile,
    staff_required,
    trainer_required,
)
from classes.models import SchoolClass, Subject
from timetable.models import ManualClass, Timetable
from trainers.models import TrainerProfile

from .forms import SessionForm
from .models import Session, get_next_session_number


@login_required
def session_list(request):
    """Trainers see their own sessions; staff see all sessions."""
    profile = get_trainer_profile(request.user)
    sessions = Session.objects.select_related(
        "trainer", "school", "school_class", "subject"
    )
    if not request.user.is_staff:
        sessions = sessions.filter(trainer=profile)

    # Filters
    date_from = request.GET.get("from", "").strip()
    date_to = request.GET.get("to", "").strip()
    month = request.GET.get("month", "").strip()
    trainer_id = request.GET.get("trainer", "").strip()
    class_id = request.GET.get("class", "").strip()
    subject_id = request.GET.get("subject", "").strip()
    month_label = ""

    if month:
        try:
            year, mon = (int(p) for p in month.split("-"))
            date_from = f"{year:04d}-{mon:02d}-01"
            last_day = calendar.monthrange(year, mon)[1]
            date_to = f"{year:04d}-{mon:02d}-{last_day:02d}"
            month_label = datetime.date(year, mon, 1).strftime("%B %Y")
        except (ValueError, TypeError):
            month = ""
            month_label = ""

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

    summary = {
        "total_sessions": sessions.count(),
        "working_days": sessions.values("date").distinct().count(),
        "classes_covered": sessions.values("school_class").distinct().count(),
        "students_present": sessions.aggregate(total=Sum("students_present"))["total"] or 0,
        "students_absent": sessions.aggregate(total=Sum("students_absent"))["total"] or 0,
    }

    page_obj = Paginator(sessions, 20).get_page(request.GET.get("page"))

    context = {
        "sessions": page_obj,
        "summary": summary,
        "date_from": date_from,
        "date_to": date_to,
        "month": month,
        "month_label": month_label,
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
    if timetable.subject is None:
        messages.error(
            request,
            "This class has no subject assigned. Ask your administrator to "
            "set a subject before completing the session.",
        )
        return redirect("timetable:my_timetable")
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
            session.school = timetable.school or profile.school
            session.timetable = timetable
            session.school_class = timetable.school_class
            session.subject = timetable.subject
            session.period = timetable.period
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


@trainer_required
@require_http_methods(["GET", "POST"])
def session_complete_manual(request, manual_id):
    """Complete a session for a manual (one-off) class."""
    profile = get_trainer_profile(request.user)
    manual = get_object_or_404(
        ManualClass.objects.select_related("school_class", "subject"),
        pk=manual_id,
        trainer=profile,
        is_active=True,
    )
    today = timezone.localdate()
    if manual.date > today:
        messages.warning(
            request,
            "This manual class is in the future. Sessions can only be "
            "completed on or after the class date.",
        )
        return redirect("timetable:my_timetable")

    existing = (
        Session.objects.filter(
            trainer=profile,
            school_class=manual.school_class,
            date=manual.date,
            period=manual.period,
        )
        .order_by("-session_number")
        .first()
    )
    if existing:
        messages.info(
            request,
            f"Session {existing.session_number} is already recorded for this class on this date.",
        )
        return redirect("sessions:session_detail", pk=existing.pk)

    subject = manual.subject
    if subject is None:
        messages.error(
            request,
            "This manual class has no subject assigned. Choose a subject "
            "before completing the session.",
        )
        return redirect("timetable:my_timetable")

    if request.method == "POST":
        form = SessionForm(request.POST)
        if form.is_valid():
            session = form.save(commit=False)
            session.trainer = profile
            session.school = manual.school or profile.school
            session.timetable = None
            session.school_class = manual.school_class
            session.subject = subject
            session.period = manual.period
            try:
                with transaction.atomic():
                    session.session_number = get_next_session_number(
                        manual.school_class, subject
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
                    {"form": form, "timetable": manual, "mode": "complete"},
                )
            messages.success(
                request,
                f"Session {session.session_number} recorded successfully for "
                f"{session.school_class} · {session.subject}.",
            )
            return redirect("sessions:session_detail", pk=session.pk)
    else:
        initial = {
            "date": manual.date,
            "start_time": manual.start_time,
            "end_time": manual.end_time,
        }
        form = SessionForm(initial=initial)

    next_number = get_next_session_number(manual.school_class, subject)

    context = {
        "form": form,
        "timetable": manual,
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