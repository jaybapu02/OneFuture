from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from accounts.permissions import staff_required

from .forms import ClassForm, SubjectForm
from .models import SchoolClass, Subject


@staff_required
def class_list(request):
    query = request.GET.get("q", "").strip()
    classes = SchoolClass.objects.annotate(
        timetable_count=Count("timetable", distinct=True)
    ).order_by("grade", "name", "section")
    if query:
        classes = classes.filter(
            Q(name__icontains=query) | Q(section__icontains=query)
        )
    page_obj = Paginator(classes, 20).get_page(request.GET.get("page"))
    return render(request, "classes/class_list.html", {"classes": page_obj, "query": query})


@staff_required
@require_http_methods(["GET", "POST"])
def class_create(request):
    if request.method == "POST":
        form = ClassForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Class created successfully.")
            return redirect("classes:class_list")
    else:
        form = ClassForm()
    return render(request, "classes/class_form.html", {"form": form, "title": "Add Class", "cancel_url": "classes:class_list"})


@staff_required
@require_http_methods(["GET", "POST"])
def class_edit(request, pk):
    obj = get_object_or_404(SchoolClass, pk=pk)
    if request.method == "POST":
        form = ClassForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Class updated successfully.")
            return redirect("classes:class_list")
    else:
        form = ClassForm(instance=obj)
    return render(request, "classes/class_form.html", {"form": form, "title": "Edit Class", "obj": obj, "cancel_url": "classes:class_list"})


@staff_required
@require_http_methods(["POST"])
def class_toggle(request, pk):
    obj = get_object_or_404(SchoolClass, pk=pk)
    obj.is_active = not obj.is_active
    obj.save(update_fields=["is_active", "updated_at"])
    action = "activated" if obj.is_active else "deactivated"
    messages.success(request, f"Class {obj} {action}.")
    return redirect("classes:class_list")


@staff_required
def subject_list(request):
    query = request.GET.get("q", "").strip()
    subjects = Subject.objects.annotate(
        timetable_count=Count("timetable", distinct=True)
    ).order_by("name")
    if query:
        subjects = subjects.filter(name__icontains=query)
    return render(request, "classes/subject_list.html", {"subjects": subjects, "query": query})


@staff_required
@require_http_methods(["GET", "POST"])
def subject_create(request):
    if request.method == "POST":
        form = SubjectForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Subject created successfully.")
            return redirect("classes:subject_list")
    else:
        form = SubjectForm()
    return render(request, "classes/subject_form.html", {"form": form, "title": "Add Subject", "cancel_url": "classes:subject_list"})


@staff_required
@require_http_methods(["GET", "POST"])
def subject_edit(request, pk):
    obj = get_object_or_404(Subject, pk=pk)
    if request.method == "POST":
        form = SubjectForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Subject updated successfully.")
            return redirect("classes:subject_list")
    else:
        form = SubjectForm(instance=obj)
    return render(request, "classes/subject_form.html", {"form": form, "title": "Edit Subject", "obj": obj, "cancel_url": "classes:subject_list"})


@staff_required
@require_http_methods(["POST"])
def subject_toggle(request, pk):
    obj = get_object_or_404(Subject, pk=pk)
    obj.is_active = not obj.is_active
    obj.save(update_fields=["is_active"])
    action = "activated" if obj.is_active else "deactivated"
    messages.success(request, f"Subject {obj.name} {action}.")
    return redirect("classes:subject_list")
