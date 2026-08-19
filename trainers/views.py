from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from accounts.permissions import staff_required
from sessions.models import Session

from .forms import TrainerCreateForm, TrainerEditForm
from .models import TrainerProfile


@staff_required
def trainer_list(request):
    query = request.GET.get("q", "").strip()
    only_active = request.GET.get("active", "") == "1"
    only_inactive = request.GET.get("inactive", "") == "1"

    trainers = (
        TrainerProfile.objects.select_related("user")
        .annotate(
            sessions_count=Count("sessions", distinct=True),
        )
        .order_by("full_name")
    )
    if query:
        trainers = trainers.filter(
            Q(full_name__icontains=query)
            | Q(employee_id__icontains=query)
            | Q(phone_number__icontains=query)
            | Q(user__username__icontains=query)
        )
    if only_active:
        trainers = trainers.filter(is_active=True)
    if only_inactive:
        trainers = trainers.filter(is_active=False)

    page_obj = Paginator(trainers, 20).get_page(request.GET.get("page"))

    context = {
        "trainers": page_obj,
        "query": query,
        "only_active": only_active,
        "only_inactive": only_inactive,
    }
    return render(request, "trainers/trainer_list.html", context)


@staff_required
@require_http_methods(["GET", "POST"])
def trainer_create(request):
    if request.method == "POST":
        form = TrainerCreateForm(request.POST)
        if form.is_valid():
            profile = form.save()
            messages.success(
                request,
                f"Trainer {profile.full_name} created successfully.",
            )
            return redirect("trainers:trainer_list")
    else:
        form = TrainerCreateForm()
    return render(request, "trainers/trainer_form.html", {"form": form, "title": "Add Trainer", "cancel_url": "trainers:trainer_list"})


@staff_required
@require_http_methods(["GET", "POST"])
def trainer_edit(request, pk):
    profile = get_object_or_404(TrainerProfile, pk=pk)
    if request.method == "POST":
        form = TrainerEditForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Trainer updated successfully.")
            return redirect("trainers:trainer_list")
    else:
        form = TrainerEditForm(instance=profile)
    return render(request, "trainers/trainer_form.html", {"form": form, "title": "Edit Trainer", "profile": profile, "cancel_url": "trainers:trainer_list"})


@staff_required
@require_http_methods(["POST"])
def trainer_toggle(request, pk):
    profile = get_object_or_404(TrainerProfile, pk=pk)
    profile.is_active = not profile.is_active
    profile.user.is_active = profile.is_active
    profile.user.save(update_fields=["is_active"])
    profile.save(update_fields=["is_active", "updated_at"])
    action = "activated" if profile.is_active else "deactivated"
    messages.success(request, f"Trainer {profile.full_name} {action}.")
    return redirect(request.POST.get("next") or "trainers:trainer_list")
