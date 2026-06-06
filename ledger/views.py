from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Q
from django.http import JsonResponse
from django.core.paginator import Paginator
from .forms import TransactionForm, SwitchForm
from .models import Transaction, ActivityLog, WhatIfTransaction
from .balance_service import BalanceService


def is_whatif_mode(request):
    return request.session.get('whatif_mode', False)


@login_required
def toggle_whatif(request):
    if request.method == "POST":
        current = request.session.get('whatif_mode', False)
        if current:
            WhatIfTransaction.objects.filter(user=request.user).delete()
            request.session['whatif_mode'] = False
            messages.info(request, "What-If mode disabled. Temporary transactions cleared.")
        else:
            request.session['whatif_mode'] = True
    return redirect(request.POST.get('next', 'dashboard'))


@login_required
def add_transaction(request):
    whatif = is_whatif_mode(request)
    
    if request.method == "POST":
        form = TransactionForm(request.POST, user=request.user)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.user = request.user

            # Only compute balances when needed (POST with validation)
            upi_balance, hand_balance = BalanceService.for_user(request.user, whatif)

            if transaction.transaction_type == "SWITCH":
                transaction.category = "Money Transfer"

                if transaction.switch_direction == "UPI_TO_HAND":
                    if transaction.amount > upi_balance:
                        messages.error(request, f"⚠️ Insufficient UPI Cash balance! Available: ₹{upi_balance:.2f}, Required: ₹{transaction.amount}")
                        return render(request, "ledger/add_transaction.html", {
                            "form": form, 
                            "whatif": whatif,
                            "upi_balance": upi_balance,
                            "hand_balance": hand_balance
                        })

                elif transaction.switch_direction == "HAND_TO_UPI":
                    if transaction.amount > hand_balance:
                        messages.error(request, f"⚠️ Insufficient Hand Cash balance! Available: ₹{hand_balance:.2f}, Required: ₹{transaction.amount}")
                        return render(request, "ledger/add_transaction.html", {
                            "form": form, 
                            "whatif": whatif,
                            "upi_balance": upi_balance,
                            "hand_balance": hand_balance
                        })

            elif transaction.transaction_type == "EXPENSE":
                if transaction.money_type == "UPI CASH":
                    if transaction.amount > upi_balance:
                        messages.error(request, f"⚠️ Insufficient UPI Cash balance! Available: ₹{upi_balance:.2f}, Required: ₹{transaction.amount}")
                        return render(request, "ledger/add_transaction.html", {
                            "form": form, 
                            "whatif": whatif,
                            "upi_balance": upi_balance,
                            "hand_balance": hand_balance
                        })

                elif transaction.money_type == "HAND CASH":
                    if transaction.amount > hand_balance:
                        messages.error(request, f"⚠️ Insufficient Hand Cash balance! Available: ₹{hand_balance:.2f}, Required: ₹{transaction.amount}")
                        return render(request, "ledger/add_transaction.html", {
                            "form": form, 
                            "whatif": whatif,
                            "upi_balance": upi_balance,
                            "hand_balance": hand_balance
                        })

            if whatif:
                WhatIfTransaction.objects.create(
                    user=request.user,
                    transaction_type=transaction.transaction_type,
                    money_type=transaction.money_type,
                    amount=transaction.amount,
                    category=transaction.category,
                    description=transaction.description,
                    date=transaction.date,
                )
            else:
                transaction.save()
            return redirect("dashboard")
    else:
        form = TransactionForm(user=request.user)
        upi_balance, hand_balance = BalanceService.for_user(request.user, whatif)

    return render(request, "ledger/add_transaction.html", {
        "form": form, 
        "whatif": whatif,
        "upi_balance": upi_balance,
        "hand_balance": hand_balance
    })


@login_required
def switch_money(request):
    whatif = is_whatif_mode(request)
    if request.method == "POST":
        form = SwitchForm(request.POST)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.user = request.user
            transaction.transaction_type = "SWITCH"

            upi_balance, hand_balance = BalanceService.for_user(request.user, whatif)

            if transaction.switch_direction == "UPI_TO_HAND":
                if transaction.amount > upi_balance:
                    messages.error(request, f"⚠️ Insufficient UPI Cash balance! Available: ₹{upi_balance:.2f}, Required: ₹{transaction.amount}")
                    return render(request, "ledger/switch_money.html", {"form": form, "whatif": whatif})

            elif transaction.switch_direction == "HAND_TO_UPI":
                if transaction.amount > hand_balance:
                    messages.error(request, f"⚠️ Insufficient Hand Cash balance! Available: ₹{hand_balance:.2f}, Required: ₹{transaction.amount}")
                    return render(request, "ledger/switch_money.html", {"form": form, "whatif": whatif})

            transaction.category = "Money Transfer"

            if not transaction.description:
                transaction.description = f"Switched from {dict(transaction.SWITCH_DIRECTION)[transaction.switch_direction]}"

            if whatif:
                WhatIfTransaction.objects.create(
                    user=request.user,
                    transaction_type="SWITCH",
                    money_type=transaction.money_type,
                    switch_direction=transaction.switch_direction,
                    amount=transaction.amount,
                    category=transaction.category,
                    description=transaction.description,
                    date=transaction.date,
                )
            else:
                transaction.save()
            return redirect("dashboard")
    else:
        from datetime import date
        form = SwitchForm(initial={"date": date.today()})

    return render(request, "ledger/switch_money.html", {"form": form, "whatif": whatif})


@login_required
def edit_transaction(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk, user=request.user)
    is_switch = transaction.transaction_type == "SWITCH"

    # Capture original values before form binding modifies the instance
    orig_type = transaction.transaction_type
    orig_amount = float(transaction.amount)
    orig_money_type = transaction.money_type
    orig_switch_direction = transaction.switch_direction

    if request.method == "POST":
        form = SwitchForm(request.POST, instance=transaction) if is_switch else TransactionForm(request.POST, instance=transaction, user=request.user)
        if form.is_valid():
            form.save(commit=False)
            transaction.user = request.user
            if is_switch:
                transaction.transaction_type = "SWITCH"

            # --- Balance check on edit ---
            whatif = is_whatif_mode(request)
            upi_balance, hand_balance = BalanceService.for_user(request.user, whatif)

            # Reverse the original transaction's effect to get available balance
            if orig_type == "INCOME":
                if orig_money_type == "UPI CASH":
                    upi_balance -= orig_amount
                elif orig_money_type == "HAND CASH":
                    hand_balance -= orig_amount
            elif orig_type == "EXPENSE":
                if orig_money_type == "UPI CASH":
                    upi_balance += orig_amount
                elif orig_money_type == "HAND CASH":
                    hand_balance += orig_amount
            elif orig_type == "SWITCH":
                if orig_switch_direction == "UPI_TO_HAND":
                    upi_balance += orig_amount
                    hand_balance -= orig_amount
                elif orig_switch_direction == "HAND_TO_UPI":
                    hand_balance += orig_amount
                    upi_balance -= orig_amount

            # Check new transaction against adjusted balances
            amt = float(transaction.amount)
            if transaction.transaction_type == "EXPENSE":
                if transaction.money_type == "UPI CASH" and amt > upi_balance:
                    messages.error(request, f"⚠️ Insufficient UPI Cash balance! Available: ₹{upi_balance:.2f}, Shortfall: ₹{amt - upi_balance:.2f}")
                    template = "ledger/edit_switch.html" if is_switch else "ledger/edit_transaction.html"
                    return render(request, template, {"form": form, "transaction": transaction, "upi_balance": upi_balance, "hand_balance": hand_balance})
                elif transaction.money_type == "HAND CASH" and amt > hand_balance:
                    messages.error(request, f"⚠️ Insufficient Hand Cash balance! Available: ₹{hand_balance:.2f}, Shortfall: ₹{amt - hand_balance:.2f}")
                    template = "ledger/edit_switch.html" if is_switch else "ledger/edit_transaction.html"
                    return render(request, template, {"form": form, "transaction": transaction, "upi_balance": upi_balance, "hand_balance": hand_balance})

            elif transaction.transaction_type == "SWITCH":
                if transaction.switch_direction == "UPI_TO_HAND" and transaction.amount > upi_balance:
                    messages.error(request, f"⚠️ Insufficient UPI Cash balance! Available: ₹{upi_balance:.2f}, Shortfall: ₹{amt - upi_balance:.2f}")
                    return render(request, "ledger/edit_switch.html", {"form": form, "transaction": transaction, "upi_balance": upi_balance, "hand_balance": hand_balance})
                elif transaction.switch_direction == "HAND_TO_UPI" and transaction.amount > hand_balance:
                    messages.error(request, f"⚠️ Insufficient Hand Cash balance! Available: ₹{hand_balance:.2f}, Shortfall: ₹{amt - hand_balance:.2f}")
                    return render(request, "ledger/edit_switch.html", {"form": form, "transaction": transaction, "upi_balance": upi_balance, "hand_balance": hand_balance})
            # --- end balance check ---

            if transaction.transaction_type == "SWITCH":
                transaction.category = "Money Transfer"

            transaction.save()

            ActivityLog.objects.create(
                user=request.user,
                action="EDIT",
                transaction_type=transaction.transaction_type,
                amount=transaction.amount,
                category=transaction.category,
                description=transaction.description,
                date=transaction.date,
                money_type=transaction.money_type or "",
                changes="",
            )
            return redirect("dashboard")
    else:
        form = SwitchForm(instance=transaction) if is_switch else TransactionForm(instance=transaction, user=request.user)

    # Calculate adjusted balances for display
    whatif = is_whatif_mode(request)
    upi_balance, hand_balance = BalanceService.for_user(request.user, whatif)

    # Reverse original transaction effect for "available before this tx" balance
    if orig_type == "INCOME":
        if orig_money_type == "UPI CASH":
            upi_balance -= orig_amount
        elif orig_money_type == "HAND CASH":
            hand_balance -= orig_amount
    elif orig_type == "EXPENSE":
        if orig_money_type == "UPI CASH":
            upi_balance += orig_amount
        elif orig_money_type == "HAND CASH":
            hand_balance += orig_amount
    elif orig_type == "SWITCH":
        if orig_switch_direction == "UPI_TO_HAND":
            upi_balance += orig_amount
            hand_balance -= orig_amount
        elif orig_switch_direction == "HAND_TO_UPI":
            hand_balance += orig_amount
            upi_balance -= orig_amount

    template = "ledger/edit_switch.html" if is_switch else "ledger/edit_transaction.html"
    return render(request, template, {"form": form, "transaction": transaction, "upi_balance": upi_balance, "hand_balance": hand_balance})


@login_required
def edit_saving_transaction(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk, user=request.user)
    if transaction.transaction_type != "SAVING" or not transaction.category.startswith("Savings: "):
        messages.error(request, "This is not a savings transaction.")
        return redirect("dashboard")

    from savings.models import SavingGoal, SavingTransaction
    goal_title = transaction.category.replace("Savings: ", "", 1)
    goal = SavingGoal.all_objects.filter(user=request.user, title=goal_title).first()
    st = None
    if goal:
        if transaction.amount >= 0:
            st = SavingTransaction.all_objects.filter(
                user=request.user, saving_goal=goal,
                transaction_type="ADD", amount=transaction.amount,
                date=transaction.date, is_active=True,
            ).first()
        else:
            st = SavingTransaction.all_objects.filter(
                user=request.user, saving_goal=goal,
                transaction_type="WITHDRAW", amount=abs(transaction.amount),
                date=transaction.date, is_active=True,
            ).first()

    from decimal import Decimal
    upi_balance, hand_balance = BalanceService.for_user(request.user)
    ctx = {"transaction": transaction, "goal": goal, "st": st, "upi_balance": upi_balance, "hand_balance": hand_balance}

    if request.method == "POST":
        new_amount = request.POST.get("amount")
        new_money_type = request.POST.get("money_type")
        new_date = request.POST.get("date")
        new_description = request.POST.get("description", "")

        if not new_amount:
            messages.error(request, "Amount is required.")
            return render(request, "ledger/edit_saving.html", ctx)
        try:
            new_amount = float(new_amount)
            if new_amount <= 0:
                messages.error(request, "Amount must be positive.")
                return render(request, "ledger/edit_saving.html", ctx)
        except ValueError:
            messages.error(request, "Invalid amount.")
            return render(request, "ledger/edit_saving.html", ctx)

        if not new_date:
            messages.error(request, "Date is required.")
            return render(request, "ledger/edit_saving.html", ctx)

        orig_abs_amount = float(abs(transaction.amount))
        orig_date = transaction.date

        if goal and st:
            if new_amount != orig_abs_amount:
                diff = Decimal(str(new_amount - orig_abs_amount))
                if st.transaction_type == "ADD":
                    goal.current_amount += diff
                else:
                    goal.current_amount -= diff
                goal.save()
                st.amount = Decimal(str(new_amount))
            if new_money_type != st.source:
                st.source = new_money_type
            if new_date != str(orig_date):
                from datetime import datetime
                st.date = datetime.strptime(new_date, "%Y-%m-%d").date()
            st.save()

        transaction.amount = Decimal(str(new_amount)) if transaction.amount >= 0 else -Decimal(str(new_amount))
        transaction.money_type = new_money_type
        from datetime import datetime as dt
        transaction.date = dt.strptime(new_date, "%Y-%m-%d").date()
        transaction.description = new_description
        transaction.save()

        ActivityLog.objects.create(
            user=request.user, action="EDIT",
            transaction_type="SAVING", amount=transaction.amount,
            category=transaction.category, description=transaction.description,
            date=transaction.date, money_type=transaction.money_type or "",
            changes="",
        )
        return redirect("dashboard")

    return render(request, "ledger/edit_saving.html", ctx)


@login_required
def delete_transaction(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk, user=request.user)
    if request.method == "POST":
        if transaction.transaction_type == "SAVING" and transaction.category.startswith("Savings: "):
            from savings.models import SavingGoal, SavingTransaction
            goal_title = transaction.category.replace("Savings: ", "", 1)
            goal = SavingGoal.all_objects.filter(user=request.user, title=goal_title).first()
            if goal:
                if transaction.amount >= 0:
                    st = SavingTransaction.all_objects.filter(
                        user=request.user, saving_goal=goal,
                        transaction_type="ADD", amount=transaction.amount,
                        date=transaction.date, is_active=True,
                    ).first()
                    adj = -transaction.amount
                else:
                    st = SavingTransaction.all_objects.filter(
                        user=request.user, saving_goal=goal,
                        transaction_type="WITHDRAW", amount=abs(transaction.amount),
                        date=transaction.date, is_active=True,
                    ).first()
                    adj = abs(transaction.amount)
                if st:
                    st.is_active = False
                    st.save()
                    if goal.is_active:
                        goal.current_amount += adj
                        goal.save()

        ActivityLog.objects.create(
            user=request.user,
            action="DELETE",
            transaction_type=transaction.transaction_type,
            amount=transaction.amount,
            category=transaction.category,
            description=transaction.description,
            date=transaction.date,
            money_type=transaction.money_type or "",
            changes="",
        )
        transaction.is_active = False
        transaction.save()
        return redirect("dashboard")
    return redirect("dashboard")


@login_required
def toggle_pin(request, pk):
    if request.method == "POST" and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        transaction = get_object_or_404(Transaction, pk=pk, user=request.user)
        transaction.is_pinned = not transaction.is_pinned
        transaction.save(update_fields=['is_pinned'])
        return JsonResponse({'success': True, 'is_pinned': transaction.is_pinned})
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)


@login_required
def edit_whatif_transaction(request, pk):
    wi = get_object_or_404(WhatIfTransaction, pk=pk, user=request.user)
    from .forms import CATEGORY_CHOICES

    whatif = is_whatif_mode(request)
    upi_balance, hand_balance = BalanceService.for_user(request.user, whatif)

    ctx = {"wi": wi, "CATEGORY_CHOICES": CATEGORY_CHOICES, "upi_balance": upi_balance, "hand_balance": hand_balance}

    if request.method == "POST":
        transaction_type = request.POST.get("transaction_type")
        amount = request.POST.get("amount")
        money_type = request.POST.get("money_type")
        category = request.POST.get("category")
        description = request.POST.get("description", "")
        date_str = request.POST.get("date")

        if not all([transaction_type, amount, date_str]):
            messages.error(request, "Required fields missing.")
            return render(request, "ledger/edit_whatif.html", ctx)

        try:
            from decimal import Decimal
            amount = Decimal(str(float(amount)))
            if amount <= 0:
                messages.error(request, "Amount must be positive.")
                return render(request, "ledger/edit_whatif.html", ctx)
        except (ValueError, TypeError):
            messages.error(request, "Invalid amount.")
            return render(request, "ledger/edit_whatif.html", ctx)

        from datetime import datetime
        wi.transaction_type = transaction_type
        wi.amount = amount
        wi.money_type = money_type
        wi.category = category
        wi.description = description
        wi.date = datetime.strptime(date_str, "%Y-%m-%d").date()
        if transaction_type == "SWITCH":
            wi.switch_direction = request.POST.get("switch_direction", "")
        wi.save()
        return redirect("dashboard")

    return render(request, "ledger/edit_whatif.html", ctx)


@login_required
def confirm_whatif_transaction(request, pk):
    """Promote a single What-If transaction to a real transaction."""
    if request.method == "POST":
        wi = get_object_or_404(WhatIfTransaction, pk=pk, user=request.user)
        Transaction.objects.create(
            user=request.user,
            transaction_type=wi.transaction_type,
            money_type=wi.money_type,
            switch_direction=wi.switch_direction,
            amount=wi.amount,
            category=wi.category,
            description=wi.description,
            date=wi.date,
        )
        wi.delete()
    return redirect("dashboard")


@login_required
def activity_log(request):
    logs = ActivityLog.objects.filter(user=request.user)
    paginator = Paginator(logs, 50)
    logs_page = paginator.get_page(request.GET.get("page", 1))
    return render(request, "ledger/activity_log.html", {"logs": logs_page})
