import csv
import io
import zipfile
from datetime import datetime

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from django.http import JsonResponse, HttpResponse
from .forms import TransactionForm, SwitchForm
from .models import Transaction, ActivityLog, WhatIfTransaction


def _user_balances(user, whatif=False):
    real_qs = Transaction.objects.filter(user=user)
    wi_qs = WhatIfTransaction.objects.filter(user=user) if whatif else WhatIfTransaction.objects.none()

    upi_income = (real_qs.filter(transaction_type="INCOME", money_type="UPI CASH").aggregate(t=Sum("amount"))["t"] or 0) + (wi_qs.filter(transaction_type="INCOME", money_type="UPI CASH").aggregate(t=Sum("amount"))["t"] or 0)
    upi_expense = (real_qs.filter(transaction_type="EXPENSE", money_type="UPI CASH").aggregate(t=Sum("amount"))["t"] or 0) + (wi_qs.filter(transaction_type="EXPENSE", money_type="UPI CASH").aggregate(t=Sum("amount"))["t"] or 0)
    upi_from_switch = real_qs.filter(transaction_type="SWITCH", switch_direction="HAND_TO_UPI").aggregate(t=Sum("amount"))["t"] or 0
    upi_to_switch = real_qs.filter(transaction_type="SWITCH", switch_direction="UPI_TO_HAND").aggregate(t=Sum("amount"))["t"] or 0
    upi_saving = real_qs.filter(transaction_type="SAVING", money_type="UPI CASH").aggregate(t=Sum("amount"))["t"] or 0
    upi_balance = upi_income - upi_expense + upi_from_switch - upi_to_switch - upi_saving

    hand_income = (real_qs.filter(transaction_type="INCOME", money_type="HAND CASH").aggregate(t=Sum("amount"))["t"] or 0) + (wi_qs.filter(transaction_type="INCOME", money_type="HAND CASH").aggregate(t=Sum("amount"))["t"] or 0)
    hand_expense = (real_qs.filter(transaction_type="EXPENSE", money_type="HAND CASH").aggregate(t=Sum("amount"))["t"] or 0) + (wi_qs.filter(transaction_type="EXPENSE", money_type="HAND CASH").aggregate(t=Sum("amount"))["t"] or 0)
    hand_from_switch = real_qs.filter(transaction_type="SWITCH", switch_direction="UPI_TO_HAND").aggregate(t=Sum("amount"))["t"] or 0
    hand_to_switch = real_qs.filter(transaction_type="SWITCH", switch_direction="HAND_TO_UPI").aggregate(t=Sum("amount"))["t"] or 0
    hand_saving = real_qs.filter(transaction_type="SAVING", money_type="HAND CASH").aggregate(t=Sum("amount"))["t"] or 0
    hand_balance = hand_income - hand_expense + hand_from_switch - hand_to_switch - hand_saving

    return upi_balance, hand_balance


def is_whatif_mode(request):
    return request.session.get('whatif_mode', False)


def _csv_bytes(header, rows):
    """Build one UTF-8 CSV (with BOM so Excel renders ₹/emoji) as bytes."""
    buf = io.StringIO()
    buf.write("﻿")
    writer = csv.writer(buf)
    writer.writerow(header)
    for row in rows:
        writer.writerow(row)
    return buf.getvalue().encode("utf-8")


@login_required
def export_transactions(request):
    """
    Download ALL of the user's data as a ZIP of CSV files:
    transactions, budgets, saving goals, saving transactions and notes.

    Replaces the old client-side DOM scraper (which only saw the current
    paginated page and broke on pages without a table). Each managed queryset
    uses the default `objects` manager, so soft-deleted rows are excluded.
    """
    from .models import Budget
    from savings.models import SavingGoal, SavingTransaction
    from notes.models import Note

    user = request.user

    transactions_csv = _csv_bytes(
        ["Date", "Type", "Category", "Amount", "Money Type", "Switch Direction", "Description"],
        (
            [
                t.date.strftime("%Y-%m-%d"),
                t.get_transaction_type_display(),
                t.category,
                t.amount,
                t.get_money_type_display(),
                t.get_switch_direction_display() if t.switch_direction else "",
                t.description,
            ]
            for t in Transaction.objects.filter(user=user).order_by("-date", "-id")
        ),
    )

    budgets_csv = _csv_bytes(
        ["Category", "Amount", "Period", "Month", "Year", "Alert Threshold %"],
        (
            [b.category, b.amount, b.get_period_display(), b.month, b.year, b.alert_threshold]
            for b in Budget.objects.filter(user=user).order_by("-year", "-month", "category")
        ),
    )

    saving_goals_csv = _csv_bytes(
        ["Title", "Target Amount", "Current Amount", "Status", "Deadline", "Description", "Created"],
        (
            [
                g.title,
                g.target_amount,
                g.current_amount,
                g.get_status_display(),
                g.deadline.strftime("%Y-%m-%d") if g.deadline else "",
                g.description or "",
                g.created_at.strftime("%Y-%m-%d"),
            ]
            for g in SavingGoal.objects.filter(user=user).order_by("-created_at")
        ),
    )

    saving_transactions_csv = _csv_bytes(
        ["Date", "Goal", "Type", "Source", "Amount", "Note"],
        (
            [
                s.date.strftime("%Y-%m-%d"),
                s.saving_goal.title if s.saving_goal_id else "",
                s.get_transaction_type_display(),
                s.get_source_display(),
                s.amount,
                s.note or "",
            ]
            for s in SavingTransaction.objects.filter(user=user)
            .select_related("saving_goal")
            .order_by("-date", "-created_at")
        ),
    )

    notes_csv = _csv_bytes(
        ["Date", "Title", "Category", "Priority", "Color", "Pinned", "Content"],
        (
            [
                n.date.strftime("%Y-%m-%d"),
                n.title,
                n.get_category_display(),
                n.get_priority_display(),
                n.get_color_display(),
                "Yes" if n.is_pinned else "No",
                n.content,
            ]
            for n in Note.objects.filter(user=user).order_by("-updated_at")
        ),
    )

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("transactions.csv", transactions_csv)
        zf.writestr("budgets.csv", budgets_csv)
        zf.writestr("saving_goals.csv", saving_goals_csv)
        zf.writestr("saving_transactions.csv", saving_transactions_csv)
        zf.writestr("notes.csv", notes_csv)

    stamp = datetime.now().strftime("%Y-%m-%d")
    response = HttpResponse(zip_buffer.getvalue(), content_type="application/zip")
    response["Content-Disposition"] = f'attachment; filename="moneylogger_export_{stamp}.zip"'
    return response


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
    upi_balance, hand_balance = _user_balances(request.user, whatif)
    
    if request.method == "POST":
        form = TransactionForm(request.POST, user=request.user)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.user = request.user

            if transaction.transaction_type == "SWITCH":
                upi_balance, hand_balance = _user_balances(request.user, whatif)
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
                upi_balance, hand_balance = _user_balances(request.user, whatif)

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
            upi_balance, hand_balance = _user_balances(request.user, whatif)

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
    upi_balance, hand_balance = _user_balances(request.user, whatif)

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

    real_qs = Transaction.objects.filter(user=request.user)
    upi_income = real_qs.filter(transaction_type="INCOME", money_type="UPI CASH").aggregate(t=Sum("amount"))["t"] or 0
    upi_expense = real_qs.filter(transaction_type="EXPENSE", money_type="UPI CASH").aggregate(t=Sum("amount"))["t"] or 0
    upi_from_sw = real_qs.filter(transaction_type="SWITCH", switch_direction="HAND_TO_UPI").aggregate(t=Sum("amount"))["t"] or 0
    upi_to_sw = real_qs.filter(transaction_type="SWITCH", switch_direction="UPI_TO_HAND").aggregate(t=Sum("amount"))["t"] or 0
    upi_saving = real_qs.filter(transaction_type="SAVING", money_type="UPI CASH").aggregate(t=Sum("amount"))["t"] or 0
    upi_balance = upi_income - upi_expense + upi_from_sw - upi_to_sw - upi_saving
    hand_income = real_qs.filter(transaction_type="INCOME", money_type="HAND CASH").aggregate(t=Sum("amount"))["t"] or 0
    hand_expense = real_qs.filter(transaction_type="EXPENSE", money_type="HAND CASH").aggregate(t=Sum("amount"))["t"] or 0
    hand_from_sw = real_qs.filter(transaction_type="SWITCH", switch_direction="UPI_TO_HAND").aggregate(t=Sum("amount"))["t"] or 0
    hand_to_sw = real_qs.filter(transaction_type="SWITCH", switch_direction="HAND_TO_UPI").aggregate(t=Sum("amount"))["t"] or 0
    hand_saving = real_qs.filter(transaction_type="SAVING", money_type="HAND CASH").aggregate(t=Sum("amount"))["t"] or 0
    hand_balance = hand_income - hand_expense + hand_from_sw - hand_to_sw - hand_saving
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
                from decimal import Decimal
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
        messages.success(request, "Transaction deleted.")
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
    upi_balance, hand_balance = _user_balances(request.user, whatif)

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
        messages.success(request, "Simulated transaction updated.")
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
        messages.success(request, f"✅ Simulated transaction of ₹{wi.amount} confirmed and saved.")
    return redirect("dashboard")


@login_required
def activity_log(request):
    logs = ActivityLog.objects.filter(user=request.user)
    return render(request, "ledger/activity_log.html", {"logs": logs})
