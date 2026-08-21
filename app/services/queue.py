from __future__ import annotations

import json

from app.core.config import Settings


class ProcessingQueue:
    async def enqueue_document(self, document_id: str) -> None:
        raise NotImplementedError


class LocalProcessingQueue(ProcessingQueue):
    async def enqueue_document(self, document_id: str) -> None:
        return None


class CloudTasksProcessingQueue(ProcessingQueue):
    def __init__(self, settings: Settings):
        from google.cloud import tasks_v2

        self.settings = settings
        self.client = tasks_v2.CloudTasksClient()
        self.parent = self.client.queue_path(
            settings.gcp_project_id,
            settings.cloud_tasks_location,
            settings.cloud_tasks_queue,
        )

    async def enqueue_document(self, document_id: str) -> None:
        from google.cloud import tasks_v2

        http_request = tasks_v2.HttpRequest(
            http_method=tasks_v2.HttpMethod.POST,
            url=self.settings.worker_url,
            headers={"Content-Type": "application/json"},
            body=json.dumps({"document_id": document_id}).encode(),
        )
        if self.settings.worker_oidc_service_account:
            http_request.oidc_token = tasks_v2.OidcToken(service_account_email=self.settings.worker_oidc_service_account)
        self.client.create_task(parent=self.parent, task=tasks_v2.Task(http_request=http_request))


def get_queue(settings: Settings) -> ProcessingQueue:
    if settings.app_env == "production":
        return CloudTasksProcessingQueue(settings)
    return LocalProcessingQueue()
