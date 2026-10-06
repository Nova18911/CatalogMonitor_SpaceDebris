"""События Модели (паттерн «Наблюдатель»): Модель сообщает об изменениях,
не зная, кто слушает."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ModelEvent:
    kind: str          # object_registered | objects_lost | observation_added
    payload: Any = None


class IModelObserver(ABC):
    @abstractmethod
    def on_model_changed(self, event: ModelEvent) -> None:
        """Вызывается после изменения данных."""


class EventBus:
    def __init__(self) -> None:
        self._observers: list[IModelObserver] = []

    def subscribe(self, observer: IModelObserver) -> None:
        if observer not in self._observers:
            self._observers.append(observer)

    def unsubscribe(self, observer: IModelObserver) -> None:
        self._observers = [o for o in self._observers if o is not observer]

    def publish(self, event: ModelEvent) -> None:
        for observer in self._observers:
            observer.on_model_changed(event)