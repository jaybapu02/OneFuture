import datetime
import json

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.shortcuts import render
from django.utils import timezone

from accounts.permissions import get_trainer_profile
from classes.models import SchoolClass, Subject
from sessions.models import Session
from trainers.models import TrainerProfile


def _parse_date(value):
    try:
        return datetime.date.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def _base_filters(request, qs):
    """Apply the shared from/to/class/subject filters."""
    date_from = request.GET.get("from", "").strip()
    date_to = request.GET.get("to", "").strip()
    class_id = request.GET.get("class", "").strip()
    subject_id = request.GET.get("subject", "").strip()

    f = _parse_date(date_from)
    t = _parse_date(date_to)
    if f:
        qs = qs.filter(date__gte=f)
    if t:
        qs = qs.filter(date__lte=t)
    if class_id:
        qs = qs.filter(school_class_id=class_id)
    if subject_id:
        qs = qs.filter(subject_id=subject_id)
    return qs, {"from": date_from, "to": date_to, "class": class_id, "subject": subject_id}


def _sessions_over_time(qs, days=14):
    """Count sessions per day for the last N days (incl. only days with data)."""
    start = timezone.localdate() - datetime.timedelta(days=days - 1)
    counts = (
        qs.filter(date__gte=start)
        .values("date")
        .annotate(count=Count("id"))
        .order_by("date")
    )
    by_date = {row["date"]: row["count"] for row in counts}
    labels, data = [], []
    for i in range(days):
        d = start + datetime.timedelta(days=i)
        labels.append(d.strftime("%d %b"))
        data.append(by_date.get(d, 0))
    return labels, data


@login_required
def report(request):
    if request.user.is_staff:
        return _admin_report(request)
    return _trainer_report(request)


def _trainer_report(request):
    profile = get_trainer_profile(request.user)
    sessions = Session.objects.filter(trainer=profile).select_related(
        "school_class", "subject"
    )
    sessions, filters = _base_filters(request, sessions)

    total_sessions = sessions.count()
    agg = sessions.aggregate(
        total_students=Sum("students_present"),
    )
    total_students = agg["total_students"] or 0
    avg_attendance = round(total_students / total_sessions, 1) if total_sessions else 0
    classes_handled = (
        sessions.values("school_class__name", "school_class__section")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    topics = sessions.order_by("-date").values_list("topic_taught", flat=True)[:50]

    labels, data = _sessions_over_time(sessions)

    context = {
        "is_admin": False,
        "filters": filters,
        "metrics": {
            "total_sessions": total_sessions,
            "total_students": total_students,
            "avg_attendance": avg_attendance,
            "classes_handled": classes_handled.count(),
        },
        "classes_handled": list(classes_handled),
        "topics": topics,
        "chart": json.dumps({"labels": labels, "data": data}),
        "classes": SchoolClass.objects.filter(is_active=True).order_by("name", "section"),
        "subjects": Subject.objects.filter(is_active=True).order_by("name"),
    }
    return render(request, "reports/trainer_report.html", context)


def _admin_report(request):
    sessions = Session.objects.select_related("trainer", "school_class", "subject")
    sessions, filters = _base_filters(request, sessions)

    trainer_id = request.GET.get("trainer", "").strip()
    if trainer_id:
        sessions = sessions.filter(trainer_id=trainer_id)
        filters["trainer"] = trainer_id

    total_sessions = sessions.count()
    agg = sessions.aggregate(total_students=Sum("students_present"))
    total_students = agg["total_students"] or 0
    avg_attendance = round(total_students / total_sessions, 1) if total_sessions else 0
    active_trainers = TrainerProfile.objects.filter(is_active=True).count()

    by_trainer = list(
        sessions.values("trainer__full_name")
        .annotate(count=Count("id"), students=Sum("students_present"))
        .order_by("-count")
    )
    by_class = list(
        sessions.values("school_class__name", "school_class__section")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    labels, data = _sessions_over_time(sessions)

    context = {
        "is_admin": True,
        "filters": filters,
        "metrics": {
            "total_sessions": total_sessions,
            "total_students": total_students,
            "avg_attendance": avg_attendance,
            "active_trainers": active_trainers,
        },
        "by_trainer": by_trainer,
        "by_class": by_class,
        "chart": json.dumps({"labels": labels, "data": data}),
        "trainers": TrainerProfile.objects.filter(is_active=True).order_by("full_name"),
        "classes": SchoolClass.objects.filter(is_active=True).order_by("name", "section"),
        "subjects": Subject.objects.filter(is_active=True).order_by("name"),
    }
    return render(request, "reports/admin_report.html", context)