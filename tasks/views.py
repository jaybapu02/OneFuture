import datetime

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from accounts.permissions import trainer_required
from classes.models import SchoolClass, Subject
from timetable.models import Timetable

from .forms import TaskForm
from .models import Task


def _task_queryset(profile):
    return Task.objects.filter(trainer=profile).select_related(
        "school_class", "subject", "timetable"
    )


@trainer_required
def task_list(request):
    profile = request.user.profile
    today = timezone.localdate()
    filter_key = request.GET.get("f", "")

    tasks = _task_queryset(profile)
    if filter_key == "today":
        tasks = tasks.filter(date=today)
    elif filter_key == "upcoming":
        tasks = tasks.filter(date__gte=today).exclude(status=Task.Status.COMPLETED)
    elif filter_key == "completed":
        tasks = tasks.filter(status=Task.Status.COMPLETED)
    elif filter_key == "pending":
        tasks = tasks.filter(status=Task.Status.PENDING)

    class_id = request.GET.get("class", "").strip()
    subject_id = request.GET.get("subject", "").strip()
    date_str = request.GET.get("date", "").strip()
    if class_id:
        tasks = tasks.filter(school_class_id=class_id)
    if subject_id:
        tasks = tasks.filter(subject_id=subject_id)
    if date_str:
        try:
            tasks = tasks.filter(date=datetime.date.fromisoformat(date_str))
        except ValueError:
            pass

    page_obj = Paginator(tasks, 15).get_page(request.GET.get("page"))

    context = {
        "tasks": page_obj,
        "filter_key": filter_key,
        "classes": SchoolClass.objects.filter(is_active=True).order_by("name", "section"),
        "subjects": Subject.objects.filter(is_active=True).order_by("name"),
        "class_id": class_id,
        "subject_id": subject_id,
        "date_str": date_str,
    }
    return render(request, "tasks/task_list.html", context)


@trainer_required
@require_http_methods(["GET", "POST"])
def task_create(request):
    profile = request.user.profile

    timetable = None
    timetable_id = request.GET.get("timetable") or request.POST.get("timetable")
    if timetable_id:
        timetable = get_object_or_404(
            Timetable, pk=timetable_id, trainer=profile, is_active=True
        )

    if request.method == "POST":
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.trainer = profile
            if timetable:
                task.timetable = timetable
                task.school_class = timetable.school_class
                task.subject = timetable.subject
                task.start_time = timetable.start_time
                task.end_time = timetable.end_time
            task.save()
            messages.success(request, "Task created successfully.")
            return redirect("tasks:task_list")
    else:
        initial = {}
        if timetable:
            initial = {
                "school_class": timetable.school_class_id,
                "subject": timetable.subject_id,
                "date": timezone.localdate(),
                "start_time": timetable.start_time,
                "end_time": timetable.end_time,
            }
        form = TaskForm(initial=initial)

    if timetable:
        form.fields["school_class"].initial = timetable.school_class_id
        form.fields["subject"].initial = timetable.subject_id

    context = {"form": form, "timetable": timetable}
    return render(request, "tasks/task_form.html", context)


@trainer_required
@require_http_methods(["GET", "POST"])
def task_edit(request, pk):
    profile = request.user.profile
    task = get_object_or_404(Task, pk=pk, trainer=profile)
    if request.method == "POST":
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            messages.success(request, "Task updated successfully.")
            return redirect("tasks:task_list")
    else:
        form = TaskForm(instance=task)
    return render(request, "tasks/task_form.html", {"form": form, "task": task})


@trainer_required
@require_http_methods(["POST"])
def task_delete(request, pk):
    profile = request.user.profile
    task = get_object_or_404(Task, pk=pk, trainer=profile)
    task.delete()
    messages.success(request, "Task deleted successfully.")
    return redirect(request.POST.get("next") or "tasks:task_list")


@trainer_required
@require_http_methods(["POST"])
def task_toggle(request, pk):
    """HTMX endpoint: toggle a task between Completed and Pending."""
    profile = request.user.profile
    task = get_object_or_404(Task, pk=pk, trainer=profile)
    if task.status == Task.Status.COMPLETED:
        task.status = Task.Status.PENDING
        messages.success(request, "Task reopened.")
    else:
        task.status = Task.Status.COMPLETED
        messages.success(request, "Task marked as complete.")
    task.save(update_fields=["status", "updated_at"])
    return render(request, "tasks/partials/_task_status.html", {"task": task})