from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Q, Count
from datetime import date, datetime
import calendar
from .models import SavingGoal, SavingTransaction
from .forms import CreateGoalForm, AddSavingForm, WithdrawForm
from ledger.models import Transaction


POPULAR_EMOJIS = ['💻', '📱', '🏠', '🚗', '✈️', '🎮', '📚', '💍', '🏖️', '🎸', '📷', '⌚', '🏦', '💰', '🎯', '🌟']


def _balances(user):
    from ledger.models import Transaction
    qs = Transaction.objects.filter(user=user)
    agg = qs.aggregate(
        upi_income=Sum('amount', filter=Q(transaction_type="INCOME", money_type="UPI CASH")),
        upi_expense=Sum('amount', filter=Q(transaction_type="EXPENSE", money_type="UPI CASH")),
        upi_in_sw=Sum('amount', filter=Q(transaction_type="SWITCH", switch_direction="HAND_TO_UPI")),
        upi_out_sw=Sum('amount', filter=Q(transaction_type="SWITCH", switch_direction="UPI_TO_HAND")),
        upi_saving=Sum('amount', filter=Q(transaction_type="SAVING", money_type="UPI CASH")),
        hand_income=Sum('amount', filter=Q(transaction_type="INCOME", money_type="HAND CASH")),
        hand_expense=Sum('amount', filter=Q(transaction_type="EXPENSE", money_type="HAND CASH")),
        hand_in_sw=Sum('amount', filter=Q(transaction_type="SWITCH", switch_direction="UPI_TO_HAND")),
        hand_out_sw=Sum('amount', filter=Q(transaction_type="SWITCH", switch_direction="HAND_TO_UPI")),
        hand_saving=Sum('amount', filter=Q(transaction_type="SAVING", money_type="HAND CASH")),
    )
    def v(key):
        return float(agg.get(key) or 0)
    upi = v('upi_income') - v('upi_expense') + v('upi_in_sw') - v('upi_out_sw') - v('upi_saving')
    hand = v('hand_income') - v('hand_expense') + v('hand_in_sw') - v('hand_out_sw') - v('hand_saving')
    return upi, hand


def get_savings_stats(user):
    today = date.today()
    stats = SavingTransaction.objects.filter(user=user).aggregate(
        total_added=Sum('amount', filter=Q(transaction_type="ADD")),
        total_withdrawn=Sum('amount', filter=Q(transaction_type="WITHDRAW")),
        month_add=Sum('amount', filter=Q(transaction_type="ADD", date__year=today.year, date__month=today.month)),
        month_withdraw=Sum('amount', filter=Q(transaction_type="WITHDRAW", date__year=today.year, date__month=today.month)),
    )
    total_added = stats['total_added'] or 0
    total_withdrawn = stats['total_withdrawn'] or 0
    total_saved = total_added - total_withdrawn
    monthly_savings = (stats['month_add'] or 0) - (stats['month_withdraw'] or 0)

    goals = SavingGoal.objects.filter(user=user)
    goal_counts = goals.aggregate(
        active_count=Count('id', filter=~Q(status="COMPLETED")),
        completed_count=Count('id', filter=Q(status="COMPLETED")),
    )
    active_count = goal_counts['active_count'] or 0
    completed_count = goal_counts['completed_count'] or 0

    avg_progress = 0
    if active_count > 0:
        active_goals = list(goals.exclude(status="COMPLETED"))
        total_progress = sum(float(g.progress_percentage()) for g in active_goals)
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
    # Build list of (year, month) for last 6 months
    months = []
    m, y = today.month, today.year
    for _ in range(6):
        months.append((y, m))
        m -= 1
        if m < 1:
            m = 12
            y -= 1

    # Single bulk query for all 6 months
    from django.db.models import Q
    qs = SavingTransaction.objects.filter(
        user=request.user,
        date__year__in=[y for y, _ in months],
        date__month__in=[m for _, m in months],
    ).values('date__year', 'date__month', 'transaction_type').annotate(
        total=Sum('amount')
    )

    # Build lookup dict
    lookup = {}
    for row in qs:
        key = (row['date__year'], row['date__month'], row['transaction_type'])
        lookup[key] = row['total']

    monthly_data = []
    for y, m in reversed(months):  # oldest first
        adds = lookup.get((y, m, "ADD"), 0) or 0
        withdraws = lookup.get((y, m, "WITHDRAW"), 0) or 0
        monthly_data.append({
            "month": calendar.month_name[m],
            "year": y,
            "added": float(adds),
            "withdrawn": float(withdraws),
            "net": float(adds - withdraws),
        })

    return render(request, "savings/analytics.html", {"stats": stats, "goals": goals, "monthly_data": monthly_data})
