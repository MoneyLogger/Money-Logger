from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Sum, Q, Count
from django.db.models.functions import TruncDate, TruncMonth
from datetime import datetime, date, timedelta
import calendar
import math
from ledger.models import Transaction, WhatIfTransaction, Budget
from savings.models import SavingGoal, SavingTransaction
from notes.models import Note
from ledger.views import is_whatif_mode
from ledger.balance_service import BalanceService
from savings.views import get_savings_stats as _savings_stats
from django.template.loader import render_to_string
from django.http import JsonResponse, HttpResponse


def _survival_warning(available_funds, expense_mtd, days_passed, days_left, today_expense):
    avg_daily = float(expense_mtd) / days_passed if days_passed > 0 else 0
    projected_end = float(available_funds) - avg_daily * days_left
    survive = projected_end >= 0

    health = 100
    if expense_mtd > 0 and float(expense_mtd) > float(available_funds):
        health -= 20
    if projected_end < 0:
        health -= 30
    if avg_daily > 0 and today_expense > avg_daily * 1.5:
        health -= 15

    days_until_broke = broke_date = None
    if not survive and avg_daily > 0:
        days_until_broke = math.ceil(float(available_funds) / avg_daily)
        if days_until_broke < 365:
            broke_date = date.today() + timedelta(days=days_until_broke)

    msg = ""
    if today_expense > avg_daily * 1.5 and avg_daily > 0:
        msg = f"⚠️ You spent ₹{today_expense:.0f} today — {((today_expense/avg_daily - 1)*100):.0f}% above your daily average of ₹{avg_daily:.0f}"
    elif not survive:
        if broke_date:
            msg = f"🚨 At current rate, funds may run out in {days_until_broke} days (by {broke_date.strftime('%d %b, %Y')})"
        else:
            msg = "🚨 Critical: Insufficient funds for the month"
    elif health < 50:
        msg = "🚨 Financial health is at risk — review spending immediately"
    elif health < 70:
        msg = "⚠️ Caution: Your spending patterns need attention"

    return avg_daily, projected_end, survive, health, days_until_broke, broke_date, msg


# ── views ─────────────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    whatif = is_whatif_mode(request)
    base_wi  = WhatIfTransaction.objects.filter(user=request.user) if whatif else WhatIfTransaction.objects.none()
    base_real = Transaction.objects.filter(user=request.user)

    start_date       = request.GET.get("start_date")
    end_date         = request.GET.get("end_date")
    category         = request.GET.get("category")
    transaction_type = request.GET.get("transaction_type")
    money_type       = request.GET.get("money_type")
    search           = request.GET.get("search", "").strip()
    page             = request.GET.get("page", 1)

    real_qs = base_real.order_by('-id')
    wi_qs   = base_wi

    if start_date:
        try:
            real_qs = real_qs.filter(date__gte=datetime.strptime(start_date, "%Y-%m-%d").date())
            wi_qs   = wi_qs.filter(date__gte=datetime.strptime(start_date, "%Y-%m-%d").date())
        except ValueError:
            pass
    if end_date:
        try:
            real_qs = real_qs.filter(date__lte=datetime.strptime(end_date, "%Y-%m-%d").date())
            wi_qs   = wi_qs.filter(date__lte=datetime.strptime(end_date, "%Y-%m-%d").date())
        except ValueError:
            pass
    if category:
        real_qs = real_qs.filter(category__icontains=category)
        wi_qs   = wi_qs.filter(category__icontains=category)
    if transaction_type:
        real_qs = real_qs.filter(transaction_type=transaction_type)
        wi_qs   = wi_qs.filter(transaction_type=transaction_type)
    if money_type:
        real_qs = real_qs.filter(money_type=money_type)
        wi_qs   = wi_qs.filter(money_type=money_type)

    if search:
        q_filter = (
            Q(description__icontains=search) |
            Q(category__icontains=search) |
            Q(transaction_type__icontains=search) |
            Q(money_type__icontains=search)
        )
        try:
            q_filter |= Q(amount=float(search))
        except ValueError:
            pass
        try:
            parsed = datetime.strptime(search, "%Y-%m-%d").date()
            q_filter |= Q(date=parsed)
        except ValueError:
            pass
        real_qs = real_qs.filter(q_filter)
        wi_qs   = wi_qs.filter(q_filter)

    # Merge real + whatif into a combined list for the table
    real_list = list(real_qs)
    wi_list   = [t for t in wi_qs.order_by('-date')]
    for t in wi_list:
        t.is_whatif = True          # flag for template badge
    combined = sorted(real_list + wi_list, key=lambda t: (-int(getattr(t, 'is_pinned', False)), 0 if getattr(t, 'is_whatif', False) else 1, -t.date.toordinal()))

    paginator         = Paginator(combined, 10)
    transactions_page = paginator.get_page(page)

    # Use base (unfiltered) querysets for all aggregates
    all_totals = base_real.aggregate(
        income=Sum('amount', filter=Q(transaction_type="INCOME")),
        expense=Sum('amount', filter=Q(transaction_type="EXPENSE")),
    )
    wi_totals = base_wi.aggregate(
        income=Sum('amount', filter=Q(transaction_type="INCOME")),
        expense=Sum('amount', filter=Q(transaction_type="EXPENSE")),
    )
    total_income  = (all_totals['income'] or 0) + (wi_totals['income'] or 0)
    total_expense = (all_totals['expense'] or 0) + (wi_totals['expense'] or 0)
    balance       = total_income - total_expense

    # Calculate savings rate and financial health
    savings_rate = ((total_income - total_expense) / total_income * 100) if total_income > 0 else 0
    is_healthy = balance >= 0 and savings_rate > 20

    upi_balance, hand_balance = BalanceService(base_real, base_wi).compute()
    savings_data = _savings_stats(request.user) if request.user.is_authenticated else {"total_saved": 0}
    total_saved = savings_data["total_saved"]

    today        = date.today()
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    days_passed  = max(1, today.day)
    days_left    = days_in_month - today.day

    # Single aggregate for month expense data
    month_real = base_real.filter(date__year=today.year, date__month=today.month)
    month_wi   = base_wi.filter(date__year=today.year, date__month=today.month)
    month_agg = month_real.aggregate(
        expense_mtd=Sum('amount', filter=Q(transaction_type="EXPENSE", date__lte=today)),
        today_expense=Sum('amount', filter=Q(transaction_type="EXPENSE", date=today)),
    )
    month_wi_agg = month_wi.aggregate(
        expense_mtd=Sum('amount', filter=Q(transaction_type="EXPENSE", date__lte=today)),
        today_expense=Sum('amount', filter=Q(transaction_type="EXPENSE", date=today)),
    )
    expense_mtd   = (month_agg['expense_mtd'] or 0) + (month_wi_agg['expense_mtd'] or 0)
    today_expense = float((month_agg['today_expense'] or 0) + (month_wi_agg['today_expense'] or 0))
    spendable_funds = float(upi_balance) + float(hand_balance)
    available_funds = spendable_funds

    avg_daily, projected_end, survive, health, days_until_broke, broke_date, warning_message = \
        _survival_warning(available_funds, expense_mtd, days_passed, days_left, today_expense)
    
    categories = base_real.exclude(transaction_type__in=["SWITCH", "SAVING"]).values_list('category', flat=True).distinct().order_by('category')
    
    balance_without_savings = balance - total_saved

    context = {
        "transactions": transactions_page,
        "total_income": total_income,
        "total_expense": total_expense,
        "balance": balance,
        "balance_without_savings": balance_without_savings,
        "total_saved": total_saved,
        "spendable_balance": spendable_funds,
        "savings_rate": savings_rate,
        "is_healthy": is_healthy,
        "upi_balance": upi_balance,
        "hand_balance": hand_balance,
        "search": search,
        "start_date": start_date,
        "end_date": end_date,
        "category": category,
        "transaction_type": transaction_type,
        "money_type": money_type,
        "categories": categories,
        "transaction_types": [("INCOME", "Income"), ("EXPENSE", "Expense"), ("SWITCH", "Switch"), ("SAVING", "Saving")],
        "money_types": [("UPI CASH", "UPI Cash"), ("HAND CASH", "Hand Cash")],
        "warning_message": warning_message,
        "whatif": whatif,
    }

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        html = render_to_string('dashboard/_transactions_table.html', context, request=request)
        return JsonResponse({'html': html})

    return render(request, "dashboard/dashboard.html", context)


@login_required
def analytics(request):
    from calendar import month_name as _month_name
    whatif = is_whatif_mode(request)

    current_date   = datetime.now()
    selected_month = int(request.GET.get('month', current_date.month))
    selected_year  = int(request.GET.get('year', current_date.year))

    real_all = Transaction.objects.filter(user=request.user)
    wi_all   = WhatIfTransaction.objects.filter(user=request.user) if whatif else WhatIfTransaction.objects.none()

    # Single aggregate for all-time totals
    all_agg = real_all.aggregate(
        income=Sum('amount', filter=Q(transaction_type="INCOME")),
        expense=Sum('amount', filter=Q(transaction_type="EXPENSE")),
        count=Count('id'),
    )
    wi_agg = wi_all.aggregate(
        income=Sum('amount', filter=Q(transaction_type="INCOME")),
        expense=Sum('amount', filter=Q(transaction_type="EXPENSE")),
        count=Count('id'),
    )
    total_income  = (all_agg['income'] or 0) + (wi_agg['income'] or 0)
    total_expense = (all_agg['expense'] or 0) + (wi_agg['expense'] or 0)
    balance       = total_income - total_expense
    total_transactions = (all_agg['count'] or 0) + (wi_agg['count'] or 0)

    # Single aggregate for selected month totals
    month_real = real_all.filter(date__year=selected_year, date__month=selected_month)
    month_wi   = wi_all.filter(date__year=selected_year, date__month=selected_month)
    month_agg = month_real.aggregate(
        income=Sum('amount', filter=Q(transaction_type="INCOME")),
        expense=Sum('amount', filter=Q(transaction_type="EXPENSE")),
        count=Count('id'),
    )
    month_wi_agg = month_wi.aggregate(
        income=Sum('amount', filter=Q(transaction_type="INCOME")),
        expense=Sum('amount', filter=Q(transaction_type="EXPENSE")),
        count=Count('id'),
    )
    month_income  = (month_agg['income'] or 0) + (month_wi_agg['income'] or 0)
    month_expense = (month_agg['expense'] or 0) + (month_wi_agg['expense'] or 0)
    month_balance = month_income - month_expense
    month_transaction_count = (month_agg['count'] or 0) + (month_wi_agg['count'] or 0)

    # Category breakdown — single bulk query per type
    from collections import defaultdict
    def category_totals(real_qs, wi_qs, ttype):
        d = defaultdict(float)
        for row in real_qs.filter(transaction_type=ttype).values("category").annotate(t=Sum("amount")):
            d[row["category"]] += float(row["t"])
        for row in wi_qs.filter(transaction_type=ttype).values("category").annotate(t=Sum("amount")):
            d[row["category"]] += float(row["t"])
        return sorted([{"category": k, "total": v} for k, v in d.items()], key=lambda x: -x["total"])

    # Single bulk query for daily chart (2 queries instead of looping per type)
    days_in_month = calendar.monthrange(selected_year, selected_month)[1]
    daily_labels  = [str(i) for i in range(1, days_in_month + 1)]
    daily_income  = [0.0] * days_in_month
    daily_expense = [0.0] * days_in_month

    daily_real = month_real.values('date', 'transaction_type').annotate(t=Sum('amount'))
    daily_wi   = month_wi.values('date', 'transaction_type').annotate(t=Sum('amount'))
    for t in list(daily_real) + list(daily_wi):
        idx = t['date'].day - 1
        if t['transaction_type'] == 'INCOME':
            daily_income[idx] += float(t['t'])
        elif t['transaction_type'] == 'EXPENSE':
            daily_expense[idx] += float(t['t'])

    # Yearly chart — single bulk query
    month_labels   = [_month_name[i] for i in range(1, 13)]
    yearly_income  = [0.0] * 12
    yearly_expense = [0.0] * 12

    year_real = real_all.filter(date__year=selected_year).values('date__month', 'transaction_type').annotate(t=Sum('amount'))
    year_wi   = wi_all.filter(date__year=selected_year).values('date__month', 'transaction_type').annotate(t=Sum('amount'))
    for t in list(year_real) + list(year_wi):
        idx = t['date__month'] - 1
        if t['transaction_type'] == 'INCOME':
            yearly_income[idx] += float(t['t'])
        elif t['transaction_type'] == 'EXPENSE':
            yearly_expense[idx] += float(t['t'])

    # Category breakdown (2 queries total for both types)
    category_expense = category_totals(month_real, month_wi, "EXPENSE")
    category_income  = category_totals(month_real, month_wi, "INCOME")

    # Navigation
    current_month_date = datetime(selected_year, selected_month, 1)
    prev_month_date    = current_month_date - timedelta(days=1)
    next_month_date    = (current_month_date.replace(day=28) + timedelta(days=4))
    next_month_date    = next_month_date - timedelta(days=next_month_date.day - 1)

    # Warning
    today        = datetime.now().date()
    days_in_month_now = calendar.monthrange(today.year, today.month)[1]
    days_passed  = max(1, today.day)
    days_left    = days_in_month_now - today.day
    upi_balance, hand_balance = BalanceService(real_all, wi_all).compute()
    savings_data_analytics = _savings_stats(request.user)
    spendable_funds_analytics = float(upi_balance) + float(hand_balance)
    available_funds = spendable_funds_analytics
    month_real_now = real_all.filter(date__year=today.year, date__month=today.month)
    month_wi_now   = wi_all.filter(date__year=today.year, date__month=today.month)
    warn_agg = month_real_now.aggregate(
        expense_mtd=Sum('amount', filter=Q(transaction_type="EXPENSE", date__lte=today)),
        today_expense=Sum('amount', filter=Q(transaction_type="EXPENSE", date=today)),
    )
    warn_wi_agg = month_wi_now.aggregate(
        expense_mtd=Sum('amount', filter=Q(transaction_type="EXPENSE", date__lte=today)),
        today_expense=Sum('amount', filter=Q(transaction_type="EXPENSE", date=today)),
    )
    expense_mtd    = (warn_agg['expense_mtd'] or 0) + (warn_wi_agg['expense_mtd'] or 0)
    today_expense  = float((warn_agg['today_expense'] or 0) + (warn_wi_agg['today_expense'] or 0))
    _, _, _, _, _, _, warning_message = _survival_warning(available_funds, expense_mtd, days_passed, days_left, today_expense)

    context = {
        "total_income": total_income, "total_expense": total_expense, "balance": balance,
        "total_transactions": total_transactions,
        "month_income": month_income, "month_expense": month_expense,
        "month_balance": month_balance, "month_transaction_count": month_transaction_count,
        "category_expense": category_expense, "category_income": category_income,
        "selected_month": selected_month, "selected_year": selected_year,
        "month_name": _month_name[selected_month],
        "prev_month": prev_month_date.month, "prev_year": prev_month_date.year,
        "next_month": next_month_date.month, "next_year": next_month_date.year,
        "daily_labels": daily_labels, "daily_income": daily_income, "daily_expense": daily_expense,
        "month_labels": month_labels, "yearly_income": yearly_income, "yearly_expense": yearly_expense,
        "warning_message": warning_message,
        "whatif": whatif,
    }
    return render(request, "dashboard/analytics.html", context)


@login_required
def survival_dashboard(request):
    whatif = is_whatif_mode(request)
    today  = date.today()
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    days_passed   = max(1, today.day)
    days_left     = days_in_month - today.day

    real_all = Transaction.objects.filter(user=request.user)
    wi_all   = WhatIfTransaction.objects.filter(user=request.user) if whatif else WhatIfTransaction.objects.none()

    # Single aggregate for current month
    month_real = real_all.filter(date__year=today.year, date__month=today.month)
    month_wi   = wi_all.filter(date__year=today.year, date__month=today.month)

    m_agg = month_real.aggregate(
        income=Sum('amount', filter=Q(transaction_type="INCOME")),
        expense_mtd=Sum('amount', filter=Q(transaction_type="EXPENSE", date__lte=today)),
        today_expense=Sum('amount', filter=Q(transaction_type="EXPENSE", date=today)),
    )
    m_wi_agg = month_wi.aggregate(
        income=Sum('amount', filter=Q(transaction_type="INCOME")),
        expense_mtd=Sum('amount', filter=Q(transaction_type="EXPENSE", date__lte=today)),
        today_expense=Sum('amount', filter=Q(transaction_type="EXPENSE", date=today)),
    )
    income_mtd  = (m_agg['income'] or 0) + (m_wi_agg['income'] or 0)
    expense_mtd = (m_agg['expense_mtd'] or 0) + (m_wi_agg['expense_mtd'] or 0)
    net_mtd     = income_mtd - expense_mtd

    upi_balance, hand_balance = BalanceService(real_all, wi_all).compute()
    savings_data = _savings_stats(request.user)
    total_saved = savings_data["total_saved"]
    spendable_funds = float(upi_balance) + float(hand_balance)
    available_funds = spendable_funds

    today_expense = float((m_agg['today_expense'] or 0) + (m_wi_agg['today_expense'] or 0))

    avg_daily, projected_end, survive, health_score, days_until_broke, broke_date, warning_message = \
        _survival_warning(available_funds, expense_mtd, days_passed, days_left, today_expense)

    spending_difference = today_expense - avg_daily
    remaining_budget = max(0, avg_daily - today_expense)

    # Weekly spending and income — 2 bulk queries (real + wi) instead of 4
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    real_week = month_real.filter(date__gte=week_start, date__lte=week_end)
    wi_week = month_wi.filter(date__gte=week_start, date__lte=week_end)

    week_exp = {}
    for r in real_week.filter(transaction_type="EXPENSE").annotate(day=TruncDate('date')).values('day').annotate(t=Sum('amount')):
        week_exp[r['day']] = float(r['t'])
    for r in wi_week.filter(transaction_type="EXPENSE").annotate(day=TruncDate('date')).values('day').annotate(t=Sum('amount')):
        week_exp[r['day']] = week_exp.get(r['day'], 0) + float(r['t'])

    week_inc = {}
    for r in real_week.filter(transaction_type="INCOME").annotate(day=TruncDate('date')).values('day').annotate(t=Sum('amount')):
        week_inc[r['day']] = float(r['t'])
    for r in wi_week.filter(transaction_type="INCOME").annotate(day=TruncDate('date')).values('day').annotate(t=Sum('amount')):
        week_inc[r['day']] = week_inc.get(r['day'], 0) + float(r['t'])

    week_data = []
    for i in range(7):
        day = week_start + timedelta(days=i)
        if day.month == today.month:
            week_data.append({
                'day': day.strftime('%a'),
                'date': day.strftime('%m/%d'),
                'full_date': day,
                'expense': week_exp.get(day, 0),
                'income': week_inc.get(day, 0),
                'is_today': day == today
            })
    week_total_expense = sum(d['expense'] for d in week_data)
    week_total_income = sum(d['income'] for d in week_data)

    if health_score >= 80:
        health_status, health_color = "Healthy ✅", "#2ecc71"
    elif health_score >= 50:
        health_status, health_color = "Caution ⚠️", "#f39c12"
    else:
        health_status, health_color = "Risk 🚨", "#e74c3c"

    # AI Insights
    insights = []
    
    if avg_daily > 0:
        if today_expense > avg_daily:
            overspend_pct = ((today_expense - avg_daily) / avg_daily * 100)
            insights.append({
                'type': 'warning',
                'message': f"You are overspending by {overspend_pct:.0f}%! Reduce daily spending to ₹{avg_daily:.0f}."
            })
        else:
            insights.append({
                'type': 'success', 
                'message': f"Great job! You're spending wisely. Keep daily spending under ₹{avg_daily:.0f}."
            })
    
    if days_until_broke and days_until_broke < days_left:
        insights.append({
            'type': 'danger',
            'message': f"⚠️ You will run out of money in {days_until_broke} days if you continue at this rate!"
        })
    else:
        days_funds_last = int(available_funds / avg_daily) if avg_daily > 0 else 999
        insights.append({
            'type': 'info',
            'message': f"You have enough funds to last {days_funds_last} days at your current spending rate."
        })
    
    if today_expense > avg_daily:
        insights.append({
            'type': 'warning',
            'message': f"Today's spending (₹{today_expense:.0f}) exceeds your safe limit!"
        })
    else:
        remaining_today = max(0, avg_daily - today_expense)
        if remaining_today > 0:
            insights.append({
                'type': 'success',
                'message': f"Today you've spent ₹{today_expense:.0f} - ₹{remaining_today:.0f} left!"
            })
        else:
            insights.append({
                'type': 'success',
                'message': f"Today you've spent ₹{today_expense:.0f} - on track!"
            })
    
    # Last month comparison — single aggregate
    last_month = today.replace(day=1) - timedelta(days=1)
    lm_real = real_all.filter(date__year=last_month.year, date__month=last_month.month)
    lm_wi   = wi_all.filter(date__year=last_month.year, date__month=last_month.month)
    lm_agg = lm_real.aggregate(
        expense=Sum('amount', filter=Q(transaction_type="EXPENSE")),
        income=Sum('amount', filter=Q(transaction_type="INCOME")),
    )
    lm_wi_agg = lm_wi.aggregate(
        expense=Sum('amount', filter=Q(transaction_type="EXPENSE")),
        income=Sum('amount', filter=Q(transaction_type="INCOME")),
    )
    last_expense = (lm_agg['expense'] or 0) + (lm_wi_agg['expense'] or 0)
    last_income = (lm_agg['income'] or 0) + (lm_wi_agg['income'] or 0)

    if last_expense > 0:
        chg = ((float(expense_mtd) - float(last_expense)) / float(last_expense)) * 100
        if chg > 25:
            insights.append({
                'type': 'warning',
                'message': f"📈 Spending {chg:.0f}% more than last month"
            })
        elif chg < -15:
            insights.append({
                'type': 'success',
                'message': f"📉 Great! Reduced spending by {abs(chg):.0f}% from last month"
            })

    # Category comparison — 2 bulk queries (last month + current month) instead of 4
    from collections import defaultdict
    lm_cats = {}
    for r in list(lm_real.filter(transaction_type="EXPENSE").values("category").annotate(t=Sum("amount"))) + \
             list(lm_wi.filter(transaction_type="EXPENSE").values("category").annotate(t=Sum("amount"))):
        lm_cats[r['category']] = lm_cats.get(r['category'], 0) + float(r['t'])

    cur_cats_d = defaultdict(float)
    for r in list(month_real.filter(transaction_type="EXPENSE").values("category").annotate(t=Sum("amount"))) + \
             list(month_wi.filter(transaction_type="EXPENSE").values("category").annotate(t=Sum("amount"))):
        cur_cats_d[r['category']] += float(r['t'])
    for cat, amt in sorted(cur_cats_d.items(), key=lambda x: -x[1])[:3]:
        last = lm_cats.get(cat, 0)
        if last > 0 and ((amt - last) / last * 100) > 30:
            insights.append({
                'type': 'warning',
                'message': f"🔥 {cat} spike (+{((amt-last)/last*100):.0f}%)"
            })

    cur_savings  = float(income_mtd) - float(expense_mtd)
    last_savings = float(last_income) - float(last_expense)
    if cur_savings > last_savings + 1000:
        insights.append({
            'type': 'success',
            'message': f"💰 Saved ₹{cur_savings - last_savings:.0f} more than last month"
        })

    if survive:
        insights.append({
            'type': 'success',
            'message': f"✅ On track to end month with ₹{projected_end:.0f}"
        })

    context = {
        "income_mtd": income_mtd, "expense_mtd": expense_mtd, "net_mtd": net_mtd,
        "upi_balance": upi_balance, "hand_balance": hand_balance,
        "available_funds": available_funds,
        "total_saved": total_saved,
        "spendable_balance": spendable_funds,
        "avg_daily_spend": avg_daily,
        "projected_remaining_spend": avg_daily * days_left,
        "projected_end_balance": projected_end,
        "survive": survive, "days_left": days_left,
        "days_until_broke": days_until_broke, "broke_date": broke_date,
        "health_score": health_score, "health_status": health_status, "health_color": health_color,
        "days_passed": days_passed, "days_in_month": days_in_month,
        "warning_message": warning_message,
        "insights": insights[:3],
        "today_expense": today_expense,
        "spending_difference": spending_difference,
        "remaining_budget": remaining_budget,
        "week_data": week_data, 
        "week_total_expense": week_total_expense,
        "week_total_income": week_total_income,
        "whatif": whatif,
    }
    return render(request, "dashboard/survival.html", context)


# ── Budget Views ──────────────────────────────────────────────────────────────

@login_required
def budget_list(request):
    """Display all budgets for the current month"""
    from ledger.models import Budget
    from collections import defaultdict
    
    whatif = is_whatif_mode(request)
    real_all = Transaction.objects.filter(user=request.user)
    wi_all = WhatIfTransaction.objects.filter(user=request.user) if whatif else WhatIfTransaction.objects.none()
    
    # Get current month and year
    today = datetime.now()
    selected_month = int(request.GET.get('month', today.month))
    selected_year = int(request.GET.get('year', today.year))
    
    # Get budgets for selected month
    budgets = Budget.objects.filter(
        user=request.user,
        month=selected_month,
        year=selected_year
    )
    
    # Calculate spent amounts for each budget (bulk query instead of N+1)
    budget_data = []
    total_budget = 0
    total_spent = 0

    # Bulk fetch all transactions for the selected period (2 queries instead of N*8)
    all_txns = Transaction.objects.filter(
        user=request.user,
        date__year=selected_year,
        date__month=selected_month,
        transaction_type__in=["EXPENSE", "INCOME"]
    ).values('category', 'transaction_type').annotate(t=Sum('amount'))

    all_wi_txns = wi_all.filter(
        date__year=selected_year,
        date__month=selected_month,
        transaction_type__in=["EXPENSE", "INCOME"]
    ).values('category', 'transaction_type').annotate(t=Sum('amount'))

    from collections import defaultdict
    category_data = defaultdict(lambda: {'expense': 0.0, 'income': 0.0})
    for row in all_txns:
        key = 'expense' if row['transaction_type'] == 'EXPENSE' else 'income'
        category_data[row['category']][key] += float(row['t'])
    for row in all_wi_txns:
        key = 'expense' if row['transaction_type'] == 'EXPENSE' else 'income'
        category_data[row['category']][key] += float(row['t'])

    for budget in budgets:
        cat = category_data.get(budget.category, {'expense': 0.0, 'income': 0.0})
        expenses = cat['expense']
        income = cat['income']
        spent = max(0, expenses - income)
        remaining = float(budget.amount) - spent
        percentage = (spent / float(budget.amount) * 100) if float(budget.amount) > 0 else 0

        status = 'safe'
        if spent > float(budget.amount):
            status = 'danger'
        elif percentage >= budget.alert_threshold:
            status = 'warning'
        
        budget_data.append({
            'budget': budget,
            'spent': spent,
            'remaining': remaining,
            'percentage': percentage,
            'status': status
        })
        
        total_budget += float(budget.amount)
        total_spent += spent
    
    total_remaining = total_budget - total_spent
    total_percentage = (total_spent / total_budget * 100) if total_budget > 0 else 0
    
    # Month navigation
    from calendar import month_name as _month_name
    current_month_date = datetime(selected_year, selected_month, 1)
    prev_month_date = current_month_date - timedelta(days=1)
    next_month_date = (current_month_date.replace(day=28) + timedelta(days=4))
    next_month_date = next_month_date - timedelta(days=next_month_date.day - 1)
    
    context = {
        'budget_data': budget_data,
        'total_budget': total_budget,
        'total_spent': total_spent,
        'total_remaining': total_remaining,
        'total_percentage': total_percentage,
        'selected_month': selected_month,
        'selected_year': selected_year,
        'month_name': _month_name[selected_month],
        'prev_month': prev_month_date.month,
        'prev_year': prev_month_date.year,
        'prev_month_name': _month_name[prev_month_date.month],
        'next_month': next_month_date.month,
        'next_year': next_month_date.year,
        'next_month_name': _month_name[next_month_date.month],
        'current_month': today.month,
        'current_year': today.year,
        'is_current_period': selected_month == today.month and selected_year == today.year,
        'whatif': whatif,
    }

    return render(request, 'dashboard/budget.html', context)


@login_required
def budget_create(request):
    """Create a new budget"""
    from ledger.models import Budget
    from ledger.forms import BudgetForm
    from django.shortcuts import redirect
    from django.contrib import messages
    
    if request.method == 'POST':
        form = BudgetForm(request.POST, user=request.user)
        if form.is_valid():
            budget = form.save(commit=False)
            budget.user = request.user

            existing = Budget.all_objects.filter(
                user=request.user,
                category=budget.category,
                month=budget.month,
                year=budget.year,
                period=budget.period,
            ).first()

            if existing:
                if existing.is_active:
                    messages.error(request, f'Budget for {budget.category} already exists for this period.')
                else:
                    existing.is_active = True
                    existing.amount = budget.amount
                    existing.alert_threshold = budget.alert_threshold
                    existing.save()
                return redirect('budget_list')

            budget.save()
            return redirect('budget_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = BudgetForm(user=request.user)
    
    context = {
        'form': form,
        'title': 'Create Budget'
    }
    return render(request, 'dashboard/budget_form.html', context)


@login_required
def budget_edit(request, budget_id):
    """Edit an existing budget"""
    from ledger.models import Budget
    from ledger.forms import BudgetForm
    from django.shortcuts import redirect, get_object_or_404
    from django.contrib import messages
    
    budget = get_object_or_404(Budget, id=budget_id, user=request.user)
    
    if request.method == 'POST':
        form = BudgetForm(request.POST, instance=budget, user=request.user)
        if form.is_valid():
            form.save()
            return redirect('budget_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = BudgetForm(instance=budget, user=request.user)
    
    context = {
        'form': form,
        'title': 'Edit Budget',
        'budget': budget
    }
    return render(request, 'dashboard/budget_form.html', context)


@login_required
def budget_delete(request, budget_id):
    """Delete a budget"""
    from ledger.models import Budget
    from django.shortcuts import redirect, get_object_or_404
    from django.contrib import messages
    
    budget = get_object_or_404(Budget, id=budget_id, user=request.user)
    category_name = budget.category
    budget.is_active = False
    budget.save()
    return redirect('budget_list')


@login_required
def trash_view(request):
    """Superuser-only trash view to see and restore soft-deleted items."""
    if not request.user.is_superuser:
        messages.error(request, "Access denied. Superuser only.")
        return redirect("dashboard")

    if request.method == "POST":
        model_type = request.POST.get("model_type")
        item_id = request.POST.get("item_id")
        if model_type and item_id:
            from ledger.models import Transaction, Budget
            from notes.models import Note
            from savings.models import SavingGoal, SavingTransaction
            model_map = {
                "transaction": (Transaction, []),
                "budget": (Budget, []),
                "note": (Note, []),
                "saving_goal": (SavingGoal, []),
                "saving_transaction": (SavingTransaction, []),
            }
            entry = model_map.get(model_type)
            if entry:
                model_cls, related = entry
                try:
                    obj = model_cls.all_objects.get(pk=item_id)
                    obj.is_active = True
                    obj.save()
                    if model_type == "saving_goal":
                        SavingTransaction.all_objects.filter(saving_goal=obj).update(is_active=True)
                except model_cls.DoesNotExist:
                    messages.error(request, "Item not found.")
        return redirect("trash_view")

    from ledger.models import Transaction, Budget
    from notes.models import Note
    from savings.models import SavingGoal, SavingTransaction

    deleted_transactions = Transaction.all_objects.filter(is_active=False).select_related('user')
    deleted_budgets = Budget.all_objects.filter(is_active=False).select_related('user')
    deleted_notes = Note.all_objects.filter(is_active=False).select_related('user')
    deleted_goals = SavingGoal.all_objects.filter(is_active=False).select_related('user')
    deleted_saving_txns = SavingTransaction.all_objects.filter(is_active=False).select_related('user', 'saving_goal')

    context = {
        "deleted_transactions": deleted_transactions,
        "deleted_budgets": deleted_budgets,
        "deleted_notes": deleted_notes,
        "deleted_goals": deleted_goals,
        "deleted_saving_txns": deleted_saving_txns,
    }
    return render(request, "dashboard/trash.html", context)


@login_required
def budget_update_ajax(request):
    """Update budget via AJAX"""
    from ledger.models import Budget
    from django.http import JsonResponse
    from django.shortcuts import get_object_or_404
    
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        try:
            budget_id = request.POST.get('budget_id')
            amount = request.POST.get('amount')
            
            if not budget_id or not amount:
                return JsonResponse({'success': False, 'error': 'Missing required fields'})
            
            budget = get_object_or_404(Budget, id=budget_id, user=request.user)
            budget.amount = float(amount)
            budget.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Budget for {budget.category} updated successfully!'
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})


@login_required
def budget_delete_ajax(request):
    """Delete budget via AJAX"""
    from ledger.models import Budget
    from django.http import JsonResponse
    from django.shortcuts import get_object_or_404
    
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        try:
            budget_id = request.POST.get('budget_id')
            
            if not budget_id:
                return JsonResponse({'success': False, 'error': 'Missing budget ID'})
            
            budget = get_object_or_404(Budget, id=budget_id, user=request.user)
            category_name = budget.category
            budget.is_active = False
            budget.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Budget for {category_name} deleted successfully!'
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})


@login_required
def export_data(request):
    import pandas as pd
    from io import BytesIO

    user = request.user
    dfs = {}

    qs = Transaction.objects.filter(user=user, is_active=True).values(
        'date', 'transaction_type', 'category', 'amount', 'money_type',
        'description', 'switch_direction', 'is_pinned'
    )
    dfs['Transactions'] = pd.DataFrame(list(qs))

    qs = Budget.objects.filter(user=user, is_active=True).values(
        'category', 'amount', 'period', 'month', 'year', 'alert_threshold'
    )
    dfs['Budgets'] = pd.DataFrame(list(qs))

    qs = SavingGoal.objects.filter(user=user, is_active=True).values(
        'title', 'icon', 'target_amount', 'current_amount',
        'description', 'deadline', 'status'
    )
    dfs['Savings Goals'] = pd.DataFrame(list(qs))

    qs = SavingTransaction.objects.filter(user=user, is_active=True).values(
        'saving_goal__title', 'transaction_type', 'source', 'amount', 'note', 'date'
    )
    dfs['Savings Transactions'] = pd.DataFrame(list(qs))

    qs = Note.objects.filter(user=user, is_active=True).values(
        'title', 'content', 'color', 'category', 'priority', 'is_pinned', 'date'
    )
    dfs['Notes'] = pd.DataFrame(list(qs))

    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for name, df in dfs.items():
            if not df.empty:
                df.to_excel(writer, sheet_name=name, index=False)

    output.seek(0)
    today_str = date.today().isoformat()
    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="MoneyLogger_{today_str}.xlsx"'
    return response
