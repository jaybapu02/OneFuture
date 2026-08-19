import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from classes.models import SchoolClass
from sessions.models import Session
from tasks.models import Task
from timetable.models import Timetable
from trainers.models import TrainerProfile

from .permissions import get_trainer_profile, staff_required, trainer_required
from .forms import ProfileEditForm


@login_required
def dashboard(request):
    """Route to the correct dashboard based on the user's role."""
    if request.user.is_staff:
        return _admin_dashboard(request)
    return _trainer_dashboard(request)


def _greeting(now):
    hour = now.hour
    if hour < 12:
        return "Good Morning"
    if hour < 17:
        return "Good Afternoon"
    return "Good Evening"


def _trainer_dashboard(request):
    profile = get_trainer_profile(request.user)
    today = timezone.localdate()
    now = timezone.localtime()
    day_name = today.strftime("%A")

    entries = (
        Timetable.objects.filter(
            trainer=profile, day_of_week=day_name, is_active=True
        )
        .select_related("school_class", "subject")
        .order_by("start_time")
    )

    sessions_today = list(
        Session.objects.filter(trainer=profile, date=today).select_related(
            "school_class", "subject", "timetable"
        )
    )
    session_ids_by_timetable = {
        s.timetable_id: s for s in sessions_today if s.timetable_id
    }

    timetable_cards = []
    for entry in entries:
        session = session_ids_by_timetable.get(entry.pk)
        if session:
            status = "completed"
        elif entry.start_time <= now.time() <= entry.end_time:
            status = "current"
        elif entry.start_time > now.time():
            status = "upcoming"
        else:
            status = "past"
        timetable_cards.append({"entry": entry, "session": session, "status": status})

    tasks_today = (
        Task.objects.filter(trainer=profile, date=today)
        .select_related("school_class", "subject")
        .order_by("status", "priority", "start_time")
    )
    open_tasks = Task.objects.filter(trainer=profile).exclude(
        status=Task.Status.COMPLETED
    )
    students_today = sum(s.students_present for s in sessions_today)

    context = {
        "greeting": _greeting(now),
        "today": today,
        "timetable_cards": timetable_cards,
        "tasks_today": tasks_today,
        "sessions_today": sessions_today,
        "stats": {
            "today_classes": len(timetable_cards),
            "completed_today": len(sessions_today),
            "pending_tasks": open_tasks.count(),
            "students_today": students_today,
        },
    }
    return render(request, "dashboard/trainer_dashboard.html", context)


@staff_required
def _admin_dashboard(request):
    today = timezone.localdate()
    day_name = today.strftime("%A")

    trainers = TrainerProfile.objects.all()
    active_trainers = trainers.filter(is_active=True)
    classes_total = SchoolClass.objects.filter(is_active=True).count()

    today_entries = (
        Timetable.objects.filter(day_of_week=day_name, is_active=True)
        .select_related("trainer", "school_class", "subject")
        .order_by("start_time", "trainer__full_name")
    )
    entry_ids = [e.pk for e in today_entries]
    completed_session_timetable_ids = set(
        Session.objects.filter(date=today, timetable_id__in=entry_ids)
        .values_list("timetable_id", flat=True)
    )

    activity_rows = []
    for entry in today_entries:
        done = entry.pk in completed_session_timetable_ids
        activity_rows.append({"entry": entry, "completed": done})

    completed_today = Session.objects.filter(date=today).count()
    pending_reports = sum(1 for r in activity_rows if not r["completed"])

    stats = {
        "total_trainers": trainers.count(),
        "active_trainers": active_trainers.count(),
        "total_classes": classes_total,
        "today_classes": len(activity_rows),
        "completed_today": completed_today,
        "pending_reports": pending_reports,
    }

    context = {
        "today": today,
        "stats": stats,
        "activity_rows": activity_rows,
    }
    return render(request, "dashboard/admin_dashboard.html", context)


@trainer_required
def profile(request):
    return render(request, "accounts/profile.html")


@trainer_required
@require_http_methods(["GET", "POST"])
def profile_edit(request):
    profile = get_trainer_profile(request.user)
    if request.method == "POST":
        form = ProfileEditForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("accounts:profile")
    else:
        form = ProfileEditForm(instance=profile)
    return render(request, "accounts/profile_edit.html", {"form": form, "title": "Edit Profile", "cancel_url": "accounts:profile", "multipart": True})
