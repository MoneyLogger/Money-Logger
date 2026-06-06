from django.db.models import Sum, Q


class BalanceService:
    def __init__(self, real_qs, whatif_qs=None):
        self.real_qs = real_qs
        self.whatif_qs = whatif_qs

    def compute(self):
        agg = self.real_qs.aggregate(
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
        if self.whatif_qs is not None and self.whatif_qs.exists():
            wi_agg = self.whatif_qs.aggregate(
                upi_income=Sum('amount', filter=Q(transaction_type="INCOME", money_type="UPI CASH")),
                upi_expense=Sum('amount', filter=Q(transaction_type="EXPENSE", money_type="UPI CASH")),
                hand_income=Sum('amount', filter=Q(transaction_type="INCOME", money_type="HAND CASH")),
                hand_expense=Sum('amount', filter=Q(transaction_type="EXPENSE", money_type="HAND CASH")),
            )
            for k in wi_agg:
                agg[k] = (agg[k] or 0) + (wi_agg[k] or 0)

        def v(key):
            return float(agg.get(key) or 0)

        upi = v('upi_income') - v('upi_expense') + v('upi_in_sw') - v('upi_out_sw') - v('upi_saving')
        hand = v('hand_income') - v('hand_expense') + v('hand_in_sw') - v('hand_out_sw') - v('hand_saving')
        return upi, hand

    @classmethod
    def for_user(cls, user, whatif=False):
        from .models import Transaction, WhatIfTransaction
        real_qs = Transaction.objects.filter(user=user)
        wi_qs = WhatIfTransaction.objects.filter(user=user) if whatif else WhatIfTransaction.objects.none()
        return cls(real_qs, wi_qs).compute()
