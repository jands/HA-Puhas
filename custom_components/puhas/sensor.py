"""Sensors for Puhas."""
from __future__ import annotations

from datetime import date

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import PuhasService
from .const import DOMAIN
from .coordinator import PuhasConfigEntry, PuhasCoordinator

WEEKDAYS = {
    "fi": (
        ("ma", "maanantai"), ("ti", "tiistai"), ("ke", "keskiviikko"), ("to", "torstai"),
        ("pe", "perjantai"), ("la", "lauantai"), ("su", "sunnuntai"),
    ),
    "en": (
        ("Mon", "Monday"), ("Tue", "Tuesday"), ("Wed", "Wednesday"), ("Thu", "Thursday"),
        ("Fri", "Friday"), ("Sat", "Saturday"), ("Sun", "Sunday"),
    ),
}


def describe_date(hass: HomeAssistant, value: date | None) -> dict[str, str]:
    """Return 'formatted' (e.g. 'ma 2.11.2026') and 'weekday' (e.g. 'maanantai')."""
    if value is None:
        return {}
    lang = "fi" if hass.config.language.lower().startswith("fi") else "en"
    short, full = WEEKDAYS[lang][value.weekday()]
    return {
        "formatted": f"{short} {value.day}.{value.month}.{value.year}",
        "weekday": full,
    }


async def async_setup_entry(
    hass: HomeAssistant, entry: PuhasConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Set up sensors; new containers appearing later get a sensor too."""
    coordinator = entry.runtime_data
    known: set[str] = set()

    @callback
    def _add_new_services() -> None:
        new = []
        for service in coordinator.data.services:
            if service.key not in known:
                known.add(service.key)
                new.append(PuhasServiceSensor(coordinator, entry, service))
        if new:
            async_add_entities(new)

    async_add_entities(
        [PuhasNextCollectionSensor(coordinator, entry), PuhasNextCollectionTextSensor(coordinator, entry)]
    )
    _add_new_services()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_services))


class PuhasEntity(CoordinatorEntity[PuhasCoordinator], SensorEntity):
    """Base entity."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.DATE

    def __init__(self, coordinator: PuhasCoordinator, entry: PuhasConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=coordinator.data.address or entry.title,
            manufacturer="Puhas Oy",
            entry_type=DeviceEntryType.SERVICE,
        )


class PuhasNextCollectionSensor(PuhasEntity):
    """Earliest upcoming collection over all containers (date)."""

    _attr_translation_key = "next_collection"

    def __init__(self, coordinator: PuhasCoordinator, entry: PuhasConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_next"

    def _upcoming(self) -> list[PuhasService]:
        today = date.today()
        dated = [s for s in self.coordinator.data.services if s.next_date and s.next_date >= today]
        if not dated:
            return []
        first = min(s.next_date for s in dated)
        return [s for s in dated if s.next_date == first]

    @property
    def native_value(self) -> date | None:
        upcoming = self._upcoming()
        return upcoming[0].next_date if upcoming else None

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        attrs: dict[str, object] = {"containers": [s.name for s in self._upcoming()]}
        attrs.update(describe_date(self.hass, self.native_value))
        return attrs


class PuhasNextCollectionTextSensor(PuhasNextCollectionSensor):
    """Same as above, but as text with weekday: 'ma 2.11.2026'."""

    _attr_translation_key = "next_collection_text"
    _attr_device_class = None

    def __init__(self, coordinator: PuhasCoordinator, entry: PuhasConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_next_text"

    @property
    def native_value(self) -> str | None:  # type: ignore[override]
        upcoming = self._upcoming()
        if not upcoming:
            return None
        return describe_date(self.hass, upcoming[0].next_date).get("formatted")

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        upcoming = self._upcoming()
        attrs: dict[str, object] = {"containers": [s.name for s in upcoming]}
        if upcoming:
            attrs["date"] = upcoming[0].next_date.isoformat()
            attrs.update(describe_date(self.hass, upcoming[0].next_date))
        return attrs


class PuhasServiceSensor(PuhasEntity):
    """Next collection of one container."""

    def __init__(
        self, coordinator: PuhasCoordinator, entry: PuhasConfigEntry, service: PuhasService
    ) -> None:
        super().__init__(coordinator, entry)
        self._key = service.key
        self._attr_name = service.name
        self._attr_unique_id = f"{entry.entry_id}_{service.key}"

    def _service(self) -> PuhasService | None:
        return next((s for s in self.coordinator.data.services if s.key == self._key), None)

    @property
    def available(self) -> bool:
        return super().available and self._service() is not None

    @property
    def native_value(self) -> date | None:
        service = self._service()
        return service.next_date if service else None

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        return describe_date(self.hass, self.native_value)
