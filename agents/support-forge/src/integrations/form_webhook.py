"""Normalize website form payloads into ingest shape."""

from __future__ import annotations

from ..models import Channel, Customer, FormWebhook, IngestMessage


def form_to_ingest(form: FormWebhook) -> IngestMessage:
    text = form.message
    if form.subject:
        text = f"Subject: {form.subject}\n\n{text}"
    return IngestMessage(
        channel=Channel.form,
        text=text,
        customer=Customer(name=form.name, email=form.email),
        subject=form.subject or "Website form",
        metadata={
            "page_url": form.page_url,
            **(form.metadata or {}),
        },
    )
