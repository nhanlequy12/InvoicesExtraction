from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import List, Optional


@dataclass
class AccountPostingLine:
    account_debit: str # TK No (e.g. 1561 - Hang hoa, 1331 - Thue GTGT)
    account_credit: str # TK Co (e.g. 331 - Phai tra nguoi ban)
    amount: Decimal
    description: str


@dataclass
class AccountingJournalEntry:
    entry_number: str
    posting_date: str
    invoice_number: str
    invoice_series: str
    seller_tax_id: str
    seller_name: str
    currency: str
    total_amount: Decimal
    lines: List[AccountPostingLine] = field(default_factory=list)
