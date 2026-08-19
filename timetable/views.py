import datetime

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from accounts.permissions import staff_required, trainer_required
from sessions.models import Session

from .forms import TimetableForm
from .models import DAYS_OF_WEEK, Timetable


def _week_start(reference_date):
    """Monday of the week containing the given date."""
    return reference_date - datetime.timedelta(days=reference_date.weekday())


@trainer_required
def my_timetable(request):
    """Trainer's weekly timetable view with week navigation."""
    profile = request.user.profile
    today = timezone.localdate()

    week_param = request.GET.get("week")
    try:
        reference = datetime.date.fromisoformat(week_param) if week_param else today
    except ValueError:
        reference = today

    week_start = _week_start(reference)
    days = [week_start + datetime.timedelta(days=i) for i in range(7)]

    entries = (
        Timetable.objects.filter(
            trainer=profile, day_of_week__in=[d.strftime("%A") for d in days], is_active=True
        )
        .select_related("school_class", "subject")
        .order_by("start_time")
    )

    sessions_this_week = Session.objects.filter(
        trainer=profile, date__in=days
    ).values_list("timetable_id", "date")
    completed = {(t, d) for t, d in sessions_this_week}

    entries_by_day = {d: [] for d in days}
    for entry in entries:
        date_key = next(d for d in days if d.strftime("%A") == entry.day_of_week)
        entries_by_day[date_key].append(
            {
                "entry": entry,
                "date": date_key,
                "completed": (entry.pk, date_key) in completed,
            }
        )

    days_data = [
        {
            "date": d,
            "is_today": d == today,
            "entries": entries_by_day[d],
        }
        for d in days
    ]

    context = {
        "days_data": days_data,
        "week_start": week_start,
        "week_end": week_start + datetime.timedelta(days=6),
        "today": today,
        "prev_week": week_start - datetime.timedelta(days=7),
        "next_week": week_start + datetime.timedelta(days=7),
    }
    return render(request, "timetable/my_timetable.html", context)


@staff_required
def manage_list(request):
    query = request.GET.get("q", "").strip()
    day = request.GET.get("day", "").strip()
    trainer_id = request.GET.get("trainer", "").strip()

    entries = (
        Timetable.objects.select_related("trainer", "school_class", "subject")
        .order_by("day_of_week", "start_time")
    )
    if query:
        entries = entries.filter(
            Q(trainer__full_name__icontains=query)
            | Q(school_class__name__icontains=query)
            | Q(subject__name__icontains=query)
            | Q(room__icontains=query)
        )
    if day in dict(DAYS_OF_WEEK):
        entries = entries.filter(day_of_week=day)
    if trainer_id:
        entries = entries.filter(trainer_id=trainer_id)

    page_obj = Paginator(entries, 25).get_page(request.GET.get("page"))

    context = {
        "entries": page_obj,
        "query": query,
        "day": day,
        "trainer_id": trainer_id,
        "days": DAYS_OF_WEEK,
    }
    return render(request, "timetable/manage_list.html", context)


@staff_required
@require_http_methods(["GET", "POST"])
def manage_create(request):
    if request.method == "POST":
        form = TimetableForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Timetable entry created successfully.")
            return redirect("timetable:manage_list")
    else:
        form = TimetableForm()
    return render(request, "timetable/manage_form.html", {"form": form, "title": "Add Timetable Entry", "cancel_url": "timetable:manage_list"})


@staff_required
@require_http_methods(["GET", "POST"])
def manage_edit(request, pk):
    entry = get_object_or_404(Timetable, pk=pk)
    if request.method == "POST":
        form = TimetableForm(request.POST, instance=entry)
        if form.is_valid():
            form.save()
            messages.success(request, "Timetable updated successfully.")
            return redirect("timetable:manage_list")
    else:
        form = TimetableForm(instance=entry)
    return render(
        request,
        "timetable/manage_form.html",
        {"form": form, "title": "Edit Timetable Entry", "entry": entry, "cancel_url": "timetable:manage_list"},
    )


@staff_required
@require_http_methods(["POST"])
def manage_delete(request, pk):
    entry = get_object_or_404(Timetable, pk=pk)
    entry.delete()
    messages.success(request, "Timetable entry deleted successfully.")
    return redirect("timetable:manage_list")