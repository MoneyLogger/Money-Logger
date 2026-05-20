from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from .forms import TransactionForm, SwitchForm
from .models import Transaction, ActivityLog, WhatIfTransaction


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
            messages.success(request, "What-If mode enabled. Transactions are temporary.")
    return redirect(request.POST.get('next', 'dashboard'))


@login_required
def add_transaction(request):
    whatif = is_whatif_mode(request)
    
    # Calculate current balances for display
    real_qs = Transaction.objects.filter(user=request.user)
    wi_qs = WhatIfTransaction.objects.filter(user=request.user) if whatif else WhatIfTransaction.objects.none()
    
    upi_income = (real_qs.filter(transaction_type="INCOME", money_type="UPI CASH").aggregate(t=Sum("amount"))["t"] or 0) + (wi_qs.filter(transaction_type="INCOME", money_type="UPI CASH").aggregate(t=Sum("amount"))["t"] or 0)
    upi_expense = (real_qs.filter(transaction_type="EXPENSE", money_type="UPI CASH").aggregate(t=Sum("amount"))["t"] or 0) + (wi_qs.filter(transaction_type="EXPENSE", money_type="UPI CASH").aggregate(t=Sum("amount"))["t"] or 0)
    upi_from_switch = real_qs.filter(transaction_type="SWITCH", switch_direction="HAND_TO_UPI").aggregate(t=Sum("amount"))["t"] or 0
    upi_to_switch = real_qs.filter(transaction_type="SWITCH", switch_direction="UPI_TO_HAND").aggregate(t=Sum("amount"))["t"] or 0
    upi_balance = upi_income - upi_expense + upi_from_switch - upi_to_switch
    
    hand_income = (real_qs.filter(transaction_type="INCOME", money_type="HAND CASH").aggregate(t=Sum("amount"))["t"] or 0) + (wi_qs.filter(transaction_type="INCOME", money_type="HAND CASH").aggregate(t=Sum("amount"))["t"] or 0)
    hand_expense = (real_qs.filter(transaction_type="EXPENSE", money_type="HAND CASH").aggregate(t=Sum("amount"))["t"] or 0) + (wi_qs.filter(transaction_type="EXPENSE", money_type="HAND CASH").aggregate(t=Sum("amount"))["t"] or 0)
    hand_from_switch = real_qs.filter(transaction_type="SWITCH", switch_direction="UPI_TO_HAND").aggregate(t=Sum("amount"))["t"] or 0
    hand_to_switch = real_qs.filter(transaction_type="SWITCH", switch_direction="HAND_TO_UPI").aggregate(t=Sum("amount"))["t"] or 0
    hand_balance = hand_income - hand_expense + hand_from_switch - hand_to_switch
    
    if request.method == "POST":
        form = TransactionForm(request.POST, user=request.user)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.user = request.user

            if transaction.transaction_type == "SWITCH":
                real_qs = Transaction.objects.filter(user=request.user)
                wi_qs = WhatIfTransaction.objects.filter(user=request.user) if whatif else WhatIfTransaction.objects.none()

                transaction.category = "Money Transfer"

                if transaction.switch_direction == "UPI_TO_HAND":
                    upi_income = (real_qs.filter(transaction_type="INCOME", money_type="UPI CASH").aggregate(t=Sum("amount"))["t"] or 0) + (wi_qs.filter(transaction_type="INCOME", money_type="UPI CASH").aggregate(t=Sum("amount"))["t"] or 0)
                    upi_expense = (real_qs.filter(transaction_type="EXPENSE", money_type="UPI CASH").aggregate(t=Sum("amount"))["t"] or 0) + (wi_qs.filter(transaction_type="EXPENSE", money_type="UPI CASH").aggregate(t=Sum("amount"))["t"] or 0)
                    upi_from_switch = real_qs.filter(transaction_type="SWITCH", switch_direction="HAND_TO_UPI").aggregate(t=Sum("amount"))["t"] or 0
                    upi_to_switch = real_qs.filter(transaction_type="SWITCH", switch_direction="UPI_TO_HAND").aggregate(t=Sum("amount"))["t"] or 0
                    upi_balance = upi_income - upi_expense + upi_from_switch - upi_to_switch
                    if transaction.amount > upi_balance:
                        messages.error(request, f"⚠️ Insufficient UPI Cash balance! Available: ₹{upi_balance:.2f}, Required: ₹{transaction.amount}")
                        return render(request, "ledger/add_transaction.html", {
                            "form": form, 
                            "whatif": whatif,
                            "upi_balance": upi_balance,
                            "hand_balance": hand_balance
                        })

                elif transaction.switch_direction == "HAND_TO_UPI":
                    hand_income = (real_qs.filter(transaction_type="INCOME", money_type="HAND CASH").aggregate(t=Sum("amount"))["t"] or 0) + (wi_qs.filter(transaction_type="INCOME", money_type="HAND CASH").aggregate(t=Sum("amount"))["t"] or 0)
                    hand_expense = (real_qs.filter(transaction_type="EXPENSE", money_type="HAND CASH").aggregate(t=Sum("amount"))["t"] or 0) + (wi_qs.filter(transaction_type="EXPENSE", money_type="HAND CASH").aggregate(t=Sum("amount"))["t"] or 0)
                    hand_from_switch = real_qs.filter(transaction_type="SWITCH", switch_direction="UPI_TO_HAND").aggregate(t=Sum("amount"))["t"] or 0
                    hand_to_switch = real_qs.filter(transaction_type="SWITCH", switch_direction="HAND_TO_UPI").aggregate(t=Sum("amount"))["t"] or 0
                    hand_balance = hand_income - hand_expense + hand_from_switch - hand_to_switch
                    if transaction.amount > hand_balance:
                        messages.error(request, f"⚠️ Insufficient Hand Cash balance! Available: ₹{hand_balance:.2f}, Required: ₹{transaction.amount}")
                        return render(request, "ledger/add_transaction.html", {
                            "form": form, 
                            "whatif": whatif,
                            "upi_balance": upi_balance,
                            "hand_balance": hand_balance
                        })

            elif transaction.transaction_type == "EXPENSE":
                real_qs = Transaction.objects.filter(user=request.user)
                wi_qs = WhatIfTransaction.objects.filter(user=request.user) if whatif else WhatIfTransaction.objects.none()

                if transaction.money_type == "UPI CASH":
                    upi_income = (real_qs.filter(transaction_type="INCOME", money_type="UPI CASH").aggregate(t=Sum("amount"))["t"] or 0) + (wi_qs.filter(transaction_type="INCOME", money_type="UPI CASH").aggregate(t=Sum("amount"))["t"] or 0)
                    upi_expense = (real_qs.filter(transaction_type="EXPENSE", money_type="UPI CASH").aggregate(t=Sum("amount"))["t"] or 0) + (wi_qs.filter(transaction_type="EXPENSE", money_type="UPI CASH").aggregate(t=Sum("amount"))["t"] or 0)
                    upi_from_switch = real_qs.filter(transaction_type="SWITCH", switch_direction="HAND_TO_UPI").aggregate(t=Sum("amount"))["t"] or 0
                    upi_to_switch = real_qs.filter(transaction_type="SWITCH", switch_direction="UPI_TO_HAND").aggregate(t=Sum("amount"))["t"] or 0
                    upi_balance = upi_income - upi_expense + upi_from_switch - upi_to_switch
                    if transaction.amount > upi_balance:
                        messages.error(request, f"⚠️ Insufficient UPI Cash balance! Available: ₹{upi_balance:.2f}, Required: ₹{transaction.amount}")
                        return render(request, "ledger/add_transaction.html", {
                            "form": form, 
                            "whatif": whatif,
                            "upi_balance": upi_balance,
                            "hand_balance": hand_balance
                        })

                elif transaction.money_type == "HAND CASH":
                    hand_income = (real_qs.filter(transaction_type="INCOME", money_type="HAND CASH").aggregate(t=Sum("amount"))["t"] or 0) + (wi_qs.filter(transaction_type="INCOME", money_type="HAND CASH").aggregate(t=Sum("amount"))["t"] or 0)
                    hand_expense = (real_qs.filter(transaction_type="EXPENSE", money_type="HAND CASH").aggregate(t=Sum("amount"))["t"] or 0) + (wi_qs.filter(transaction_type="EXPENSE", money_type="HAND CASH").aggregate(t=Sum("amount"))["t"] or 0)
                    hand_from_switch = real_qs.filter(transaction_type="SWITCH", switch_direction="UPI_TO_HAND").aggregate(t=Sum("amount"))["t"] or 0
                    hand_to_switch = real_qs.filter(transaction_type="SWITCH", switch_direction="HAND_TO_UPI").aggregate(t=Sum("amount"))["t"] or 0
                    hand_balance = hand_income - hand_expense + hand_from_switch - hand_to_switch
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

            real_qs = Transaction.objects.filter(user=request.user)
            wi_qs = WhatIfTransaction.objects.filter(user=request.user) if whatif else WhatIfTransaction.objects.none()

            if transaction.switch_direction == "UPI_TO_HAND":
                upi_income = (real_qs.filter(transaction_type="INCOME", money_type="UPI CASH").aggregate(t=Sum("amount"))["t"] or 0) + (wi_qs.filter(transaction_type="INCOME", money_type="UPI CASH").aggregate(t=Sum("amount"))["t"] or 0)
                upi_expense = (real_qs.filter(transaction_type="EXPENSE", money_type="UPI CASH").aggregate(t=Sum("amount"))["t"] or 0) + (wi_qs.filter(transaction_type="EXPENSE", money_type="UPI CASH").aggregate(t=Sum("amount"))["t"] or 0)
                upi_from_switch = real_qs.filter(transaction_type="SWITCH", switch_direction="HAND_TO_UPI").aggregate(t=Sum("amount"))["t"] or 0
                upi_to_switch = real_qs.filter(transaction_type="SWITCH", switch_direction="UPI_TO_HAND").aggregate(t=Sum("amount"))["t"] or 0
                upi_balance = upi_income - upi_expense + upi_from_switch - upi_to_switch
                if transaction.amount > upi_balance:
                    messages.error(request, f"⚠️ Insufficient UPI Cash balance! Available: ₹{upi_balance:.2f}, Required: ₹{transaction.amount}")
                    return render(request, "ledger/switch_money.html", {"form": form, "whatif": whatif})

            elif transaction.switch_direction == "HAND_TO_UPI":
                hand_income = (real_qs.filter(transaction_type="INCOME", money_type="HAND CASH").aggregate(t=Sum("amount"))["t"] or 0) + (wi_qs.filter(transaction_type="INCOME", money_type="HAND CASH").aggregate(t=Sum("amount"))["t"] or 0)
                hand_expense = (real_qs.filter(transaction_type="EXPENSE", money_type="HAND CASH").aggregate(t=Sum("amount"))["t"] or 0) + (wi_qs.filter(transaction_type="EXPENSE", money_type="HAND CASH").aggregate(t=Sum("amount"))["t"] or 0)
                hand_from_switch = real_qs.filter(transaction_type="SWITCH", switch_direction="UPI_TO_HAND").aggregate(t=Sum("amount"))["t"] or 0
                hand_to_switch = real_qs.filter(transaction_type="SWITCH", switch_direction="HAND_TO_UPI").aggregate(t=Sum("amount"))["t"] or 0
                hand_balance = hand_income - hand_expense + hand_from_switch - hand_to_switch
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
                    category=transaction.category,  # Use the category from form or None
                    description=transaction.description,
                    date=transaction.date,
                )
            else:
                transaction.save()
            return redirect("dashboard")
    else:
        form = SwitchForm()

    return render(request, "ledger/switch_money.html", {"form": form, "whatif": whatif})


@login_required
def edit_transaction(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk, user=request.user)
    is_switch = transaction.transaction_type == "SWITCH"

    # Capture original values before form binding modifies the instance
    orig_type = transaction.transaction_type
    orig_amount = transaction.amount
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
            real_qs = Transaction.objects.filter(user=request.user)
            wi_qs = WhatIfTransaction.objects.filter(user=request.user) if whatif else WhatIfTransaction.objects.none()

            upi_income = (real_qs.filter(transaction_type="INCOME", money_type="UPI CASH").aggregate(t=Sum("amount"))["t"] or 0) + (wi_qs.filter(transaction_type="INCOME", money_type="UPI CASH").aggregate(t=Sum("amount"))["t"] or 0)
            upi_expense = (real_qs.filter(transaction_type="EXPENSE", money_type="UPI CASH").aggregate(t=Sum("amount"))["t"] or 0) + (wi_qs.filter(transaction_type="EXPENSE", money_type="UPI CASH").aggregate(t=Sum("amount"))["t"] or 0)
            upi_from_switch = real_qs.filter(transaction_type="SWITCH", switch_direction="HAND_TO_UPI").aggregate(t=Sum("amount"))["t"] or 0
            upi_to_switch = real_qs.filter(transaction_type="SWITCH", switch_direction="UPI_TO_HAND").aggregate(t=Sum("amount"))["t"] or 0
            upi_balance = upi_income - upi_expense + upi_from_switch - upi_to_switch

            hand_income = (real_qs.filter(transaction_type="INCOME", money_type="HAND CASH").aggregate(t=Sum("amount"))["t"] or 0) + (wi_qs.filter(transaction_type="INCOME", money_type="HAND CASH").aggregate(t=Sum("amount"))["t"] or 0)
            hand_expense = (real_qs.filter(transaction_type="EXPENSE", money_type="HAND CASH").aggregate(t=Sum("amount"))["t"] or 0) + (wi_qs.filter(transaction_type="EXPENSE", money_type="HAND CASH").aggregate(t=Sum("amount"))["t"] or 0)
            hand_from_switch = real_qs.filter(transaction_type="SWITCH", switch_direction="UPI_TO_HAND").aggregate(t=Sum("amount"))["t"] or 0
            hand_to_switch = real_qs.filter(transaction_type="SWITCH", switch_direction="HAND_TO_UPI").aggregate(t=Sum("amount"))["t"] or 0
            hand_balance = hand_income - hand_expense + hand_from_switch - hand_to_switch

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
            if transaction.transaction_type == "EXPENSE":
                if transaction.money_type == "UPI CASH" and transaction.amount > upi_balance:
                    messages.error(request, f"⚠️ Insufficient UPI Cash balance! Available: ₹{upi_balance:.2f}, Shortfall: ₹{transaction.amount - upi_balance:.2f}")
                    template = "ledger/edit_switch.html" if is_switch else "ledger/edit_transaction.html"
                    return render(request, template, {"form": form, "transaction": transaction, "upi_balance": upi_balance, "hand_balance": hand_balance})
                elif transaction.money_type == "HAND CASH" and transaction.amount > hand_balance:
                    messages.error(request, f"⚠️ Insufficient Hand Cash balance! Available: ₹{hand_balance:.2f}, Shortfall: ₹{transaction.amount - hand_balance:.2f}")
                    template = "ledger/edit_switch.html" if is_switch else "ledger/edit_transaction.html"
                    return render(request, template, {"form": form, "transaction": transaction, "upi_balance": upi_balance, "hand_balance": hand_balance})

            elif transaction.transaction_type == "SWITCH":
                if transaction.switch_direction == "UPI_TO_HAND" and transaction.amount > upi_balance:
                    messages.error(request, f"⚠️ Insufficient UPI Cash balance! Available: ₹{upi_balance:.2f}, Shortfall: ₹{transaction.amount - upi_balance:.2f}")
                    return render(request, "ledger/edit_switch.html", {"form": form, "transaction": transaction, "upi_balance": upi_balance, "hand_balance": hand_balance})
                elif transaction.switch_direction == "HAND_TO_UPI" and transaction.amount > hand_balance:
                    messages.error(request, f"⚠️ Insufficient Hand Cash balance! Available: ₹{hand_balance:.2f}, Shortfall: ₹{transaction.amount - hand_balance:.2f}")
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
            messages.success(request, "Transaction updated successfully!")
            return redirect("dashboard")
    else:
        form = SwitchForm(instance=transaction) if is_switch else TransactionForm(instance=transaction, user=request.user)

    # Calculate adjusted balances for display
    whatif = is_whatif_mode(request)
    real_qs = Transaction.objects.filter(user=request.user)
    wi_qs = WhatIfTransaction.objects.filter(user=request.user) if whatif else WhatIfTransaction.objects.none()

    upi_income = (real_qs.filter(transaction_type="INCOME", money_type="UPI CASH").aggregate(t=Sum("amount"))["t"] or 0) + (wi_qs.filter(transaction_type="INCOME", money_type="UPI CASH").aggregate(t=Sum("amount"))["t"] or 0)
    upi_expense = (real_qs.filter(transaction_type="EXPENSE", money_type="UPI CASH").aggregate(t=Sum("amount"))["t"] or 0) + (wi_qs.filter(transaction_type="EXPENSE", money_type="UPI CASH").aggregate(t=Sum("amount"))["t"] or 0)
    upi_from_switch = real_qs.filter(transaction_type="SWITCH", switch_direction="HAND_TO_UPI").aggregate(t=Sum("amount"))["t"] or 0
    upi_to_switch = real_qs.filter(transaction_type="SWITCH", switch_direction="UPI_TO_HAND").aggregate(t=Sum("amount"))["t"] or 0
    upi_balance = upi_income - upi_expense + upi_from_switch - upi_to_switch

    hand_income = (real_qs.filter(transaction_type="INCOME", money_type="HAND CASH").aggregate(t=Sum("amount"))["t"] or 0) + (wi_qs.filter(transaction_type="INCOME", money_type="HAND CASH").aggregate(t=Sum("amount"))["t"] or 0)
    hand_expense = (real_qs.filter(transaction_type="EXPENSE", money_type="HAND CASH").aggregate(t=Sum("amount"))["t"] or 0) + (wi_qs.filter(transaction_type="EXPENSE", money_type="HAND CASH").aggregate(t=Sum("amount"))["t"] or 0)
    hand_from_switch = real_qs.filter(transaction_type="SWITCH", switch_direction="UPI_TO_HAND").aggregate(t=Sum("amount"))["t"] or 0
    hand_to_switch = real_qs.filter(transaction_type="SWITCH", switch_direction="HAND_TO_UPI").aggregate(t=Sum("amount"))["t"] or 0
    hand_balance = hand_income - hand_expense + hand_from_switch - hand_to_switch

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
def delete_transaction(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk, user=request.user)
    if request.method == "POST":
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
        transaction.delete()
        messages.success(request, "Transaction deleted.")
        return redirect("dashboard")
    return redirect("dashboard")


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
        messages.success(request, f"✅ Simulated transaction of ₹{wi.amount} confirmed and saved.")
    return redirect("dashboard")


@login_required
def activity_log(request):
    logs = ActivityLog.objects.filter(user=request.user)
    return render(request, "ledger/activity_log.html", {"logs": logs})
