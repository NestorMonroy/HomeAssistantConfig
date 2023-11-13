"""Support for the Airzone diagnostics."""
from __future__ import annotations
import datetime

from typing import Any
from attr import asdict

from proxmoxer.core import ResourceException

from homeassistant.components.diagnostics.util import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_UNIQUE_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers import device_registry as dr, entity_registry as er

from .const import COORDINATORS, DOMAIN, LOGGER, PROXMOX_CLIENT
from .coordinator import ProxmoxNodeCoordinator, ProxmoxQEMUCoordinator, ProxmoxLXCCoordinator, ProxmoxStorageCoordinator, ProxmoxUpdateCoordinator

TO_REDACT_CONFIG = ["host", "username", "password"]

TO_REDACT_COORD = []

TO_REDACT_API = []

TO_REDACT_DATA = ["configuration_url"]


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""

    coordinators: dict[str, ProxmoxNodeCoordinator | ProxmoxQEMUCoordinator | ProxmoxLXCCoordinator | ProxmoxStorageCoordinator | ProxmoxUpdateCoordinator] = hass.data[DOMAIN][config_entry.entry_id][COORDINATORS]

    proxmox_client = hass.data[DOMAIN][config_entry.entry_id][PROXMOX_CLIENT]

    proxmox = proxmox_client.get_api_client()

    try:
        resources = await hass.async_add_executor_job(proxmox.cluster.resources.get)
    except ResourceException as error:
        if error.status_code == 403:
            resources = "403 Forbidden: Permission check failed"
        else:
            resources = "Error"


    nodes = {}
    try:
        nodes_api= await hass.async_add_executor_job(proxmox.nodes().get)
    except ResourceException as error:
        if error.status_code == 403:
            nodes_api = "403 Forbidden: Permission check failed"
        else:
            nodes_api = "Error"

    for node in nodes_api:
        nodes[node["node"]] = node

        try:
            nodes[node["node"]]["qemu"] = await hass.async_add_executor_job(proxmox.nodes(node["node"]).qemu.get)
        except ResourceException as error:
            if error.status_code == 403:
                nodes[node["node"]]["qemu"] = "403 Forbidden: Permission check failed"
            else:
                nodes[node["node"]]["qemu"] = "Error"

        try:
            nodes[node["node"]]["lxc"] = await hass.async_add_executor_job(proxmox.nodes(node["node"]).lxc.get)
        except ResourceException as error:
            if error.status_code == 403:
                nodes[node["node"]]["lxc"] = "403 Forbidden: Permission check failed"
            else:
                nodes[node["node"]]["lxc"] = "Error"

        try:
            nodes[node["node"]]["storage"] = await hass.async_add_executor_job(proxmox.nodes(node["node"]).storage.get)
        except ResourceException as error:
            if error.status_code == 403:
                nodes[node["node"]]["storage"] = "403 Forbidden: Permission check failed"
            else:
                nodes[node["node"]]["storage"] = "Error"

        try:
            nodes[node["node"]]["updates"] = await hass.async_add_executor_job(proxmox.nodes(node["node"]).apt.update.get)
        except ResourceException as error:
            if error.status_code == 403:
                nodes[node["node"]]["updates"] = "403 Forbidden: Permission check failed"
            else:
                nodes[node["node"]]["updates"] = "Error"

    api_data = {
            "resources": resources,
            "nodes":nodes,
        }

    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)

    devices = []

    registry_devices = dr.async_entries_for_config_entry(
        device_registry, config_entry.entry_id
    )

    for device in registry_devices:
        entities = []

        registry_entities = er.async_entries_for_device(
            entity_registry,
            device_id=device.id,
            include_disabled_entities=True,
        )

        for entity_entry in registry_entities:
            state_dict = None
            if state := hass.states.get(entity_entry.entity_id):
                state_dict = dict(state.as_dict())
                state_dict.pop("context", None)

            entities.append({"entry": asdict(entity_entry), "state": state_dict})

        devices.append({"device": asdict(device), "entities": entities})

    return {
        "timestamp": datetime.datetime.now(),
        "config_entry": async_redact_data(config_entry.data, TO_REDACT_CONFIG),
        "options": async_redact_data(config_entry.options, TO_REDACT_CONFIG),
        "devices": async_redact_data(devices, TO_REDACT_DATA),
        "proxmox_coordinators": {
            coordinator.name: {
                "data": async_redact_data(
                    coordinator.data.__dict__, TO_REDACT_COORD
                ) if coordinator.data is not None else {}
            }
            for coordinator in coordinators.values()
        },
        "api_response": async_redact_data(api_data, TO_REDACT_API) if api_data is not None else {},
    }

async def async_get_device_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry, device: DeviceEntry
) -> dict:
    """Return diagnostics for a device entry."""

    config_entry_diagnostics = await async_get_config_entry_diagnostics(hass, config_entry)

    return {
        "source": f"device - {device.id}",
        **config_entry_diagnostics,
    }