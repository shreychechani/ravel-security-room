"""Background job with no public entry point (second caller of process_payment)."""
from payments import process_payment


def retry_job(failed_amounts):
    return [process_payment(a) for a in failed_amounts]
