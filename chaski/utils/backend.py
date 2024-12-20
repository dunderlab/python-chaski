import os
import logging
from typing import Any, Dict, Optional

from celery.backends.base import BaseBackend
from celery.app import backends

from chaski.streamer_sync import ChaskiStreamerSync


########################################################################
class ChaskiBackend(BaseBackend):
    """
    A custom Celery backend using ChaskiStreamerSync for task results.

    Parameters
    ----------
    app : Celery
        The Celery application instance.
    kwargs : dict
        Additional arguments for the backend initialization.
    """

    def __init__(self, app: Any, **kwargs: Any) -> None:
        super().__init__(app, **kwargs)
        self._results: Dict[str, Any] = {}

        self.storage = ChaskiStreamerSync(
            name="Storage Streamer - GET",
            subscriptions=["storage"],
            paired=True,
            persistent_storage=True,
        )
        self.storage.connect(
            os.getenv("CHASKI_STREAMER_ROOT", "*ChaskiStreamer@127.0.0.1:65433")
        )

    # ----------------------------------------------------------------------
    def _store_result(
        self,
        task_id: str,
        result: Any,
        state: str,
        traceback: Optional[str] = None,
        request: Optional[Any] = None,
        **kwargs: Any,
    ) -> Any:
        """
        Store the result of a Celery task.

        Parameters
        ----------
        task_id : str
            The unique identifier for the task.
        result : Any
            The result of the task execution.
        state : str
            The state of the task (e.g., SUCCESS, FAILURE).
        traceback : Optional[str], optional
            The traceback if the task failed.
        request : Optional[Any], optional
            The task request information.
        kwargs : Any
            Additional arguments.

        Returns
        -------
        Any
            The result of the task.
        """
        logging.debug(f"Storing result for task_id: {task_id}")
        self.storage.store_data(
            task_id,
            {
                "result": result,
                "state": state,
                "traceback": traceback,
            },
        )
        return result

    # ----------------------------------------------------------------------
    def _get_task_meta_for(self, task_id: str) -> Dict[str, Any]:
        """
        Retrieve the metadata for a given task.

        Parameters
        ----------
        task_id : str
            The unique identifier for the task.

        Returns
        -------
        dict
            The metadata for the task, including result, state, and traceback.
        """
        response = self.storage.persistent_storage.get(task_id, None)

        if response:
            return {
                "task_id": task_id,
                "result": response["result"],
                "state": response["state"],
                "traceback": response["traceback"],
                "status": response["state"],
            }
        else:
            self.storage.fetch_storage(task_id)
            return {"status": "PENDING", "result": None}

    # ----------------------------------------------------------------------
    def cleanup(self) -> None:
        """
        Clear all cached results from the backend.
        """
        self._results.clear()


# Update Celery backend aliases to include ChaskiBackend.
backends.BACKEND_ALIASES["chaski"] = "chaski.utils.backend:ChaskiBackend"
