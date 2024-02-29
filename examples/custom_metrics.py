from datetime import datetime, timedelta, timezone

from bytewax import operators as op
from bytewax.connectors.stdio import StdOutSink
from bytewax.dataflow import Dataflow
from bytewax.inputs import (
    DynamicSource,
    StatelessSourcePartition,
)
from prometheus_client import Gauge


class PeriodicPartition(StatelessSourcePartition):
    def __init__(self, step_id: str, frequency: timedelta):
        self.frequency = frequency
        self._next_awake = datetime.now(timezone.utc)
        self._gauge = Gauge(
            "next_batch_delay",
            "Calculated delay of when next batch was called in seconds",
            ["step_id", "partition"],
            unit="seconds",
        )
        self._counter = 0
        self._metric_labels = {"step_id": step_id, "partition": "0"}

    def next_awake(self):
        return self._next_awake

    def next_batch(self):
        self._counter += 1
        # Calculate the delay between when this was supposed
        # to  be called, and when it is actually called
        delay = datetime.now(timezone.utc) - self._next_awake
        self._next_awake += self.frequency
        self._gauge.labels(**self._metric_labels).set(delay.total_seconds())

        return [self._counter]


class PeriodicSource(DynamicSource):
    def __init__(self, frequency):
        self.frequency = frequency

    def build(self, step_id: str, worker_index: int, worker_count: int):
        return PeriodicPartition(step_id, frequency=self.frequency)


flow = Dataflow("custom_metrics")
stream = op.input("periodic", flow, PeriodicSource(timedelta(seconds=1)))
op.output("stdout", stream, StdOutSink())
