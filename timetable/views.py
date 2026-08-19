import datetime
import json

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

import openpyxl

from accounts.permissions import staff_required, trainer_required
from sessions.models import Session

from .forms import ManualClassForm, TimetableForm, TimetableUploadForm
from .importers import import_timetable_rows
from .models import (
    DAYS_OF_WEEK,
    ManualClass,
    Timetable,
    TimetableOccurrenceRemoval,
)
from .parsing import build_template_workbook, parse_workbook

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]


def _week_start(reference_date):
    """Monday of the week containing the given date."""
    return reference_date - datetime.timedelta(days=reference_date.weekday())


def _remove_date(profile, date):
    """Occurrence-removal dates for the trainer on a given date."""
    return set(
        TimetableOccurrenceRemoval.objects.filter(
            timetable__trainer=profile, date=date
        ).values_list("timetable_id", flat=True)
    )


def _session_lookup(profile, start_date, end_date):
    """Map (timetable_id, date) -> session for completed occurrences."""
    sessions = Session.objects.filter(
        trainer=profile, date__gte=start_date, date__lte=end_date
    )
    return {
        (s.timetable_id, s.date): s
        for s in sessions
        if s.timetable_id is not None
    }


@trainer_required
def my_timetable(request):
    """Trainer's weekly timetable view with week navigation.

    Shows the recurring weekly timetable as a period grid (like the Excel
    structure) plus manual assignments for the current week.
    """
    profile = request.user.profile
    today = timezone.localdate()

    week_param = request.GET.get("week")
    try:
        reference = datetime.date.fromisoformat(week_param) if week_param else today
    except ValueError:
        reference = today

    week_start = _week_start(reference)
    week_end = week_start + datetime.timedelta(days=6)

    entries = (
        Timetable.objects.filter(
            trainer=profile, day_of_week__in=WEEKDAYS, is_active=True
        )
        .select_related("school_class", "subject")
        .order_by("period", "start_time")
    )

    sessions_this_week = _session_lookup(profile, week_start, week_end)

    periods = sorted({e.period for e in entries if e.period})

    enriched = {}
    for e in entries:
        date_key = week_start + datetime.timedelta(days=WEEKDAYS.index(e.day_of_week))
        session = sessions_this_week.get((e.pk, date_key))
        item = {
            "entry": e,
            "date": date_key,
            "removed": e.pk in _remove_date(profile, date_key),
            "session": session,
            "completed": session is not None,
        }
        enriched.setdefault((e.day_of_week, e.period), []).append(item)

    period_columns = [
        {
            "period": period,
            "cells": {
                day: enriched.get((day, period), []) for day in WEEKDAYS
            },
        }
        for period in periods
    ]

    grid = {day: [] for day in WEEKDAYS}
    for (day, _period), items in enriched.items():
        grid[day].extend(items)

    manual_classes = ManualClass.objects.filter(
        trainer=profile, date__gte=week_start, date__lte=week_end, is_active=True
    ).select_related("school_class", "subject")

    context = {
        "grid": grid,
        "period_columns": period_columns,
        "manual_classes": manual_classes,
        "week_start": week_start,
        "week_end": week_end,
        "today": today,
        "prev_week": week_start - datetime.timedelta(days=7),
        "next_week": week_start + datetime.timedelta(days=7),
        "weekly_count": entries.count(),
    }
    return render(request, "timetable/my_timetable.html", context)


@trainer_required
@require_http_methods(["GET", "POST"])
def upload_timetable(request):
    """Upload weekly timetable: upload → preview → confirm → import."""
    profile = request.user.profile

    if request.method == "POST" and request.POST.get("confirm"):
        raw_rows = request.session.get("timetable_import_rows")
        if not raw_rows:
            messages.error(request, "The preview has expired. Please upload the file again.")
            return redirect("timetable:upload_timetable")
        try:
            rows = [
                {
                    "day": r["day"],
                    "period": int(r["period"]),
                    "class_name": r["class_name"],
                    "grade": int(r["grade"]),
                    "start_time": datetime.time.fromisoformat(r["start_time"]),
                    "end_time": datetime.time.fromisoformat(r["end_time"]),
                }
                for r in json.loads(raw_rows)
            ]
        except (KeyError, ValueError, TypeError):
            messages.error(request, "The preview data is invalid. Please upload the file again.")
            request.session.pop("timetable_import_rows", None)
            return redirect("timetable:upload_timetable")

        try:
            created = import_timetable_rows(profile, rows, mode="replace")
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect("timetable:upload_timetable")

        request.session.pop("timetable_import_rows", None)
        messages.success(
            request,
            f"Weekly timetable imported: {created} class{'es' if created != 1 else ''} detected and saved.",
        )
        return redirect("timetable:my_timetable")

    if request.method == "POST":
        form = TimetableUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded = request.FILES["file"]
            try:
                workbook = openpyxl.load_workbook(uploaded, data_only=True)
            except Exception:
                messages.error(
                    request,
                    "Could not read the file. Please make sure it is a valid .xlsx workbook.",
                )
                form = TimetableUploadForm()
                return render(request, "timetable/upload.html", {"form": form})

            result = parse_workbook(workbook)
            if result["detected"] == 0:
                for error in result["errors"]:
                    messages.error(request, error)
                if not result["errors"]:
                    messages.error(
                        request,
                        "No classes were found in the file. Make sure the "
                        "structure is 'Day' + 'Period N' columns.",
                    )
                return render(request, "timetable/upload.html", {"form": form})

            session_rows = []
            for row in result["rows"]:
                session_rows.append(
                    {
                        "day": row["day"],
                        "period": row["period"],
                        "class_name": row["class_name"],
                        "grade": row["grade"],
                        "start_time": row["start_time"].strftime("%H:%M"),
                        "end_time": row["end_time"].strftime("%H:%M"),
                    }
                )
            request.session["timetable_import_rows"] = json.dumps(session_rows)
            request.session["timetable_import_detected"] = result["detected"]

            context = {
                "rows": result["rows"],
                "periods": result["periods"],
                "errors": result["errors"],
                "detected": result["detected"],
                "has_existing": Timetable.objects.filter(
                    trainer=profile, source="EXCEL", is_active=True
                ).exists(),
            }
            return render(request, "timetable/preview.html", context)
    else:
        form = TimetableUploadForm()

    return render(request, "timetable/upload.html", {"form": form})


@trainer_required
def download_template(request):
    buffer = build_template_workbook()
    response = HttpResponse(
        buffer.read(),
        content_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
    )
    response["Content-Disposition"] = (
        'attachment; filename="weekly_timetable_template.xlsx"'
    )
    return response


@trainer_required
@require_http_methods(["GET", "POST"])
def assign_manual_class(request):
    """Add a one-off manual class for a specific date."""
    profile = request.user.profile

    if request.method == "POST":
        form = ManualClassForm(request.POST)
        if form.is_valid():
            manual = form.save(commit=False)
            manual.trainer = profile
            manual.school = profile.school
            manual.save()
            messages.success(
                request,
                f"Manual class added: {manual.school_class} on "
                f"{manual.date} at {manual.start_time:%H:%M}. "
                "Your weekly timetable is unchanged.",
            )
            return redirect("timetable:my_timetable")
    else:
        form = ManualClassForm(
            initial={"date": timezone.localdate(), "subject": None}
        )

    context = {
        "form": form,
        "title": "Assign Class",
        "cancel_url": "timetable:my_timetable",
    }
    return render(request, "timetable/manual_form.html", context)


@trainer_required
@require_http_methods(["GET", "POST"])
def manual_class_delete(request, pk):
    """Delete a manual assignment only (recurring timetable untouched)."""
    profile = request.user.profile
    manual = get_object_or_404(
        ManualClass, pk=pk, trainer=profile, is_active=True
    )
    if request.method == "POST":
        manual.delete()
        messages.success(request, "Manual class removed. Your weekly timetable is unchanged.")
        return redirect(request.POST.get("next") or "timetable:my_timetable")
    context = {
        "manual": manual,
        "title": "Delete Manual Class",
        "cancel_url": "timetable:my_timetable",
    }
    return render(request, "timetable/manual_delete_confirm.html", context)


@trainer_required
def class_detail(request, pk):
    """Details of one recurring timetable class: info, tasks and sessions."""
    profile = request.user.profile
    entry = get_object_or_404(
        Timetable.objects.select_related("school_class", "subject", "school"),
        pk=pk,
        trainer=profile,
        is_active=True,
    )
    date_param = request.GET.get("date", "")
    try:
        context_date = datetime.date.fromisoformat(date_param)
    except ValueError:
        context_date = timezone.localdate()
        while context_date.strftime("%A") != entry.day_of_week:
            context_date += datetime.timedelta(days=1)

    from tasks.models import Task

    sessions = Session.objects.filter(
        trainer=profile, timetable=entry
    ).order_by("-date", "-session_number")
    tasks = Task.objects.filter(
        trainer=profile, timetable=entry
    ).order_by("-date", "start_time")

    context = {
        "entry": entry,
        "context_date": context_date,
        "sessions": sessions,
        "tasks": tasks,
        "removed_on": TimetableOccurrenceRemoval.objects.filter(
            timetable=entry, date=context_date
        ).exists(),
    }
    return render(request, "timetable/class_detail.html", context)


@trainer_required
@require_http_methods(["POST"])
def occurrence_remove_date(request, pk):
    """Remove a recurring class for ONE date only (no timetable change)."""
    profile = request.user.profile
    entry = get_object_or_404(
        Timetable, pk=pk, trainer=profile, is_active=True
    )
    date_str = request.POST.get("date", "")
    try:
        date = datetime.date.fromisoformat(date_str)
    except ValueError:
        date = timezone.localdate()
    TimetableOccurrenceRemoval.objects.get_or_create(
        timetable=entry, date=date
    )
    messages.success(
        request,
        f"Removed {entry.school_class} on {date} only. "
        "The weekly timetable rule is unchanged.",
    )
    return redirect("timetable:my_timetable")


@trainer_required
@require_http_methods(["GET", "POST"])
def recurring_remove_weekly(request, pk):
    """Remove a class from the recurring weekly timetable (with confirmation)."""
    profile = request.user.profile
    entry = get_object_or_404(
        Timetable.objects.select_related("school_class", "subject"),
        pk=pk,
        trainer=profile,
        is_active=True,
    )
    if request.method == "POST":
        entry.is_active = False
        entry.save(update_fields=["is_active", "updated_at"])
        messages.success(
            request,
            f"Removed {entry.school_class} (Period {entry.period or '-'}, "
            f"{entry.day_of_week}) from your weekly timetable. "
            "Historical sessions and tasks are untouched.",
        )
        return redirect("timetable:my_timetable")
    context = {"entry": entry, "cancel_url": "timetable:my_timetable"}
    return render(request, "timetable/recurring_delete_confirm.html", context)


@staff_required
def manage_list(request):
    query = request.GET.get("q", "").strip()
    day = request.GET.get("day", "").strip()
    trainer_id = request.GET.get("trainer", "").strip()

    entries = (
        Timetable.objects.select_related("trainer", "school_class", "subject")
        .order_by("day_of_week", "period", "start_time")
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
            entry = form.save(commit=False)
            entry.school = entry.trainer.school
            entry.save()
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
            saved = form.save(commit=False)
            saved.school = saved.trainer.school
            saved.save()
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
