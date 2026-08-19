import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from classes.models import SchoolClass
from sessions.models import Session
from tasks.models import Task
from timetable.models import ManualClass, Timetable, TimetableOccurrenceRemoval
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

    removed_ids = set(
        TimetableOccurrenceRemoval.objects.filter(date=today)
        .values_list("timetable_id", flat=True)
    )
    entries = (
        Timetable.objects.filter(
            trainer=profile, day_of_week=day_name, is_active=True
        )
        .select_related("school_class", "subject")
        .order_by("period", "start_time")
    )
    recurring = [e for e in entries if e.pk not in removed_ids]

    manual = list(
        ManualClass.objects.filter(
            trainer=profile, date=today, is_active=True
        ).select_related("school_class", "subject")
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
    for entry in recurring:
        session = session_ids_by_timetable.get(entry.pk)
        if session:
            status = "completed"
        elif entry.start_time <= now.time() <= entry.end_time:
            status = "current"
        elif entry.start_time > now.time():
            status = "upcoming"
        else:
            status = "past"
        timetable_cards.append(
            {
                "entry": entry,
                "session": session,
                "status": status,
                "is_manual": False,
                "manual": None,
                "period": entry.period,
                "start_time": entry.start_time,
                "end_time": entry.end_time,
            }
        )
    for m in manual:
        session = next(
            (s for s in sessions_today if s.school_class_id == m.school_class_id),
            None,
        )
        status = (
            "completed"
            if session
            else (
                "current"
                if m.start_time <= now.time() <= m.end_time
                else ("upcoming" if m.start_time > now.time() else "past")
            )
        )
        timetable_cards.append(
            {
                "entry": None,
                "session": session,
                "status": status,
                "is_manual": True,
                "manual": m,
                "period": m.period,
                "start_time": m.start_time,
                "end_time": m.end_time,
            }
        )
    timetable_cards.sort(key=lambda c: c["start_time"])

    tasks_today = (
        Task.objects.filter(trainer=profile, date=today)
        .select_related("school_class", "subject")
        .order_by("status", "priority", "start_time")
    )
    open_tasks = Task.objects.filter(trainer=profile).exclude(
        status=Task.Status.COMPLETED
    )
    weekly_classes = Timetable.objects.filter(
        trainer=profile, is_active=True
    ).count()

    all_sessions = Session.objects.filter(trainer=profile)
    recent_sessions = all_sessions.order_by("-date", "-start_time", "-pk")[:5]

    context = {
        "greeting": _greeting(now),
        "today": today,
        "timetable_cards": timetable_cards,
        "tasks_today": tasks_today,
        "sessions_today": sessions_today,
        "recent_sessions": recent_sessions,
        "profile": profile,
        "stats": {
            "today_classes": len(timetable_cards),
            "completed_today": len(sessions_today),
            "pending_tasks": open_tasks.count(),
            "weekly_classes": weekly_classes,
            "completed_sessions": all_sessions.count(),
            "classes_covered": all_sessions.values("school_class").distinct().count(),
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
    return render(request, "accounts/profile_edit.html", {"form": form, "title": "Edit Profile", "cancel_url": "accounts:profile"})
