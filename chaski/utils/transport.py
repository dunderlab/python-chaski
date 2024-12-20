import os
from queue import Empty
import time
from typing import Optional, Any

from kombu import transport
from kombu.transport.virtual import Transport, Channel
from chaski.streamer_sync import ChaskiStreamerSync

CHASKI_TOPIC = "celery_tasks"


########################################################################
class ChaskiChannel(Channel):
    """
    A custom Kombu channel implementation using ChaskiStreamerSync.

    Parameters
    ----------
    args : tuple
        Positional arguments for the base Channel class.
    kwargs : dict
        Keyword arguments for the base Channel class.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.producer = ChaskiStreamerSync(
            name="ChaskiChannel Producer",
            paired=True,
        )
        self.producer.connect(
            os.getenv("CHASKI_STREAMER_ROOT", "*ChaskiStreamer@127.0.0.1:65433")
        )
        time.sleep(0.5)

        self.consumer: Optional[ChaskiStreamerSync] = None

    # ----------------------------------------------------------------------
    def _new_queue(self, queue: str, **kwargs: Any) -> None:
        """
        Simulates the creation of a new logical queue.

        Parameters
        ----------
        queue : str
            The name of the logical queue.
        kwargs : dict
            Additional arguments.
        """
        pass

    # ----------------------------------------------------------------------
    def _delete(self, queue: str, **kwargs: Any) -> None:
        """
        Simulates the deletion of a logical queue.

        Parameters
        ----------
        queue : str
            The name of the logical queue to delete.
        kwargs : dict
            Additional arguments.
        """
        pass

    # ----------------------------------------------------------------------
    def _put(self, queue: str, message: dict, **kwargs: Any) -> None:
        """
        Publishes a message to the logical queue.

        Parameters
        ----------
        queue : str
            The name of the logical queue.
        message : dict
            The message to be published.
        kwargs : dict
            Additional arguments.
        """
        self.producer.push(CHASKI_TOPIC, message)

    # ----------------------------------------------------------------------
    def _get(self, queue: str, timeout: Optional[int] = None) -> dict:
        """
        Retrieves a message from the logical queue.

        Parameters
        ----------
        queue : str
            The name of the logical queue.
        timeout : Optional[int], optional
            The maximum time to wait for a message, in seconds.

        Returns
        -------
        dict
            The retrieved message.

        Raises
        ------
        Empty
            If no message is available within the specified timeout.
        """
        if self.consumer is None:
            self.consumer = ChaskiStreamerSync(
                name="ChaskiChannel Consumer",
                subscriptions=[CHASKI_TOPIC],
                paired=True,
            )
            self.consumer.connect(
                os.getenv("CHASKI_STREAMER_ROOT", "*ChaskiStreamer@127.0.0.1:65433")
            )

        try:
            incoming_message = next(self.consumer.message_stream(timeout=5))
            message = incoming_message.data
            message["delivery_info"] = {"routing_key": queue}
            return message

        except:
            raise Empty()

    # ----------------------------------------------------------------------
    def close(self) -> None:
        """
        Closes the producer and consumer connections.
        """
        self.producer.close()
        if self.consumer is not None:
            self.consumer.close()


########################################################################
class ChaskiTransport(Transport):
    """
    A custom Kombu transport implementation using ChaskiStreamerSync.

    Attributes
    ----------
    Channel : type
        The channel class used by this transport.
    default_port : int
        The default port used by the transport.
    """

    Channel = ChaskiChannel

    # ----------------------------------------------------------------------
    def driver_version(self) -> str:
        """
        Retrieves the version of the driver.

        Returns
        -------
        str
            The driver version string.
        """
        return "chaski"


# Update Kombu transport aliases to include ChaskiTransport.
transport.TRANSPORT_ALIASES.update({"chaski": "chaski.utils.transport:ChaskiTransport"})
