from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from datetime import date, datetime
import calendar
from .models import SavingGoal, SavingTransaction
from .forms import CreateGoalForm, AddSavingForm, WithdrawForm
from ledger.models import Transaction


POPULAR_EMOJIS = ['💻', '📱', '🏠', '🚗', '✈️', '🎮', '📚', '💍', '🏖️', '🎸', '📷', '⌚', '🏦', '💰', '🎯', '🌟']


def _balances(user):
    from ledger.models import Transaction
    qs = Transaction.objects.filter(user=user)
    upi_income = qs.filter(transaction_type="INCOME", money_type="UPI CASH").aggregate(t=Sum("amount"))["t"] or 0
    upi_expense = qs.filter(transaction_type="EXPENSE", money_type="UPI CASH").aggregate(t=Sum("amount"))["t"] or 0
    upi_from_sw = qs.filter(transaction_type="SWITCH", switch_direction="HAND_TO_UPI").aggregate(t=Sum("amount"))["t"] or 0
    upi_to_sw = qs.filter(transaction_type="SWITCH", switch_direction="UPI_TO_HAND").aggregate(t=Sum("amount"))["t"] or 0
    upi_saving = qs.filter(transaction_type="SAVING", money_type="UPI CASH").aggregate(t=Sum("amount"))["t"] or 0
    upi = upi_income - upi_expense + upi_from_sw - upi_to_sw - upi_saving

    hand_income = qs.filter(transaction_type="INCOME", money_type="HAND CASH").aggregate(t=Sum("amount"))["t"] or 0
    hand_expense = qs.filter(transaction_type="EXPENSE", money_type="HAND CASH").aggregate(t=Sum("amount"))["t"] or 0
    hand_from_sw = qs.filter(transaction_type="SWITCH", switch_direction="UPI_TO_HAND").aggregate(t=Sum("amount"))["t"] or 0
    hand_to_sw = qs.filter(transaction_type="SWITCH", switch_direction="HAND_TO_UPI").aggregate(t=Sum("amount"))["t"] or 0
    hand_saving = qs.filter(transaction_type="SAVING", money_type="HAND CASH").aggregate(t=Sum("amount"))["t"] or 0
    hand = hand_income - hand_expense + hand_from_sw - hand_to_sw - hand_saving
    return float(upi), float(hand)


def get_savings_stats(user):
    add_qs = SavingTransaction.objects.filter(user=user, transaction_type="ADD")
    withdraw_qs = SavingTransaction.objects.filter(user=user, transaction_type="WITHDRAW")

    total_added = add_qs.aggregate(t=Sum("amount"))["t"] or 0
    total_withdrawn = withdraw_qs.aggregate(t=Sum("amount"))["t"] or 0
    total_saved = total_added - total_withdrawn

    today = date.today()
    month_add = add_qs.filter(date__year=today.year, date__month=today.month).aggregate(t=Sum("amount"))["t"] or 0
    month_withdraw = withdraw_qs.filter(date__year=today.year, date__month=today.month).aggregate(t=Sum("amount"))["t"] or 0
    monthly_savings = month_add - month_withdraw

    goals = SavingGoal.objects.filter(user=user)
    active_count = goals.exclude(status="COMPLETED").count()
    completed_count = goals.filter(status="COMPLETED").count()

    avg_progress = 0
    if active_count > 0:
        total_progress = sum(float(g.progress_percentage()) for g in goals.exclude(status="COMPLETED"))
        avg_progress = total_progress / active_count

    level = int(total_saved / 10000) + 1
    xp = (total_saved % 10000) / 100
    saving_health_score = min(100, round(completed_count * 20 + avg_progress * 0.8))

    return {
        "total_saved": total_saved,
        "monthly_savings": monthly_savings,
        "total_added": total_added,
        "total_withdrawn": total_withdrawn,
        "level": level,
        "xp": xp,
        "saving_health_score": saving_health_score,
        "active_goals": active_count,
        "completed_goals": completed_count,
    }


@login_required
def saving_dashboard(request):
    goals = SavingGoal.objects.filter(user=request.user)
    stats = get_savings_stats(request.user)
    today = date.today()
    return render(request, "savings/dashboard.html", {"goals": goals, "stats": stats, "today": today})


@login_required
def create_goal(request):
    if request.method == "POST":
        form = CreateGoalForm(request.POST)
        if form.is_valid():
            goal = form.save(commit=False)
            goal.user = request.user
            goal.save()
            messages.success(request, f'Savings goal "{goal.title}" created! 🎯')
            return redirect("saving_dashboard")
    else:
        form = CreateGoalForm()

    return render(request, "savings/create_goal.html", {"form": form, "emojis": POPULAR_EMOJIS, "goal": None})


@login_required
def goal_detail(request, pk):
    goal = get_object_or_404(SavingGoal, pk=pk, user=request.user)
    transactions = goal.transactions.all()[:20]
    return render(request, "savings/goal_detail.html", {"goal": goal, "transactions": transactions})


@login_required
def add_saving(request, pk):
    goal = get_object_or_404(SavingGoal, pk=pk, user=request.user)
    upi_balance, hand_balance = _balances(request.user)
    goals = SavingGoal.objects.filter(user=request.user).exclude(status="COMPLETED")

    if request.method == "POST":
        form = AddSavingForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data["amount"]
            source = form.cleaned_data["source"]
            note = form.cleaned_data["note"]
            available = upi_balance if source == "UPI CASH" else hand_balance

            if float(amount) > max(0, available):
                messages.error(request, f"Insufficient {source} balance! Available: ₹{max(0, available):.2f}")
                return render(request, "savings/add_saving.html", {"form": form, "goal": goal, "upi_balance": upi_balance, "hand_balance": hand_balance, "goals": goals})

            goal.current_amount += amount
            goal.save()

            SavingTransaction.objects.create(
                user=request.user, saving_goal=goal,
                transaction_type="ADD", source=source,
                amount=amount, note=note or None, date=date.today(),
            )
            Transaction.objects.create(
                user=request.user,
                transaction_type="SAVING",
                money_type=source,
                amount=amount,
                category=f"Savings: {goal.title}",
                description=note or f"Saved to {goal.title}",
                date=date.today(),
            )
            return redirect("saving_dashboard")
    else:
        form = AddSavingForm()

    return render(request, "savings/add_saving.html", {"form": form, "goal": goal, "upi_balance": upi_balance, "hand_balance": hand_balance, "goals": goals})


@login_required
def withdraw_saving(request, pk):
    goal = get_object_or_404(SavingGoal, pk=pk, user=request.user)

    if goal.current_amount <= 0:
        messages.error(request, "No savings to withdraw from this goal.")
        return redirect("saving_dashboard")

    if request.method == "POST":
        form = WithdrawForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data["amount"]
            note = form.cleaned_data["note"]

            if amount > goal.current_amount:
                messages.error(request, f"Insufficient saved amount! Available: ₹{goal.current_amount:.2f}")
                return render(request, "savings/withdraw_saving.html", {"form": form, "goal": goal})

            goal.current_amount -= amount
            goal.save()

            SavingTransaction.objects.create(
                user=request.user, saving_goal=goal,
                transaction_type="WITHDRAW", source="UPI CASH",
                amount=amount, note=note or None, date=date.today(),
            )
            Transaction.objects.create(
                user=request.user,
                transaction_type="SAVING",
                money_type="UPI CASH",
                amount=-amount,
                category=f"Savings: {goal.title}",
                description=note or f"Withdrew from {goal.title}",
                date=date.today(),
            )
            return redirect("saving_dashboard")
    else:
        form = WithdrawForm()

    return render(request, "savings/withdraw_saving.html", {"form": form, "goal": goal})


@login_required
def delete_goal(request, pk):
    goal = get_object_or_404(SavingGoal, pk=pk, user=request.user)
    if request.method == "POST":
        goal.is_active = False
        goal.save()
        SavingTransaction.all_objects.filter(saving_goal=goal).update(is_active=False)
        return redirect("saving_dashboard")
    return render(request, "savings/confirm_delete.html", {"goal": goal})


@login_required
def edit_goal(request, pk):
    goal = get_object_or_404(SavingGoal, pk=pk, user=request.user)
    if request.method == "POST":
        form = CreateGoalForm(request.POST, instance=goal)
        if form.is_valid():
            form.save()
            messages.success(request, f'Goal "{goal.title}" updated!')
            return redirect("saving_dashboard")
    else:
        form = CreateGoalForm(instance=goal)

    return render(request, "savings/create_goal.html", {"form": form, "emojis": POPULAR_EMOJIS, "goal": goal})


@login_required
def saving_analytics(request):
    stats = get_savings_stats(request.user)
    goals = SavingGoal.objects.filter(user=request.user)

    today = date.today()
    monthly_data = []
    for i in range(6):
        m = today.month - i
        y = today.year
        while m < 1:
            m += 12
            y -= 1
        adds = SavingTransaction.objects.filter(
            user=request.user, transaction_type="ADD",
            date__year=y, date__month=m
        ).aggregate(t=Sum("amount"))["t"] or 0
        withdraws = SavingTransaction.objects.filter(
            user=request.user, transaction_type="WITHDRAW",
            date__year=y, date__month=m
        ).aggregate(t=Sum("amount"))["t"] or 0
        monthly_data.append({
            "month": calendar.month_name[m],
            "year": y,
            "added": float(adds),
            "withdrawn": float(withdraws),
            "net": float(adds - withdraws),
        })
    monthly_data.reverse()

    return render(request, "savings/analytics.html", {"stats": stats, "goals": goals, "monthly_data": monthly_data})
