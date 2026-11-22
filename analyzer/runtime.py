"""UI-independent cooperative cancellation and progress notifications."""


class AnalysisCancelled(Exception):
    """A local operation was cancelled before publishing its result."""


def check_cancel(cancel):
    if cancel is not None and cancel():
        raise AnalysisCancelled('Vorgang abgebrochen; keine unvollständige Ausgabe gespeichert.')


def notify(progress, stage, fraction, message):
    if progress is not None:
        progress(stage, fraction, message)
